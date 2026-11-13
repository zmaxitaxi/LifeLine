"""Pure model handoff: three physically checked plans from identical inputs."""

from .energy_types import TOL
from .energy_simulator import simulate_baseline
from .heuristic import sunshine_first
from .optimizer import optimize


def compare_schedules(inputs):
    baseline = simulate_baseline(inputs)
    heuristic = sunshine_first(inputs)
    optimized = optimize(inputs)
    old, rule, new = [p['metrics'] for p in (baseline, heuristic, optimized)]
    evening_min = lambda plan: min(plan['hourly'][17]['soc_end_kwh'],
                                   *(r['soc_end_kwh'] for r in plan['hourly'][18:]))
    same_work = all(abs(a['served_kwh']-b['served_kwh']) <= TOL
                    for a,b in zip(baseline['flexible_tasks'], optimized['flexible_tasks']))
    matched_keys = ('critical_unserved_kwh', 'flexible_served_kwh', 'min_soc_kwh',
                    'final_soc_kwh', 'conversion_loss_kwh')
    comparison = dict(
        same_flexible_work_completed=same_work,
        battery_preserved_at_midnight_kwh=new['final_soc_kwh']-old['final_soc_kwh'],
        minimum_battery_improvement_kwh=new['min_soc_kwh']-old['min_soc_kwh'],
        evening_minimum_improvement_kwh=evening_min(optimized)-evening_min(baseline),
        conversion_loss_reduction_kwh=old['conversion_loss_kwh']-new['conversion_loss_kwh'],
        heuristic_matches_optimizer_metrics=all(abs(rule[k]-new[k]) <= TOL for k in matched_keys),
    )
    return dict(baseline=baseline, heuristic=heuristic, optimized=optimized, comparison=comparison)
