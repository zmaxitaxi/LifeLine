"""Bounded intervention search over existing, physically checked simulations.

Candidate sizes are sensitivities, not available products or procurement advice.
No second dispatch model is implemented here.
"""
from starlette.concurrency import run_in_threadpool
from datetime import date
from .energy_types import TOL
from .forecast_models import ForecastLocation, ForecastPlanRequest
from .forecast_planner import forecast_case, LIMITATIONS
from .models import SimulationRequest
from .recovery_models import (RecoveryMetrics, RecoveryOption, RecoveryResponse,
                              InfrastructureChange, WorkChange, BackupDeficit)
from .simulation import simulate_case
from .scenarios import load_weather
from .weather_forecast import ForecastError


def recovery_metrics(plan, config, original_work, postponed=0.):
    m = plan.metrics
    return RecoveryMetrics(essential_requested_kwh=m.critical_requested_kwh,
        essential_served_kwh=m.critical_requested_kwh-m.critical_unserved_kwh,
        essential_unserved_kwh=m.critical_unserved_kwh,
        original_flexible_required_kwh=original_work,
        tested_flexible_required_kwh=m.flexible_requested_kwh,
        flexible_completed_kwh=m.flexible_served_kwh,
        flexible_unfinished_kwh=max(0., original_work-m.flexible_served_kwh),
        explicitly_postponed_kwh=postponed, minimum_battery_kwh=m.min_soc_kwh,
        reserve_shortfall_kwh=max(0., config.reserve_kwh-m.min_soc_kwh),
        reserve_breach_boundaries=m.reserve_breach_boundaries,
        conversion_losses_kwh=m.conversion_loss_kwh)


def rank_key(option):
    m = option.metrics
    # Ignore solver dust, not meaningful deficits. No economic weights.
    return (round(m.essential_unserved_kwh, 6), round(m.reserve_shortfall_kwh, 6),
            len(m.reserve_breach_boundaries), round(m.flexible_unfinished_kwh, 6),
            round(option.normalized_change_magnitude, 6), option.id)


def make_option(identifier, label, kind, result, original, *, existing=False, changes=None):
    plan = result.baseline if existing else result.optimized
    before = original.baseline.metrics
    original_work = original.optimized.metrics.flexible_requested_kwh
    changes = changes or []
    postponed = sum(c.explicitly_postponed_kwh for c in changes)
    metrics = recovery_metrics(plan, result.effective_config, original_work, postponed)
    infrastructure = [InfrastructureChange(field=field, before=getattr(original.effective_config, field),
        after=getattr(result.effective_config, field), unit='kWh' if field=='battery_capacity_kwh' else 'kW')
        for field in ('pv_capacity_kw', 'battery_capacity_kwh', 'max_discharge_kw')
        if abs(getattr(result.effective_config, field)-getattr(original.effective_config, field)) > TOL]
    # Dimensionless sensitivity size, explicitly not cost/installation effort.
    magnitude = sum((c.after-c.before)/max(c.before, 1.) for c in infrastructure)
    old_tasks = {t.task_id:t for t in original.baseline.flexible_tasks}
    moved = 0.
    for task in plan.flexible_tasks:
        old = {a.hour:a.served_kwh for a in old_tasks[task.task_id].allocations}
        new = {a.hour:a.served_kwh for a in task.allocations}
        moved += sum(abs(old.get(h,0.)-new.get(h,0.)) for h in range(24))/2
    magnitude += (moved+postponed)/max(original_work, 1.)
    remaining = list(result.diagnosis.constraints)
    if metrics.essential_unserved_kwh > TOL:
        remaining.append('ESSENTIAL_ENERGY_UNSERVED')
    if metrics.reserve_shortfall_kwh > TOL:
        remaining.append('RESERVE_TARGET_UNMET')
    if metrics.flexible_unfinished_kwh > TOL:
        remaining.append('ORIGINAL_FLEXIBLE_WORK_UNFINISHED')
    if metrics.essential_requested_kwh <= TOL:
        remaining.append('NO_ESSENTIAL_REQUIREMENTS_CONFIGURED')
    met = metrics.essential_requested_kwh > TOL and metrics.essential_unserved_kwh <= TOL and metrics.reserve_shortfall_kwh <= TOL
    return RecoveryOption(id=identifier, label=label, kind=kind, config=result.effective_config,
        plan=plan, simulation=result, metrics=metrics, infrastructure_changes=infrastructure, work_changes=changes,
        essential_shortage_reduction_kwh=before.critical_unserved_kwh-metrics.essential_unserved_kwh,
        minimum_battery_improvement_kwh=metrics.minimum_battery_kwh-before.min_soc_kwh,
        flexible_completion_improvement_kwh=metrics.flexible_completed_kwh-before.flexible_served_kwh,
        normalized_change_magnitude=magnitude, modeled_essential_and_reserve_met=met,
        modeled_all_requirements_met=met and metrics.flexible_unfinished_kwh <= TOL,
        backup_deficits=[BackupDeficit(hour=h.hour, electrical_energy_kwh=h.critical_unserved_kwh)
                        for h in plan.hourly if h.critical_unserved_kwh > TOL],
        remaining_constraints=list(dict.fromkeys(remaining)))


def candidate_sizes(current, limit):
    # Include an absolute increment for zero/tiny systems, without inferring hardware.
    return sorted({min(limit, round(max(current*factor, current+increment), 8))
                   for factor,increment in ((1.25,.5),(1.5,1.),(2.,2.))
                   if min(limit, max(current*factor,current+increment)) > current+TOL})


def candidate_clinic(clinic, **changes):
    return SimulationRequest.model_validate(clinic.model_dump(exclude_unset=True) | changes)


async def generate_recovery_plan(body, catalog, service, solve_lock, progress=None):
    if body.midnight_battery_kwh is None:
        raise ForecastError('INVALID_REQUEST', 'Provide the configured starting battery energy for this planning day.', 422)
    clinic = candidate_clinic(body.clinic, initial_battery_kwh=body.midnight_battery_kwh)
    config = catalog.resolve(clinic)  # before any network call
    equipment = catalog.equipment_for(clinic, config)
    flexible = {e.id:e for e in equipment if e.category=='flexible'}
    if any(identifier not in flexible for identifier in body.optional_load_ids):
        raise ForecastError('INVALID_REQUEST', 'Only explicitly designated flexible equipment IDs may be postponed; essential equipment is protected.', 422)
    forecast = None
    day = None
    if body.weather_mode == 'live_forecast':
        if progress:
            await progress({'type':'activity','id':'recovery-weather','label':'Retrieving the actual weather forecast','status':'running'})
        forecast = await service.get(ForecastLocation(latitude=body.latitude,longitude=body.longitude))
        day = forecast.days[0 if body.day=='today' else 1]
        if not day.simulation_supported:
            raise ForecastError('UNSUPPORTED_FORECAST_DAY',day.warnings[0],422)
        if progress:
            await progress({'type':'activity','id':'recovery-weather','label':'Weather snapshot retrieved','status':'completed'})

    def solve(candidate):
        if forecast:
            request = ForecastPlanRequest(latitude=body.latitude,longitude=body.longitude,clinic=candidate,
                midnight_battery_kwh=body.midnight_battery_kwh,day=body.day,reduced_sunshine_factors=[])
            return forecast_case(catalog,request,day,forecast,body.sunshine_factor)
        factors = candidate.cloud_factors if candidate.cloud_factors is not None else catalog.preset(candidate.scenario).cloud_factors
        return simulate_case(catalog,candidate_clinic(candidate,cloud_factors=[f*body.sunshine_factor for f in factors]))

    async with solve_lock:
        reference = await run_in_threadpool(solve,clinic)
        existing = make_option('existing','Existing fixed schedule','existing',reference,reference,existing=True)
        options = [make_option('reschedule','Reschedule within allowed hours','scheduling',reference,reference)]
        kinds = ('solar','battery','output') if body.focus=='all' else (body.focus,)
        for kind,field,limit in (('solar','pv_capacity_kw',100.),('battery','battery_capacity_kwh',200.),('output','max_discharge_kw',100.)):
            if kind not in kinds:
                continue
            for size in candidate_sizes(getattr(config,field),limit):
                identifier = f'{kind}-{size:g}'
                if progress:
                    await progress({'type':'activity','id':identifier,'label':f'Testing hypothetical {kind} capacity: {size:g} {"kWh" if kind=="battery" else "kW"}','status':'running'})
                result = await run_in_threadpool(solve,candidate_clinic(clinic,**{field:size}))
                options.append(make_option(identifier,f'Test {kind}: {size:g} {"kWh" if kind=="battery" else "kW"}',kind,result,reference))
                if progress:
                    await progress({'type':'activity','id':identifier,'label':f'{kind.capitalize()} sensitivity calculated','status':'completed'})
        if body.optional_load_ids and body.focus in ('all','optional'):
            changes = [WorkChange(equipment_id=e.id,name=e.name,original_required_kwh=e.required_energy_kwh,
                tested_required_kwh=0.,explicitly_postponed_kwh=e.required_energy_kwh) for e in flexible.values() if e.id in body.optional_load_ids]
            changed = [e.model_dump() | ({'required_energy_kwh':0.,'baseline_allocations':[]} if e.id in body.optional_load_ids else {}) for e in equipment]
            # Additional preset protection is made explicit in the unchanged inventory.
            candidate = candidate_clinic(clinic,equipment=changed,**({'additional_critical_kw':0.} if clinic.scenario=='high_demand' else {}))
            result = await run_in_threadpool(solve,candidate)
            options.append(make_option('postpone-optional','Postpone designated optional work','optional',result,reference,changes=changes))
    for rank,option in enumerate(sorted(options,key=rank_key),1):
        option.rank = rank
    options.sort(key=lambda option:option.rank)
    selected = options[0]
    resolving = [o for o in options if o.modeled_all_requirements_met]
    smallest = min(resolving,key=lambda o:(o.normalized_change_magnitude,o.id)) if resolving else None
    triggers = []
    if existing.metrics.essential_unserved_kwh > TOL: triggers.append('ESSENTIAL_SHORTAGE')
    if existing.metrics.reserve_shortfall_kwh > TOL: triggers.append('RESERVE_BREACH')
    if existing.metrics.flexible_unfinished_kwh > TOL: triggers.append('UNFINISHED_FLEXIBLE_WORK')
    baseline = existing.metrics
    operational = next(o for o in options if o.id=='reschedule')
    summary = (f'Existing schedule: {baseline.essential_unserved_kwh:.3f} kWh essential energy unserved; '
        f'{baseline.flexible_unfinished_kwh:.3f} kWh flexible work unfinished. '
        f'Rescheduling leaves {operational.metrics.essential_unserved_kwh:.3f} kWh essential energy unserved and '
        f'{operational.metrics.flexible_unfinished_kwh:.3f} kWh flexible work unfinished. '
        f'Best ranked tested option: {selected.label}. Essential shortage becomes {selected.metrics.essential_unserved_kwh:.3f} kWh; '
        f'minimum battery is {selected.metrics.minimum_battery_kwh:.3f} kWh; original flexible work unfinished is {selected.metrics.flexible_unfinished_kwh:.3f} kWh. ')
    if not resolving:
        summary += 'No tested option meets all original work and reserve requirements. '
    if body.focus=='battery' and selected.metrics.essential_unserved_kwh >= operational.metrics.essential_unserved_kwh-TOL and operational.metrics.essential_unserved_kwh > TOL:
        summary += 'Additional empty battery capacity did not remove the essential deficit; check generation, timing and output power. '
    if operational.backup_deficits:
        summary += (f'After scheduling, additional delivered electrical energy of {operational.metrics.essential_unserved_kwh:.3f} kWh is still needed during local hourly slots '
            +', '.join(f'{d.hour:02d}:00' for d in operational.backup_deficits)+'. ')
    next_action = ('Review the proposed equipment times with staff. An energy technician must verify any hypothetical capacity or output change; '
        'this comparison does not authorize purchases or equipment control.')
    planning_date=day.date if day else (date.fromisoformat(load_weather()['local_date']) if clinic.weather_dataset!='synthetic' else None)
    return RecoveryResponse(weather_mode='demo_weather' if forecast and forecast.weather_mode=='demo' else body.weather_mode,forecast=forecast,planning_date=planning_date,
        timezone=forecast.timezone if forecast else catalog.timezone,sunshine_factor=body.sunshine_factor,reference=reference,
        existing=existing,options=options,problem_detected=bool(triggers),triggers=triggers,
        recommended_option_id=selected.id,smallest_tested_resolving_option_id=smallest.id if smallest else None,
        summary=summary+'Electrical feasibility only; no clinical safety or availability guarantee.',next_action=next_action,
        assumptions=['Each option uses the same weather snapshot, essential equipment, efficiencies, absolute initial stored kWh and reserve target.',
            'Only explicitly listed capacity, output or optional-work changes differ. More battery capacity begins with the same stored energy, not a full charge.',
            'Solar and storage/output candidates are bounded sensitivity sizes, not real products; unchanged charge limits may still constrain them.',
            'Rank: essential shortage, reserve shortfall and breaches, original flexible work unfinished, then normalized modeled change. This is not a cost ranking.',
            'Normalized change sums fractional capacity increases and changed/postponed work divided by original flexible energy (denominators at least 1).',
            'Smallest means smallest among tested candidates under this score, not a global minimum or a hardware sizing recommendation.'],
        limitations=LIMITATIONS+['Only individual interventions are tested; combinations, site installation feasibility, staffing, clinical acceptability and costs require human review.',
            'Postponed optional work remains reported against the original workload; it is not counted as completed or as a full-work success.',
            'Backup values are unmet delivered electrical kWh per hourly slot, not generator ratings, fuel quantities or purchase recommendations.']+
            (forecast.warnings+day.warnings if forecast else ['Explicit scenario mode: historical/synthetic inputs, not a live weather forecast.']))
