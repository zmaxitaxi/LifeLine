"""Ordered MILP objectives for divisible flexible loads and binary battery mode."""

from time import monotonic
from .energy_types import ModelInput, HOURS, TOL, finite
from .energy_simulator import NumericalError, build_result


class SolverError(RuntimeError):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def optimize(inputs: ModelInput, time_limit_seconds=5.):
    """Return a verified PlanResult, or raise a typed technical failure.

    No API or file access. Requires an optimal result at each stage; never
    treats a solver failure as evidence of physical critical shortage.
    """
    finite(time_limit_seconds, "solver time budget", high=5, exclusive_low=True)
    try:
        import numpy as np
        from scipy.optimize import milp, Bounds, LinearConstraint
    except ImportError as exc:
        raise SolverError("SOLVER_UNAVAILABLE", "Install the model requirements") from exc

    deadline = monotonic()+time_limit_seconds
    b = inputs.battery
    # e[25], charge/discharge/curtail/unmet/mode[24 each], reserve floor,
    # then one continuous 24-slot allocation vector per task.
    e = np.arange(25)
    q, d, w, u, z = [np.arange(25+24*i, 49+24*i) for i in range(5)]
    r = 145
    x = [np.arange(146+24*j, 170+24*j) for j in range(len(inputs.tasks))]
    size = 146+24*len(inputs.tasks)
    lower = np.zeros(size)
    upper = np.full(size, np.inf)
    upper[e] = b.battery_capacity_kwh
    lower[0] = upper[0] = b.initial_battery_kwh
    upper[q], upper[d] = b.max_charge_kw, b.max_discharge_kw
    upper[w], upper[u], upper[z], upper[r] = inputs.pv_kwh, inputs.critical_kwh, 1, b.reserve_kwh
    for task_indices in x:
        upper[task_indices] = 0  # critical/reserve feasibility without flexible work
    integrality = np.zeros(size)
    integrality[z] = 1
    rows, lows, highs = [], [], []

    def row(terms, low, high):
        a = np.zeros(size)
        for index, coefficient in terms:
            a[index] += coefficient
        rows.append(a)
        lows.append(low)
        highs.append(high)

    for h in range(HOURS):
        demand_minus_pv = inputs.critical_kwh[h]-inputs.pv_kwh[h]
        row([(d[h], 1), (u[h], 1), (q[h], -1), (w[h], -1)]
            + [(indices[h], -1) for indices in x], demand_minus_pv, demand_minus_pv)
        row([(e[h+1], 1), (e[h], -1), (q[h], -b.charge_efficiency),
             (d[h], 1/b.discharge_efficiency)], 0, 0)
        row([(q[h], 1), (z[h], -b.max_charge_kw)], -np.inf, 0)
        row([(d[h], 1), (z[h], b.max_discharge_kw)], -np.inf, b.max_discharge_kw)
    for boundary in e:
        row([(boundary, 1), (r, -1)], 0, np.inf)
    for task, indices in zip(inputs.tasks, x):
        row([(i, 1) for i in indices], -np.inf, task.required_energy_kwh)

    def objective(indices, coefficient=1):
        cost = np.zeros(size)
        cost[indices] = coefficient
        return cost

    def solve(cost, freeze=True):
        remaining = deadline-monotonic()
        if remaining <= 0:
            raise SolverError("SOLVER_TIME_LIMIT", "Total solve budget exhausted")
        matrix = np.array(rows)
        try:
            result = milp(cost, integrality=integrality, bounds=Bounds(lower, upper),
                          constraints=LinearConstraint(matrix, lows, highs),
                          options={"time_limit": remaining, "mip_rel_gap": 0.})
        except Exception as exc:
            raise SolverError("SOLVER_UNAVAILABLE", "MILP solver failed to execute") from exc
        if result.status == 1 or monotonic() > deadline:
            raise SolverError("SOLVER_TIME_LIMIT", "Optimal solve exceeded the time budget")
        if result.status != 0 or not result.success or result.x is None:
            raise NumericalError(f"MILP did not establish an optimum (status {result.status})")
        values = result.x
        activity = matrix @ values
        if (not np.isfinite(values).all()
                or np.any(values < lower-TOL) or np.any(values > upper+TOL)
                or np.any(activity < np.array(lows)-TOL)
                or np.any(activity > np.array(highs)+TOL)
                or np.any(abs(values[z]-np.rint(values[z])) > TOL)):
            raise NumericalError("MILP result failed raw constraint verification")
        if freeze:
            optimum = float(cost @ values)
            # Equality freezes prevent tolerance losses accumulating across stages.
            rows.append(cost.copy())
            lows.append(optimum)
            highs.append(optimum)
        return values

    values = solve(objective(u))
    minimum_shortfall = float(sum(values[u]))
    shortage = minimum_shortfall > TOL
    if not shortage:
        upper[u] = 0
    values = solve(objective(r, -1))
    reserve_floor = float(values[r])
    if not shortage and x:
        for task, indices in zip(inputs.tasks, x):
            upper[indices] = [task.max_power_kw if h in task.allowed_hours else 0 for h in range(HOURS)]
        values = solve(objective(np.concatenate(x), -1))
    values = solve(objective(e[-1], -1))
    values = solve(objective(np.concatenate([q, d])))
    if not shortage and x:
        # Fixed earlier-hour preference, then input task order. Earlier objective
        # equalities protect service, final energy, and throughput from this tie.
        cost = np.zeros(size)
        for j, indices in enumerate(x):
            cost[indices] = [(h+1)*(len(x)+1)+j for h in range(HOURS)]
        values = solve(cost, freeze=False)
    if float(sum(values[u])) > minimum_shortfall+TOL or min(values[e]) < reserve_floor-TOL:
        raise NumericalError("Ordered objectives lost critical coverage or reserve")
    if shortage and any(abs(v) > TOL for indices in x for v in values[indices]):
        raise NumericalError("Flexible work allocated during critical shortage")
    return build_result(inputs, values[e], values[q], values[d], values[w], values[u],
                        [values[indices] for indices in x])
