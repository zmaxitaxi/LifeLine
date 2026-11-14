"""Forecast profiles feed the original simulator/heuristic/MILP unchanged."""
from dataclasses import replace
from starlette.concurrency import run_in_threadpool
from .comparison import compare_schedules
from .diagnosis import diagnose
from .energy_types import TOL
from .explanations import explain, hour_labels
from .forecast_models import ForecastLocation, ForecastPlanResponse, ForecastStressCase
from .models import SimulationRequest, SimulationResponse
from .solar_forecast import pv_from_irradiance
from .weather_forecast import ForecastError
from .activity import report


LIMITATIONS = [
    'This evaluates energy feasibility under stated assumptions, not whether clinical operations are safe. No electricity guarantee or equipment control.',
    'The starting battery is the operator’s assumed stored energy at local midnight. Tomorrow’s charge is not predicted by carrying today’s simulation forward.',
    'Today is a complete local calendar-day scenario, including elapsed hours; this is not a real-time remaining-day controller.',
    'PV energy = rated kW × hourly horizontal irradiation (kWh/m²) ÷ 1 kW/m² × existing performance ratio. Tilt, shading, temperature and inverter clipping are omitted.',
    'Reduced-sunshine cases are user-chosen sensitivity tests, not confidence intervals or calibrated forecast probabilities. Each case is independently reoptimized.',
    'Essential equipment hours and requirements stay fixed. Flexible energy is divisible and interruptible; medical appliance cycles and staffing constraints require separate validation.',
    'No grid, generator, sub-hour starting surge, degradation, or multi-day reliability model is included.',
]


def forecast_case(catalog, body, day, forecast, factor):
    # Replace the weather source and explicitly supplied midnight energy only.
    # All equipment, durations, windows and physical limits remain unchanged.
    request = SimulationRequest.model_validate(body.clinic.model_dump(exclude_unset=True) | {
        'initial_battery_kwh': body.midnight_battery_kwh,
        'weather_dataset': 'synthetic', 'cloud_factors': [factor]*24})
    config = catalog.resolve(request)
    original = catalog.build_inputs(request, config)
    pv = pv_from_irradiance(config.pv_capacity_kw, tuple(h.irradiance_kwh_m2*factor for h in day.hours), catalog.pv_model.performance_ratio)
    inputs = replace(original, pv_kwh=pv)
    results = compare_schedules(inputs)
    equipment = catalog.equipment_for(request, config)
    warnings, recommendations = explain(results, inputs, equipment)
    return SimulationResponse(scenario=request.scenario, scenario_name=catalog.preset(request.scenario).name,
        data_source='mixed', weather_dataset='synthetic-demo' if forecast.weather_mode=='demo' else 'open-meteo-forecast', timezone=forecast.timezone,
        cloud_factors=[factor]*24, effective_config=config, pv_performance_ratio=catalog.pv_model.performance_ratio,
        input_provenance={'equipment': 'user_entered_unverified' if request.equipment is not None else 'synthetic',
                          'weather': 'LifeLine_synthetic_demo_weather' if forecast.weather_mode=='demo' else 'Open_Meteo_weather_model_forecast',
                          'model': 'Horizontal irradiance approximation; reduced-sunshine factor applied once; preset cloud curve replaced.',
                          'initial_battery': 'Operator assumption at selected day’s local midnight; not a carried-forward prediction.'},
        equipment=equipment, assumptions=[f'24 hourly slots for {day.date.isoformat()} in {forecast.timezone}.',
            f'{forecast.source}: {forecast.data_kind}; generated/retrieved at {forecast.retrieved_at.isoformat()}; cache status: {forecast.cache_status}.',
            f'Radiation profile multiplied by {factor:g}; identical profile supplied to all three schedules.']+forecast.warnings+LIMITATIONS,
        diagnosis=diagnose(inputs, results), status=results['optimized']['status'], baseline=results['baseline'],
        heuristic=results['heuristic'], optimized=results['optimized'], comparison=results['comparison'],
        warnings=warnings, recommendations=recommendations)


def computed_assessment(plan):
    m = plan.optimized.metrics
    if m.critical_requested_kwh <= TOL:
        return 'No essential-equipment requirements are configured. Add and review them before assessing essential power; a zero-demand result cannot establish reliability.'
    if m.critical_unserved_kwh > TOL:
        return f'The model cannot supply all essential equipment: {m.critical_unserved_kwh:.3f} kWh is unserved. Scheduling alone cannot resolve this modeled shortage.'
    if m.min_soc_kwh < plan.effective_config.reserve_kwh-TOL:
        return f'Essential demand is covered in this modeled day, but the battery minimum is {m.min_soc_kwh:.3f} kWh, below the {plan.effective_config.reserve_kwh:.3f} kWh reserve target.'
    return f'Under the forecast and stated midnight battery assumption, essential demand is covered in the model. Minimum battery energy is {m.min_soc_kwh:.3f} kWh; flexible work deferred is {m.flexible_deferred_kwh:.3f} kWh. This is not a safety or availability guarantee.'


def computed_actions(plan):
    names = {e.id:e.name for e in plan.equipment}
    actions = []
    if plan.optimized.metrics.critical_unserved_kwh > TOL:
        actions.append('Review additional energy supply and output-power limits with an energy technician before relying on this plan.')
    for task in plan.optimized.flexible_tasks:
        times = hour_labels([a.hour for a in task.allocations if a.served_kwh > TOL])
        actions.append(f'{names[task.task_id]}: {task.served_kwh:.3f} kWh in hourly slots starting {times} ({plan.timezone}); {task.deferred_kwh:.3f} kWh deferred. Review exact partial-hour allocations below.')
    if not actions:
        actions.append('Keep protected equipment hours unchanged; no flexible equipment is configured for rescheduling.')
    return actions


async def plan_forecast(body, catalog, service, solve_lock, progress=None):
    # Validate cross-field hardware bounds before making any external request.
    catalog.resolve(SimulationRequest.model_validate(body.clinic.model_dump(exclude_unset=True) | {'initial_battery_kwh':body.midnight_battery_kwh}))
    await report(progress, 'forecast', 'Retrieving the Open-Meteo forecast')
    forecast = await service.get(ForecastLocation(latitude=body.latitude, longitude=body.longitude))
    await report(progress, 'forecast', f'Weather forecast retrieved ({forecast.cache_status})', 'completed')
    day = forecast.days[0 if body.day == 'today' else 1]
    if not day.simulation_supported:
        raise ForecastError('UNSUPPORTED_FORECAST_DAY', day.warnings[0], 422)
    factors = [1.] + body.reduced_sunshine_factors
    await report(progress, 'simulation', 'Running the electricity model and checking equipment needs')
    async with solve_lock:
        # Same forecast snapshot, physical constraints, equipment and initial
        # energy for every case; only the explicitly named factor differs.
        plans = []
        for factor in factors:
            plans.append(await run_in_threadpool(forecast_case, catalog, body, day, forecast, factor))
    await report(progress, 'simulation', 'Energy calculations and schedules verified', 'completed')
    return ForecastPlanResponse(forecast=forecast, planning_date=day.date, midnight_battery_kwh=body.midnight_battery_kwh,
        initial_battery_basis=LIMITATIONS[1], plan=plans[0],
        uncertainty_cases=[ForecastStressCase(sunshine_factor=f, plan=p) for f,p in zip(factors[1:],plans[1:])],
        assessment=computed_assessment(plans[0]), actions=computed_actions(plans[0]),
        limitations=LIMITATIONS+forecast.warnings+day.warnings)
