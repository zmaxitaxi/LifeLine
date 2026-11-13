"""Physical baseline and contract-shaped results shared with the optimizer."""

import math
from .energy_types import ModelInput, HOURS, TOL


class NumericalError(RuntimeError):
    code = "NUMERICAL_ERROR"


def build_result(inputs: ModelInput, energy, charge, discharge, curtail, unmet,
                 allocations, planned=None):
    """Verify raw flows before serialization. Values are never rounded/clamped."""
    b = inputs.battery
    if planned is None:
        planned = allocations
    arrays = [energy, charge, discharge, curtail, unmet, *allocations, *planned]
    if (len(energy) != 25 or any(len(a) != 24 for a in arrays[1:])
            or len(allocations) != len(inputs.tasks) or len(planned) != len(inputs.tasks)):
        raise NumericalError("Invalid dispatch dimensions")
    if any(not math.isfinite(float(v)) for a in arrays for v in a):
        raise NumericalError("Non-finite dispatch")

    def check(ok, message):
        if not ok:
            raise NumericalError(message)

    check(abs(energy[0] - b.initial_battery_kwh) <= TOL, "Initial battery changed")
    check(all(-TOL <= e <= b.battery_capacity_kwh + TOL for e in energy), "Battery bounds")
    task_results = []
    for task, served, requested in zip(inputs.tasks, allocations, planned):
        for h in range(HOURS):
            cap = task.max_power_kw if h in task.allowed_hours else 0
            check(-TOL <= served[h] <= requested[h] + TOL <= cap + 2*TOL, "Task allocation bounds")
        total = float(sum(served))
        check(total <= task.required_energy_kwh + TOL, "Task over-served")
        task_results.append(dict(task_id=task.id, requested_kwh=task.required_energy_kwh,
                                 served_kwh=total, deferred_kwh=task.required_energy_kwh-total,
                                 allocations=[dict(hour=h, served_kwh=float(v))
                                              for h, v in enumerate(served) if v > 0]))
    hourly = []
    for h in range(HOURS):
        p, c = inputs.pv_kwh[h], inputs.critical_kwh[h]
        q, d, w, u = charge[h], discharge[h], curtail[h], unmet[h]
        f = sum(a[h] for a in allocations)
        check(-TOL <= q <= b.max_charge_kw + TOL and -TOL <= d <= b.max_discharge_kw + TOL, "Battery rate")
        check(min(q, d) <= TOL, "Simultaneous charging/discharging")
        check(-TOL <= u <= c + TOL and -TOL <= w <= p + TOL, "Shortage/curtailment bounds")
        check(abs(p+d-(c-u+f+q+w)) <= TOL, "Hourly bus balance")
        check(abs(energy[h+1]-energy[h]-b.charge_efficiency*q+d/b.discharge_efficiency) <= TOL, "Battery balance")
        requested = sum(a[h] for a in planned)
        hourly.append(dict(hour=h, pv_kwh=float(p), critical_requested_kwh=float(c),
                           critical_served_kwh=float(c-u), critical_unserved_kwh=float(u),
                           flexible_planned_kwh=float(requested), flexible_served_kwh=float(f),
                           flexible_unserved_kwh=float(requested-f), charge_input_kwh=float(q),
                           discharge_output_kwh=float(d), curtailed_kwh=float(w),
                           soc_start_kwh=float(energy[h]), soc_end_kwh=float(energy[h+1])))
    critical_total, shortfall = sum(inputs.critical_kwh), float(sum(unmet))
    check(-TOL <= shortfall <= critical_total+TOL, "Aggregate critical shortage bounds")
    flex_requested = sum(t.required_energy_kwh for t in inputs.tasks)
    flex_served = sum(t["served_kwh"] for t in task_results)
    losses = float((1-b.charge_efficiency)*sum(charge) + (1/b.discharge_efficiency-1)*sum(discharge))
    check(abs(b.initial_battery_kwh + sum(inputs.pv_kwh) - energy[-1]
              - (critical_total-shortfall) - flex_served - sum(curtail)-losses) <= TOL, "Daily energy balance")
    minimum = float(min(energy))
    status = ("CRITICAL_SHORTAGE" if shortfall > TOL else
              "RESERVE_AT_RISK" if minimum < b.reserve_kwh-TOL else "OK")
    metrics = dict(total_solar_kwh=float(sum(inputs.pv_kwh)), critical_requested_kwh=float(critical_total),
                   critical_unserved_kwh=shortfall,
                   # Ratio first yields exactly 100 for zero shortfall. Bound
                   # only reporting residue after validating raw energy flows.
                   critical_coverage_pct=min(100., max(0., 100*(1-shortfall/critical_total))) if critical_total else None,
                   min_soc_kwh=minimum, final_soc_kwh=float(energy[-1]),
                   flexible_requested_kwh=float(flex_requested), flexible_served_kwh=float(flex_served),
                   flexible_deferred_kwh=float(flex_requested-flex_served), curtailed_kwh=float(sum(curtail)),
                   conversion_loss_kwh=losses,
                   critical_shortage_hours=[h for h,u in enumerate(unmet) if u > TOL],
                   reserve_breach_boundaries=[h for h,e in enumerate(energy) if e < b.reserve_kwh-TOL])
    def clean(value):
        # Raw flows were checked above. Remove display-only floating-point dust.
        if isinstance(value, float) and abs(value) < 1e-10:
            return 0.
        if isinstance(value, dict):
            return {k: clean(v) for k, v in value.items()}
        if isinstance(value, list):
            return [clean(v) for v in value]
        return value
    return clean(dict(status=status, hourly=hourly, metrics=metrics, flexible_tasks=task_results))


def simulate_baseline(inputs: ModelInput, requested_schedule=None):
    """Fixed requested schedule; critical first, then flexible, then storage.

    Within a slot tasks receive energy in the supplied task order. Missed
    work stays unserved; the reserve target does not constrain this baseline.
    """
    b = inputs.battery
    schedule = [t.baseline_kwh for t in inputs.tasks] if requested_schedule is None else requested_schedule
    if len(schedule) != len(inputs.tasks) or any(len(a) != HOURS for a in schedule):
        raise ValueError("Invalid requested schedule")
    energy = [b.initial_battery_kwh]
    charge, discharge, curtail, unmet = [], [], [], []
    allocations = [[0.] * HOURS for _ in inputs.tasks]
    for h in range(HOURS):
        available = inputs.pv_kwh[h]
        output = min(b.max_discharge_kw, energy[-1]*b.discharge_efficiency)
        served = min(inputs.critical_kwh[h], available+output)
        used = max(0., served-available)
        available = max(0., available-served)
        output -= used
        for j, task in enumerate(inputs.tasks):
            f = min(schedule[j][h], available+output)
            allocations[j][h] = f
            battery_used = max(0., f-available)
            available = max(0., available-f)
            output -= battery_used
            used += battery_used
        e = energy[-1]-used/b.discharge_efficiency
        q = min(available, b.max_charge_kw, max(0., b.battery_capacity_kwh-e)/b.charge_efficiency)
        energy.append(e+b.charge_efficiency*q)
        charge.append(q)
        discharge.append(used)
        curtail.append(available-q)
        unmet.append(inputs.critical_kwh[h]-served)
    return build_result(inputs, energy, charge, discharge, curtail, unmet,
                        allocations, schedule)
