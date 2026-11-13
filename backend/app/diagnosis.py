"""Diagnostic bounds: evidence of limitations, not certified system sizing."""
from .energy_types import TOL


def diagnose(inputs, results):
    optimized = results['optimized']['metrics']
    baseline = results['baseline']['metrics']
    rate_hours = [h for h,(c,p) in enumerate(zip(inputs.critical_kwh, inputs.pv_kwh))
                  if c > p+inputs.battery.max_discharge_kw+TOL]
    # Optimistic supply bound ignores storage losses/curtailment. A shortfall
    # even against this bound proves more usable supply/less demand is needed.
    energy_gap = max(0.,sum(inputs.critical_kwh)-sum(inputs.pv_kwh)
                     -inputs.battery.initial_battery_kwh*inputs.battery.discharge_efficiency)
    constrained_tasks = [t.id for t in inputs.tasks
                         if t.required_energy_kwh > t.max_power_kw*len(t.allowed_hours)+TOL]
    reasons = []
    if rate_hours:
        reasons.append('DISCHARGE_POWER_LIMIT')
    if energy_gap > TOL:
        reasons.append('TOTAL_ENERGY_DEFICIT')
    if optimized['critical_unserved_kwh'] > TOL:
        assessment = 'INFRASTRUCTURE_LIMITATION'
        if not rate_hours and energy_gap <= TOL:
            reasons.append('STORAGE_OR_TIMING_LIMIT')
        explanation = ('Essential requirements remain unserved even with optional work disabled. '
                       'Use the Capacity Explorer to test supply, stored energy, and output limits separately. '
                       'More battery capacity alone may not fix a power bottleneck.')
    elif optimized['min_soc_kwh'] < inputs.battery.reserve_kwh-TOL:
        assessment = 'RESERVE_AT_RISK'
        explanation = 'Essential energy is covered for this modeled day, but the reserve target cannot be maintained. Optional work may be deferred.'
    elif (baseline['critical_unserved_kwh'] > TOL or
          results['comparison']['same_flexible_work_completed'] and
          (results['comparison']['battery_preserved_at_midnight_kwh'] > TOL or
           results['comparison']['conversion_loss_reduction_kwh'] > TOL)):
        assessment = 'SCHEDULING_OPPORTUNITY'
        explanation = 'The computed operating plan improves the current schedule. Check completed work and remaining warnings before interpreting the difference.'
    else:
        assessment = 'ADEQUATE_CAPACITY'
        explanation = 'Essential requirements and the reserve target are met in this modeled day. There may be little scheduling benefit; this does not guarantee future availability.'
    if constrained_tasks:
        reasons.append('TASK_WINDOW_LIMIT')
    return dict(assessment=assessment, explanation=explanation, constraints=reasons,
                discharge_limited_hours=rate_hours, optimistic_energy_deficit_kwh=energy_gap,
                window_limited_tasks=constrained_tasks)
