"""Deterministic prose built only from computed results and resolved inputs."""

from .energy_types import TOL
from .models import Recommendation, SimulationWarning


def hour_labels(hours):
    return ', '.join(f'{h:02d}:00' for h in hours) or 'none'


def explain(results, inputs, equipment):
    warnings = []
    for plan_name in ('baseline', 'heuristic', 'optimized'):
        metrics = results[plan_name]['metrics']
        if metrics['critical_unserved_kwh'] > TOL:
            warnings.append(SimulationWarning(code='CRITICAL_UNSERVED', plan=plan_name,
                message=f"{metrics['critical_unserved_kwh']:.6f} kWh of critical demand is unserved "
                        f"in slots starting {hour_labels(metrics['critical_shortage_hours'])}."))
        if metrics['min_soc_kwh'] < inputs.battery.reserve_kwh-TOL:
            warnings.append(SimulationWarning(code='RESERVE_BELOW_TARGET', plan=plan_name,
                message=f"Minimum stored energy {metrics['min_soc_kwh']:.6f} kWh is below the "
                        f"{inputs.battery.reserve_kwh:.6f} kWh target; breach boundaries: "
                        f"{metrics['reserve_breach_boundaries']} (0–24)."))
        if metrics['flexible_deferred_kwh'] > TOL:
            warnings.append(SimulationWarning(code='FLEXIBLE_DEFERRED', plan=plan_name,
                message=f"{metrics['flexible_deferred_kwh']:.6f} kWh of optional work is unserved "
                        'within this horizon; no next-day completion is guaranteed.'))

    optimized = results['optimized']
    metrics = optimized['metrics']
    recommendations = []
    if metrics['critical_unserved_kwh'] > TOL:
        rate_limited = [h for h,(c,p) in enumerate(zip(inputs.critical_kwh, inputs.pv_kwh))
                        if c-p > inputs.battery.max_discharge_kw+TOL]
        reason = (f"Demand exceeds solar plus the {inputs.battery.max_discharge_kw:g} kW battery "
                  f"output limit in slots starting {hour_labels(rate_limited)}. " if rate_limited else '')
        recommendations.append(Recommendation(severity='critical', title='Critical demand cannot be fully supplied',
            explanation=reason + f"Even with optional work disabled, {metrics['critical_unserved_kwh']:.6f} kWh "
                        'remains unserved under the modeled constraints. Flexible scheduling cannot eliminate this shortage.',
            hours=metrics['critical_shortage_hours']))
    if metrics['min_soc_kwh'] < inputs.battery.reserve_kwh-TOL:
        recommendations.append(Recommendation(severity='warning', title='Reserve target remains out of reach',
            explanation=f"The strongest feasible reserve floor is below the {inputs.battery.reserve_kwh:g} kWh "
                        'target under these inputs. Critical demand takes precedence; the reserve is a target, not physical zero.'))

    comparison = results['comparison']
    old = results['baseline']['metrics']
    if comparison['same_flexible_work_completed']:
        recommendations.append(Recommendation(severity='info', title='Same flexible work completed',
            explanation=f"Both schedules complete {metrics['flexible_served_kwh']:.6f} kWh of optional work. "
                        f"Optimized minus baseline battery at midnight: {comparison['battery_preserved_at_midnight_kwh']:+.6f} kWh; "
                        f"daily minimum: {comparison['minimum_battery_improvement_kwh']:+.6f} kWh. "
                        f"Baseline minus optimized conversion losses: {comparison['conversion_loss_reduction_kwh']:+.6f} kWh. "
                        'These are separate quantities and must not be added together.'))
    else:
        recommendations.append(Recommendation(severity='warning', title='Work completion differs between schedules',
            explanation=f"Baseline completes {old['flexible_served_kwh']:.6f} kWh; optimized completes "
                        f"{metrics['flexible_served_kwh']:.6f} kWh. Battery differences include a change in work completed "
                        'and must not be presented as a same-work scheduling benefit.'))

    names = {item.id: item.name for item in equipment}
    for task in optimized['flexible_tasks']:
        hours = [a['hour'] for a in task['allocations'] if a['served_kwh'] > TOL]
        recommendations.append(Recommendation(severity='warning' if task['deferred_kwh'] > TOL else 'info',
            title=f"Schedule: {names[task['task_id']]}", task_id=task['task_id'], hours=hours,
            explanation=f"Serve {task['served_kwh']:.6f} of {task['requested_kwh']:.6f} kWh in slots starting "
                        f"{hour_labels(hours)}; defer {task['deferred_kwh']:.6f} kWh within this horizon. "
                        'Allocations respect the allowed windows and the ordered critical/reserve constraints.'))

    recommendations.append(Recommendation(severity='info', title=(
        'Sunshine-first matches key metrics' if comparison['heuristic_matches_optimizer_metrics'] else
        'Sunshine-first and MILP outcomes differ'), explanation=(
        'The simple rule matches critical coverage, flexible service, minimum/final battery, and conversion losses '
        'within 0.000001 kWh in this case. Equivalent task hours may differ; no optimizer superiority is claimed.'
        if comparison['heuristic_matches_optimizer_metrics'] else
        'Compare all three plans, including their work completion and warnings. The sunshine-first rule has no '
        'battery look-ahead or reserve constraint; a higher battery alone does not establish a better outcome.')))
    return warnings, recommendations
