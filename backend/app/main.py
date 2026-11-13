"""Local FastAPI integration around LifeLine's existing, deterministic model."""

import asyncio
from contextlib import asynccontextmanager
import importlib
import logging
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from starlette.concurrency import run_in_threadpool
from starlette.exceptions import HTTPException
from .comparison import compare_schedules
from .energy_simulator import NumericalError
from .explanations import explain
from .models import (ApiErrorResponse, HealthResponse, ScenarioListResponse,
                     SimulationRequest, SimulationResponse)
from .optimizer import SolverError
from .scenarios import CONFIG_PATH, load_catalog

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
            defaults=catalog.resolve(SimulationRequest(scenario=p.id)), expected_status=p.expected_status)
            for p in catalog.scenarios])

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
            pv_performance_ratio=catalog.pv_model.performance_ratio, effective_config=config,
            equipment=equipment, assumptions=[catalog.provenance,
                'All clinic and weather values are synthetic; this is a scenario forecast, not measured or trained-model output.',
                'Fixed 24 hourly slots in Africa/Nairobi; battery chart boundaries run from 0 through 24.',
                'PV uses a synthetic 06:00–18:00 sine curve and the returned performance ratio/cloud profile.',
                'Critical loads are operator-defined and never rescheduled; flexible tasks are divisible energy approximations.',
                'Reserve is a target above physical zero; losses, rate limits, and capacity are modeled on one idealized energy bus.',
                'Storm starts depleted after hypothetical earlier cloudy days; those days are not simulated.',
                'No thermal dynamics, sub-hour surges, degradation, uncertainty, grid, or generator are modeled.',
                'All three schedules use identical inputs. Same-work comparisons must check completion; heuristic ties are explicit.',
                'Illustrative simulation; not for clinical or operational use.'],
            status=results['optimized']['status'], baseline=results['baseline'], heuristic=results['heuristic'],
            optimized=results['optimized'], comparison=results['comparison'], warnings=warnings,
            recommendations=recommendations)

    return app


app = create_app()
