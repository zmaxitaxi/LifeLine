"""Validated tools usable by a hosted agent; no provider or LLM is implied."""
from .forecast_models import (EmptyArguments, ForecastLocation, ForecastPlanRequest,
                              PlanForecastArguments)
from .forecast_planner import plan_forecast
from .weather_forecast import ForecastError


def tool_definitions():
    return [dict(name=name, description=description, parameters=model.model_json_schema()) for name,description,model in (
        ('get_clinic_configuration', 'Inspect operator-provided equipment and physical settings. Read only.', EmptyArguments),
        ('get_solar_forecast', 'Fetch today/tomorrow Open-Meteo radiation for the operator-selected clinic coordinates. No invented weather.', EmptyArguments),
        ('plan_forecast', 'Fetch real forecast and run baseline, sunshine-first and MILP with the operator’s midnight battery assumption; compare reduced-sunshine cases. Cannot edit equipment or physical limits.', PlanForecastArguments))]


async def execute_tool(context, call, catalog, service, solve_lock):
    if call.name == 'get_clinic_configuration':
        EmptyArguments.model_validate(call.arguments)
        return {'clinic': context.clinic.model_dump(exclude_unset=True),
                'resolved_config': catalog.resolve(context.clinic).model_dump(),
                'equipment': [e.model_dump() for e in catalog.equipment_for(context.clinic, catalog.resolve(context.clinic))],
                'midnight_battery_assumption_kwh':context.midnight_battery_kwh}
    if call.name == 'get_solar_forecast':
        EmptyArguments.model_validate(call.arguments)
        return await service.get(ForecastLocation(latitude=context.latitude, longitude=context.longitude))
    args = PlanForecastArguments.model_validate(call.arguments)
    if context.midnight_battery_kwh is None:
        raise ForecastError('INVALID_REQUEST', 'What stored battery energy should be assumed at the selected day’s local midnight? Provide and review this assumption before running the forecast simulation.', 422)
    request = ForecastPlanRequest.model_validate({
        'clinic':context.clinic, 'latitude':context.latitude, 'longitude':context.longitude,
        'midnight_battery_kwh':context.midnight_battery_kwh, **args.model_dump()})
    return await plan_forecast(request, catalog, service, solve_lock)


def guided_intent(question):
    """Explicitly limited non-LLM fallback; never silently extract new loads."""
    text = question.lower().strip().rstrip('?.!')
    if text == 'what if the weather is worse than expected? test with 25% of the current sunshine':
        return {'day':'tomorrow', 'reduced_sunshine_factors':[.25,.5]}
    accepted = {
        'can our clinic safely operate tomorrow given the weather forecast',
        'will we have enough electricity tomorrow', 'plan tomorrow’s electricity',
        "plan tomorrow's electricity", 'plan tomorrow', 'plan today',
        'can our clinic operate tomorrow', 'what if tomorrow’s sunshine is 50% lower',
        "what if tomorrow's sunshine is 50% lower", 'what happens if tomorrow’s sunshine is 50% lower',
        "what happens if tomorrow's sunshine is 50% lower", 'prepare for cloudy weather',
    }
    if text not in accepted:
        return None
    return {'day': 'today' if text == 'plan today' else 'tomorrow', 'reduced_sunshine_factors':[.75,.5]}
