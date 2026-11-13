"""Independent forecast/planner endpoints, preserving /api/simulate behavior."""
from fastapi import APIRouter, Query, Request
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from .forecast_models import (ForecastLocation, ForecastPlanRequest, ForecastPlanResponse, GuidedPlanRequest, GuidedForecastResponse,
                              PlannerToolCall, PlannerToolRequest, SolarForecast)
from .forecast_planner import plan_forecast, computed_assessment
from .planner_tools import execute_tool, guided_intent, tool_definitions
from .models import ApiErrorResponse

router = APIRouter()
ERRORS = {
    422: {'model': ApiErrorResponse, 'description': 'Unprocessable Entity'},
    503: {'model': ApiErrorResponse},
    500: {'model': ApiErrorResponse},
}
LOCATIONS = [
    {'id':'kisumu', 'name':'Kisumu, Kenya (representative location)', 'latitude':-.0917, 'longitude':34.768},
    {'id':'kampala', 'name':'Kampala, Uganda (representative location)', 'latitude':.3476, 'longitude':32.5825},
    {'id':'berkeley', 'name':'Berkeley, California (representative location)', 'latitude':37.8715, 'longitude':-122.273},
]


@router.get('/api/forecast/locations')
async def locations():
    return {'locations':LOCATIONS, 'note':'Coordinates are representative points, not identified partner clinics.'}


@router.get('/api/forecast', response_model=SolarForecast, responses=ERRORS)
async def forecast(request: Request, latitude: float = Query(ge=-90, le=90), longitude: float = Query(ge=-180, le=180)):
    return await request.app.state.forecasts.get(ForecastLocation(latitude=latitude, longitude=longitude))


@router.post('/api/forecast/plan', response_model=ForecastPlanResponse, responses=ERRORS)
async def forecast_plan(body: ForecastPlanRequest, request: Request):
    try:
        return await plan_forecast(body, request.app.state.catalog, request.app.state.forecasts, request.app.state.solve_lock)
    except ValidationError as exc:
        raise RequestValidationError(exc.errors()) from None


@router.get('/api/planner/tools')
async def planner_tools():
    return {'tools':tool_definitions(), 'context_schema':PlannerToolRequest.model_json_schema(),
            'llm_enabled':False, 'mode':'validated_tools_and_deterministic_guided_fallback',
            'note':'No hosted language model is connected. These tools can be called by a separately configured agent; guided answers are deterministic, not LLM-generated.'}


@router.post('/api/planner/tool', responses=ERRORS)
async def planner_tool(body: PlannerToolRequest, request: Request):
    try:
        return await execute_tool(body, body.tool_call, request.app.state.catalog, request.app.state.forecasts, request.app.state.solve_lock)
    except ValidationError as exc:
        raise RequestValidationError(exc.errors()) from None


@router.post('/api/planner/ask', response_model=GuidedForecastResponse, responses=ERRORS)
async def guided_plan(body: GuidedPlanRequest, request: Request):
    intent = guided_intent(body.question)
    if intent is None:
        return {'mode':'deterministic_guided_fallback', 'needs_clarification':True, 'tool_calls':[], 'result':None,
                'message':'A hosted language model is not connected. Guided mode supports planning today/tomorrow and a 50% lower-sunshine comparison for the configured equipment. Edit requirements in clinic settings; no new equipment, medical priorities, or operating windows have been inferred from this question.'}
    call = PlannerToolCall(name='plan_forecast', arguments=intent)
    try:
        result = await execute_tool(body, call, request.app.state.catalog, request.app.state.forecasts, request.app.state.solve_lock)
    except ValidationError as exc:
        raise RequestValidationError(exc.errors()) from None
    message = 'Computed planning answer using a validated tool call. This guided fallback is not an LLM agent.'
    factor = .5 if '50%' in body.question else .25 if '25% of the current sunshine' in body.question else 1.
    if factor != 1:
        reduced = next(case.plan for case in result.uncertainty_cases if case.sunshine_factor == factor)
        message += f' For {(1-factor)*100:g}% lower sunshine: '+computed_assessment(reduced)
        message += (f' Forecast solar energy changes from {result.plan.optimized.metrics.total_solar_kwh:.3f} to '
                    f'{reduced.optimized.metrics.total_solar_kwh:.3f} kWh. Each weather case has its own recomputed schedule.')
    else:
        message += ' '+computed_assessment(result.plan)
    return {'mode':'deterministic_guided_fallback', 'needs_clarification':False, 'tool_calls':[call.model_dump()],
            'message':message, 'result':result, 'selected_sunshine_factor':factor}
