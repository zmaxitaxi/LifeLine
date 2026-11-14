"""Local FastAPI integration around LifeLine's existing, deterministic model."""

import asyncio
from contextlib import asynccontextmanager
import importlib
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError
from starlette.concurrency import run_in_threadpool
from starlette.exceptions import HTTPException
from .comparison import compare_schedules
from .diagnosis import diagnose
from .energy_simulator import NumericalError
from .explanations import explain
from .models import (ApiErrorResponse, HealthResponse, ScenarioListResponse,
                     SimulationRequest, SimulationResponse)
from .optimizer import SolverError
from .scenarios import CONFIG_PATH, load_catalog, load_weather
from .assistant import AssistantRequest, AssistantResponse, prepare, summarize
from .forecast_routes import router as forecast_router
from .weather_forecast import ForecastError, ForecastService
from .agent_provider import configured_agent, load_local_settings
from .agent_routes import router as agent_router
from .demos import competing_windows, recovery_demo
from .simulation import simulate_case
from .recovery_routes import router as recovery_router
from .planning_routes import router as planning_router
from .planning_state import PlanningStore, PlanningError
from .weather_outlook import WeatherOutlookService
from .weather_outlook_routes import router as weather_outlook_router

logger = logging.getLogger(__name__)


def error_response(status, code, message, details=None):
    payload = ApiErrorResponse(error=dict(code=code, message=message, details=details or []))
    return JSONResponse(status_code=status, content=payload.model_dump())


def validation_details(errors, prefix=()):
    # Never serialize Pydantic input/ctx: they may contain NaN, exception objects,
    # or request values that should not be reflected into an error response.
    return [dict(loc=list(prefix)+list(e['loc']), message=e['msg'], type=e['type']) for e in errors]


def create_app(config_path: Path = CONFIG_PATH, forecast_service=None, agent_service=None, outlook_service=None,
               planning_state_path=None, weather_mode='live', agent_provider=None):
    if weather_mode not in ('live', 'demo'):
        raise ValueError('Weather mode must be live or demo')
    @asynccontextmanager
    async def lifespan(app):
        app.state.catalog = load_catalog(config_path)
        load_weather()
        importlib.import_module('scipy.optimize')  # preload before accepting requests
        app.state.solve_lock = asyncio.Lock()
        from .demo_weather import DemoWeatherService, DemoOutlookService
        app.state.forecasts = forecast_service or (DemoWeatherService() if weather_mode=='demo' else ForecastService())
        app.state.agent = agent_service or configured_agent(agent_provider)
        app.state.planning = PlanningStore(planning_state_path)
        app.state.outlooks = outlook_service or (DemoOutlookService() if weather_mode=='demo' else WeatherOutlookService())
        app.state.weather_mode = weather_mode
        yield

    app = FastAPI(title='LifeLine API', version='1.0', lifespan=lifespan,
                  description='Synthetic energy planning; not for clinical or operational use.')

    @app.get('/api/weather/mode')
    async def configured_weather_mode(request: Request):
        return {'mode': request.app.state.weather_mode,
                'label': 'Demo weather · synthetic sample conditions' if request.app.state.weather_mode=='demo' else 'Live weather · Open-Meteo',
                'description': 'Sample weather and real physical calculations; the configured AI provider authors replies.' if request.app.state.weather_mode=='demo' else 'Actual forecasts require a reachable weather provider.'}

    @app.exception_handler(PlanningError)
    async def planning_error(request, exc):
        details = [dict(loc=['body'] + field.split('.'), message='Required operator input', type='missing') for field in exc.fields]
        return error_response(exc.status, exc.code, exc.message, details)

    @app.exception_handler(RequestValidationError)
    async def request_error(request, exc):
        return error_response(422, 'INVALID_REQUEST', 'Request validation failed.', validation_details(exc.errors()))

    @app.exception_handler(SolverError)
    async def solver_error(request, exc):
        # Do not expose solver/backend exception text to callers.
        code = exc.code if exc.code in {'SOLVER_UNAVAILABLE', 'SOLVER_TIME_LIMIT'} else 'SOLVER_UNAVAILABLE'
        return error_response(503, code, 'A verified optimization result is unavailable. Please retry.')

    @app.exception_handler(NumericalError)
    async def numerical_error(request, exc):
        logger.error('Numerical verification failed: %s', exc)
        return error_response(503, 'NUMERICAL_ERROR', 'The numerical result could not be verified. Please retry.')

    @app.exception_handler(ForecastError)
    async def forecast_error(request, exc):
        return error_response(exc.status, exc.code, exc.message)

    @app.exception_handler(HTTPException)
    async def http_error(request, exc):
        return error_response(exc.status_code, 'INVALID_REQUEST', str(exc.detail))

    @app.exception_handler(Exception)
    async def internal_error(request, exc):
        logger.exception('Unexpected simulation service failure')
        return error_response(500, 'INTERNAL_ERROR', 'The request could not be completed.')

    @app.get('/api/health', response_model=HealthResponse)
    async def health():
        return HealthResponse()

    @app.get('/api/scenarios', response_model=ScenarioListResponse)
    async def scenarios(request: Request):
        catalog = request.app.state.catalog
        return ScenarioListResponse(scenarios=[dict(id=p.id, name=p.name, description=p.description,
            defaults=catalog.resolve(SimulationRequest(scenario=p.id)), expected_status=p.expected_status,
            equipment=catalog.equipment_for(SimulationRequest(scenario=p.id), catalog.resolve(SimulationRequest(scenario=p.id))),
            cloud_factors=p.cloud_factors)
            for p in catalog.scenarios])

    @app.get('/api/weather')
    async def weather_datasets():
        return {'datasets': [load_weather()]}

    @app.get('/api/demos/competing-windows')
    async def competing_demo(request:Request):
        return competing_windows(request.app.state.catalog)

    @app.get('/api/demos/recovery')
    async def recovery_example(request:Request):
        return recovery_demo(request.app.state.catalog)

    @app.get('/api/planning-status')
    async def planning_status():
        # This describes the offline assistant's default example context. No
        # forecast is fetched without coordinates; it is not a provider health check.
        return {'assistant': 'offline', 'forecast': {'available': False,
            'reason': 'No forecast is selected for this offline example. Use the live-weather planner to retrieve Open-Meteo data.', 'source': None,
            'provider_configured': True, 'provider': 'Open-Meteo Forecast API',
            'forecast_date': None,
            'requested_date': (datetime.now(ZoneInfo('Africa/Nairobi')) + timedelta(days=1)).date().isoformat(),
            'updated_at': None}, 'timezone': 'Africa/Nairobi'}

    @app.post('/api/simulate', response_model=SimulationResponse, responses={
        422: {'model': ApiErrorResponse, 'description': 'Unprocessable Entity'},
        503: {'model': ApiErrorResponse}, 500: {'model': ApiErrorResponse}})
    async def simulate(body: SimulationRequest, request: Request):
        catalog = request.app.state.catalog
        try:
            config = catalog.resolve(body)
        except ValidationError as exc:
            return error_response(422, 'INVALID_REQUEST', 'Resolved battery configuration is invalid.',
                                  validation_details(exc.errors(), ('body',)))
        async with request.app.state.solve_lock:
            return await run_in_threadpool(simulate_case, catalog, body)

    @app.post('/api/assistant', response_model=AssistantResponse)
    async def assistant(body: AssistantRequest, request: Request):
        try:
            decision = prepare(body, request.app.state.catalog)
        except ValidationError as exc:
            return error_response(422, 'INVALID_REQUEST', 'Please check the clinic requirements.',
                                  validation_details(exc.errors(), ('body',)))
        if isinstance(decision, AssistantResponse):
            return decision
        candidates = decision if isinstance(decision, list) else [decision]
        computed = []
        for candidate in candidates:
            result = await simulate(candidate, request)
            if isinstance(result, JSONResponse):
                return result
            computed.append((candidate, result))
        # Minimize essential shortages, then reserve breaches, then maximize
        # minimum and final stored energy. All candidates use the real solver.
        selected, result = min(computed, key=lambda pair: (
            pair[1].optimized.metrics.critical_unserved_kwh,
            len(pair[1].optimized.metrics.reserve_breach_boundaries),
            -pair[1].optimized.metrics.min_soc_kwh,
            -pair[1].optimized.metrics.final_soc_kwh))
        message = summarize(result)
        previous_clouds = body.plan.cloud_factors if body.plan.cloud_factors is not None else request.app.state.catalog.preset(body.plan.scenario).cloud_factors
        if selected.cloud_factors is not None and sum(previous_clouds) > 0 and sum(selected.cloud_factors) < sum(previous_clouds) - 1e-8:
            fraction = 100 * sum(selected.cloud_factors) / sum(previous_clouds)
            message = f'I tested one day with {fraction:g}% of the sunshine in your current inputs, keeping equipment and starting battery charge unchanged. ' + message
        if 'reliab' in body.message.lower():
            metrics = result.optimized.metrics
            if result.diagnosis.discharge_limited_hours:
                message += ' Battery output is too limited during some essential hours, even with energy still stored.'
            elif metrics.reserve_breach_boundaries:
                message += ' The battery drops below its reserve target during this day.'
            else:
                message += ' The battery stays at or above its reserve target during this day.'
            message += ' This checks one day of energy use, not battery health or aging.'
        if isinstance(decision, list):
            item = result.equipment[-1]
            message += f' The added equipment was checked as a fixed hourly load from {min(item.required_hours):02d}:00 to {max(item.required_hours)+1:02d}:00. Actual sterilization cycles still require validation.'
        return AssistantResponse(message=message, request=selected, result=result,
            tools_used=['energy_simulator', 'schedule_optimizer', 'schedule_comparison'])

    app.include_router(forecast_router)
    app.include_router(agent_router)
    app.include_router(recovery_router)
    app.include_router(planning_router)
    app.include_router(weather_outlook_router)

    @app.api_route('/api/{path:path}', methods=['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD', 'OPTIONS'], include_in_schema=False)
    async def invalid_api_path(path: str, request: Request):
        # Do not let the dashboard's static catch-all turn known API method
        # errors into asset 404s. API errors keep their existing envelope.
        methods = set().union(*(getattr(route, 'methods', set()) for route in app.routes
                                if getattr(route, 'path', None) == request.url.path))
        response = error_response(405 if methods else 404, 'INVALID_REQUEST',
                                  'Method Not Allowed' if methods else 'Not Found')
        if methods:
            response.headers['Allow'] = ', '.join(sorted(methods))
        return response

    static_path = Path(__file__).resolve().parents[2] / "frontend/dist"
    if static_path.is_dir():
        app.mount("/", StaticFiles(directory=static_path, html=True), name="dashboard")
    return app


def local_state_path():
    import os
    configured = os.environ.get('LIFELINE_STATE_PATH')
    if configured == ':memory:':
        return None
    return Path(configured).expanduser() if configured else CONFIG_PATH.parent.parent / '.local' / 'planning-state.json'


import os
load_local_settings()
app = create_app(planning_state_path=local_state_path(), weather_mode=os.environ.get('LIFELINE_WEATHER_MODE', 'live'))
