"""Read-only what-if tools. No operator configuration is ever mutated."""
import re
from .agent_models import (CapacityArguments, CapacityResult, CapacitySample,
                           FixedRequirementArguments, RequirementResult)
from .energy_types import TOL
from .forecast_models import ForecastLocation, ForecastPlanRequest
from .forecast_planner import plan_forecast, computed_assessment
from .models import SimulationRequest
from .weather_forecast import ForecastError


class SnapshotService:
    def __init__(self, forecast):
        self.forecast = forecast

    async def get(self, location):
        return self.forecast


def plan_request(context, day, factors=None, clinic=None):
    if context.midnight_battery_kwh is None:
        raise ForecastError('INVALID_REQUEST', 'Review the stored battery energy assumed at local midnight before planning.', 422)
    return ForecastPlanRequest(latitude=context.latitude, longitude=context.longitude,
        clinic=clinic or context.clinic, midnight_battery_kwh=context.midnight_battery_kwh,
        day=day, reduced_sunshine_factors=factors if factors is not None else [])


def explicit_requirement(arguments, questions):
    """Reject invented ratings/times. All four numbers need user evidence.

    These checks intentionally support a narrower grammar than the local LLM.
    Unknown appliance cycles are never inferred from a model's knowledge.
    """
    text = ' '.join(questions).lower().replace('’', "'")
    ratings = [float(v) * (1 if unit.startswith(('kw', 'kilowatt')) else .001)
               for v, unit in re.findall(r'(?<![\w.])(-?\d+(?:\.\d+)?)\s*(kw|kilowatts?|watts?|w)\b', text)]
    durations = [float(v) for v in re.findall(r'(?<![\w.])(-?\d+(?:\.\d+)?)\s*(?:hours?|hrs?)\b', text)]
    starts = [clock(v, ampm) for v, ampm in re.findall(r'(?:from|start(?:ing)?(?:\s+at)?|earliest(?:\s+start)?(?:\s+is)?)\s+(\d{1,2})(?::00)?\s*(am|pm)?\b', text)]
    ends = [clock(v, ampm) for v, ampm in re.findall(r'(?:before|by|until|deadline(?:\s+is)?)\s+(\d{1,2})(?::00)?\s*(am|pm)?\b', text)]
    if re.search(r'(?:before|by|until)\s+noon', text):
        ends.append(12)
    for field, value, values in [('power', arguments.power_kw, ratings), ('duration', arguments.duration_hours, durations),
                                  ('earliest_start', arguments.earliest_start, starts), ('deadline', arguments.deadline, ends)]:
        if not any(v is not None and abs(value-v) <= TOL for v in values):
            return field
    return None


def clock(value, ampm):
    hour = int(value)
    if ampm:
        return hour % 12 + (12 if ampm == 'pm' else 0) if 1 <= hour <= 12 else None
    return hour if 0 <= hour <= 24 else None


async def evaluate_fixed_requirement(context, args: FixedRequirementArguments, catalog, service, lock):
    # Capture one weather snapshot for the unchanged clinic and every candidate.
    forecast = await service.get(ForecastLocation(latitude=context.latitude, longitude=context.longitude))
    frozen = SnapshotService(forecast)
    original = await plan_forecast(plan_request(context, args.day), catalog, frozen, lock)
    config = catalog.resolve(context.clinic)
    equipment = [e.model_dump() for e in catalog.equipment_for(context.clinic, config)]
    if len(equipment) >= 20:
        raise ForecastError('INVALID_REQUEST', 'The equipment limit is reached. Review the inventory before testing another requirement.', 422)
    task_id = 'additional_fixed_requirement'
    while any(e['id'] == task_id for e in equipment):
        task_id += '_new'
    candidates = []
    for start in range(args.earliest_start, args.deadline-args.duration_hours+1):
        # New hypothetical load only; never remove/reclassify/move existing loads.
        extra = dict(id=task_id, name=args.name+' (fixed hourly energy check)', category='critical',
                     power_kw=args.power_kw, required_hours=list(range(start,start+args.duration_hours)))
        changes={'equipment':equipment+[extra]}
        if context.clinic.scenario == 'high_demand':
            changes['additional_critical_kw']=0.
        candidate = SimulationRequest.model_validate(context.clinic.model_dump(exclude_unset=True) | changes)
        result = await plan_forecast(plan_request(context, args.day, clinic=candidate), catalog, frozen, lock)
        m = result.plan.optimized.metrics
        candidates.append((m.critical_unserved_kwh, len(m.reserve_breach_boundaries), m.flexible_deferred_kwh,
                           -m.min_soc_kwh, -m.final_soc_kwh, start, result))
    *_, start, proposed = min(candidates, key=lambda x:x[:-1])
    supplied=proposed.plan.optimized.metrics.critical_unserved_kwh <= TOL
    message = (f'Hypothetical additional requirement: {args.name}, {args.power_kw:g} kW for {args.duration_hours} consecutive hourly slots. '
               f'Of {len(candidates)} allowed starts, the selected energy check is {start:02d}:00–{start+args.duration_hours:02d}:00 '
               f'({forecast.timezone}), before the {args.deadline:02d}:00 deadline. '+computed_assessment(proposed.plan)+
               ' Existing protected equipment is unchanged. This proposal is not applied to the clinic inventory. '
               'It evaluates fixed consecutive hourly demand, not medical-cycle effectiveness, temperature, starting surges, or clinical safety.')
    if not supplied:
        message += ' No tested start supplies all essential requirements. Do not treat the added cycle as completed; additional resources or explicit operator review are needed.'
    return RequirementResult(name=args.name,start_hour=start,end_hour=start+args.duration_hours,
        candidates_evaluated=len(candidates),essential_requirements_fully_supplied=supplied,
        original=original,proposed=proposed,explanation=message)


async def explore_capacity(context, args: CapacityArguments, catalog, service, lock):
    forecast = await service.get(ForecastLocation(latitude=context.latitude, longitude=context.longitude))
    frozen = SnapshotService(forecast)
    config = catalog.resolve(context.clinic)
    current = config.battery_capacity_kwh
    samples = []
    resolution = .25

    async def sample(capacity):
        clinic = SimulationRequest.model_validate(context.clinic.model_dump(exclude_unset=True) | {'battery_capacity_kwh':capacity})
        factors = [] if args.sunshine_factor == 1 else [args.sunshine_factor]
        result = await plan_forecast(plan_request(context, args.day, factors, clinic), catalog, frozen, lock)
        plan = result.plan if args.sunshine_factor == 1 else result.uncertainty_cases[0].plan
        m = plan.optimized.metrics
        meets = (m.critical_requested_kwh > TOL and m.critical_unserved_kwh <= TOL and not m.reserve_breach_boundaries
                 and (args.target == 'essential' or m.flexible_deferred_kwh <= TOL))
        point = CapacitySample(battery_capacity_kwh=capacity,essential_unmet_kwh=m.critical_unserved_kwh,
            flexible_deferred_kwh=m.flexible_deferred_kwh,minimum_battery_kwh=m.min_soc_kwh,
            reserve_breached=bool(m.reserve_breach_boundaries),meets_target=meets)
        samples.append(point)
        return point

    first = await sample(current)
    upper = None
    if first.meets_target:
        upper = current
        explanation = 'The current battery capacity meets this modeled target; no additional capacity is indicated by this single-day check.'
    else:
        last = await sample(200.) if current < 200 else first
        if not last.meets_target:
            explanation = 'Increasing storage alone did not meet this target even at the search limit. More capacity adds no starting energy and cannot increase battery output power or solar supply. Review the actual shortage and supply constraints with a technician.'
        else:
            low, upper = current, 200.
            while upper-low > resolution+TOL:
                mid = round((low+upper)/2,8)
                if (await sample(mid)).meets_target:
                    upper = mid
                else:
                    low = mid
            explanation = (f'A tested capacity of {upper:.3f} kWh ({upper-current:.3f} kWh above the current {current:.3f} kWh) '
                f'meets this modeled target. The transition is bracketed within {resolution:g} kWh; this is not a hardware sizing or procurement recommendation.')
    return CapacityResult(target=args.target,sunshine_factor=args.sunshine_factor,current_capacity_kwh=current,
        tested_capacity_kwh=upper,additional_capacity_kwh=None if upper is None else max(0.,upper-current),
        resolution_kwh=resolution,search_limit_kwh=200.,samples=samples,explanation=explanation,
        assumptions=['Same forecast snapshot, equipment, absolute reserve, initial stored kWh, efficiencies, and charge/discharge limits at every tested capacity.',
                     'A larger battery is not assumed to arrive charged. More empty storage cannot fix inadequate input energy or output power.',
                     'Single-day idealized capacity sensitivity; no multi-day autonomy, degradation, cost, backup generator, or installation design.'])
