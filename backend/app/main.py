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

logger = logging.getLogger(__name__)


def error_response(status, code, message, details=None):
    payload = ApiErrorResponse(error=dict(code=code, message=message, details=details or []))
    return JSONResponse(status_code=status, content=payload.model_dump())


def validation_details(errors, prefix=()):
    # Never serialize Pydantic input/ctx: they may contain NaN, exception objects,
    # or request values that should not be reflected into an error response.
    return [dict(loc=list(prefix)+list(e['loc']), message=e['msg'], type=e['type']) for e in errors]


def create_app(config_path: Path = CONFIG_PATH):
    @asynccontextmanager
    async def lifespan(app):
        app.state.catalog = load_catalog(config_path)
        load_weather()
        importlib.import_module('scipy.optimize')  # preload before accepting requests
        app.state.solve_lock = asyncio.Lock()
        yield

    app = FastAPI(title='LifeLine API', version='1.0', lifespan=lifespan,
                  description='Synthetic energy planning; not for clinical or operational use.')

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

    @app.get('/api/planning-status')
    async def planning_status():
        # No forecast provider is configured in this offline application. Do not
        # present bundled historical data as tomorrow's weather or a live check.
        return {'assistant': 'offline', 'forecast': {'available': False,
            'reason': 'No live forecast provider is connected.', 'source': None,
            'forecast_date': None,
            'requested_date': (datetime.now(ZoneInfo('Africa/Nairobi')) + timedelta(days=1)).date().isoformat(),
            'updated_at': None}, 'timezone': 'Africa/Nairobi'}

    @app.post('/api/simulate', response_model=SimulationResponse, responses={
        422: {'model': ApiErrorResponse}, 503: {'model': ApiErrorResponse}, 500: {'model': ApiErrorResponse}})
    async def simulate(body: SimulationRequest, request: Request):
        catalog = request.app.state.catalog
        try:
            config = catalog.resolve(body)
        except ValidationError as exc:
            return error_response(422, 'INVALID_REQUEST', 'Resolved battery configuration is invalid.',
                                  validation_details(exc.errors(), ('body',)))
        inputs = catalog.build_inputs(body, config)
        # Keep health/catalog responsive during CPU work; one solve at a time
        # per worker avoids competing HiGHS solves exhausting local resources.
        async with request.app.state.solve_lock:
            results = await run_in_threadpool(compare_schedules, inputs)
        equipment = catalog.equipment_for(body, config)
        warnings, recommendations = explain(results, inputs, equipment)
        return SimulationResponse(scenario=body.scenario, scenario_name=catalog.preset(body.scenario).name,
            data_source="mixed" if body.weather_dataset != "synthetic" else ("user_defined" if body.equipment is not None else "synthetic"),
            cloud_factors=body.cloud_factors if body.cloud_factors is not None else catalog.preset(body.scenario).cloud_factors,
            weather_dataset=body.weather_dataset, diagnosis=diagnose(inputs, results),
            input_provenance={"equipment": "user_entered_unverified" if body.equipment is not None else "synthetic",
                              "weather": "NASA_POWER_historical_satellite_derived" if body.weather_dataset != "synthetic" else ("user_entered_scenario_factors" if body.cloud_factors is not None else "synthetic_scenario"),
                              "model": "Horizontal irradiance approximation; not a forecast" if body.weather_dataset != "synthetic" else "Fixed daylight curve; not measured irradiance or an operational weather forecast"},
            pv_performance_ratio=catalog.pv_model.performance_ratio, effective_config=config,
            equipment=equipment, assumptions=[
                'Equipment values are user-entered and unverified.' if body.equipment is not None else catalog.provenance,
                ('Weather is historical satellite-derived irradiance, not a clinic measurement or current forecast.' if body.weather_dataset != 'synthetic' else 'Weather is a synthetic/user-adjusted scenario forecast, not measured or trained-model output.'),
                'Fixed 24 hourly slots in Africa/Nairobi; battery chart boundaries run from 0 through 24.',
                ('NASA POWER historical satellite-derived irradiance; horizontal input is an approximation, not a clinic measurement or forecast.' if body.weather_dataset != 'synthetic' else 'PV uses a synthetic 06:00–18:00 sine curve and the returned performance ratio/cloud profile.'),
                'Critical loads are operator-defined and never rescheduled; flexible tasks are divisible energy approximations.',
                'Reserve is a target above physical zero; losses, rate limits, and capacity are modeled on one idealized energy bus.',
                'Storm starts depleted after hypothetical earlier cloudy days; those days are not simulated.',
                'No thermal dynamics, sub-hour surges, degradation, uncertainty, grid, or generator are modeled.',
                'All three schedules use identical inputs. Same-work comparisons must check completion; heuristic ties are explicit.',
                'Illustrative simulation; not for clinical or operational use.'],
            status=results['optimized']['status'], baseline=results['baseline'], heuristic=results['heuristic'],
            optimized=results['optimized'], comparison=results['comparison'], warnings=warnings,
            recommendations=recommendations)

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


app = create_app()
