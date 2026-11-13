"""Independent sunshine-first rule: no MILP, battery look-ahead, or reserve constraint."""

from .energy_simulator import simulate_baseline


def sunshine_first(inputs):
    available = [max(0., p-c) for p,c in zip(inputs.pv_kwh, inputs.critical_kwh)]
    schedule = []
    for task in inputs.tasks:
        allocation = [0.] * 24
        remaining = task.required_energy_kwh
        # Re-evaluate remaining sunshine after each task, deterministic hour ties.
        for h in sorted(task.allowed_hours, key=lambda h: (-available[h], h)):
            if remaining <= 1e-10:
                break
            amount = min(task.max_power_kw, remaining)
            allocation[h] = amount
            remaining -= amount
            available[h] = max(0., available[h]-amount)
        schedule.append(allocation)
    return simulate_baseline(inputs, schedule)
