# Person 1 — implemented energy model and scheduling comparison

Scope: pure Python forecast, physical baseline, sunshine-first heuristic, MILP, complete plan results, and automated numerical tests. The original Person 1 delivery did not include API endpoints or a dashboard. The API is now implemented separately; see [PERSON_2_HANDOFF.md](PERSON_2_HANDOFF.md). The dashboard remains pending. The supplied brief is preserved unchanged.

## What works

| Module | Interface | Responsibility |
|---|---|---|
| `energy_types.py` | `BatteryConfig`, `FlexibleTask`, `ModelInput` | Validated numerical inputs; fixed 24 slots and 1-hour steps |
| `solar_forecast.py` | `forecast_solar(pv_capacity_kw, cloud_factors, performance_ratio=.8)` | Synthetic 06:00–18:00 curve, kWh per slot, zero nighttime PV |
| `energy_simulator.py` | `simulate_baseline(inputs)` | Fixed requested schedule; critical first, flexible, storage, curtailment |
| `heuristic.py` | `sunshine_first(inputs)` | Rank allowed slots by remaining solar after critical demand |
| `optimizer.py` | `optimize(inputs, time_limit_seconds=5)` | Multi-stage MILP, exclusive battery mode, feasible reserve, task service and terminal energy |
| `comparison.py` | `compare_schedules(inputs)` | Three plans from identical inputs and computed deltas |
| `model_demo.py` | `load_inputs(scenario_id, overrides=None)` | Example mapping from shared JSON to numerical types; CLI |

All three plans use the same `ModelInput`: identical sunlight, task requirements, battery configuration, and initial state. Results expose `status`, `hourly`, `metrics`, and `flexible_tasks` matching `PlanResult`. Raw constraints and hourly/daily accounting are verified before serialization. Numerical dust below `1e-10` is suppressed only after verification.

## Primary scenario and improvement

`scheduling` is the primary demo. PV capacity is 1.5 kW, battery capacity 8 kWh, initial energy 6 kWh, reserve target 4.8 kWh. Critical demand is 5.340 kWh; flexible requirements total 2.100 kWh. Equipment requirements/windows match the standard examples.

Baseline device charging runs at 18:00, 19:00, and 20:00; auxiliary laundry at 18:00 and 19:00. Both alternatives move work into allowed daytime windows without reducing completion. Exact allocations are returned per task and recorded in the [calculated evidence](evidence/person-1-results.json); display actual allocations rather than hard-coded times.

| Metric | Baseline | Heuristic | Optimized |
|---|---:|---:|---:|
| Flexible served | 2.100000 | 2.100000 | 2.100000 kWh |
| Critical unserved | 0 | 0 | 0 kWh |
| Minimum battery, all 25 boundaries | 4.617507 | 4.985928 | 4.985928 kWh |
| Minimum battery, boundaries 18–24 | 4.617507 | 6.828033 | 6.828033 kWh |
| Final battery, boundary 24 | 4.617507 | 6.828033 | 6.828033 kWh |
| Conversion losses | 0.378464 | 0.267937 | 0.267937 kWh |

This is a 0.368421 kWh higher full-day minimum, 2.210526 kWh more at midnight, and 0.110526 kWh less conversion loss. Shifting work uses solar that otherwise would be curtailed when the battery fills. Stored-energy and loss differences must not be added together as one battery-saving metric.

The heuristic matches the optimizer's critical coverage, flexible service, minimum/final battery, and losses here within `1e-6`. Equivalent task hours can differ. A separate two-task test with a narrow allowed window demonstrates lower MILP losses; do not generalize that result to every clinic.

## Solver priorities and failures

1. Minimize unmet critical energy with optional work disabled; slack cannot exceed actual critical demand.
2. Maximize a battery floor capped by reserve, constrained at all 25 boundaries. In critical shortage, retain the minimum-unmet diagnostic plan and keep optional work disabled.
3. If critical demand is feasible, enable flexible allocations and maximize completed energy within the feasible floor.
4. Preserve earlier optima and maximize midnight battery energy.
5. Minimize total charge/discharge throughput, then apply stable earlier-hour/task ordering to equivalent flexible schedules.

Stages freeze earlier objective values with equality constraints and verify raw solver results. One binary battery mode per slot prevents simultaneous charging/discharging. The 5-second budget covers formulation and solves after dependency import; first-time Python/SciPy import is excluded. Repeatability is tested in the pinned environment, not promised bit-identical across solver versions/platforms.

`SolverError.code` is `SOLVER_UNAVAILABLE` or `SOLVER_TIME_LIMIT`. `NumericalError.code` is `NUMERICAL_ERROR`, including unexpected infeasible/unbounded diagnostic formulations or corrupt results. Person 2 should map these to structured 503 responses. These exceptions are not proof of a physical shortage. Successful plans calculate status from actual unmet energy and reserve breaches.

## Other scenarios

- `normal`: critical and flexible work served; abundant sunlight; no promised daily-minimum improvement.
- `storm`: explicitly depleted 6 kWh start, cloud factor 0.08. MILP serves critical demand, defers 2.1 kWh optional work, and still reports reserve risk. Its improvement is not a same-work result.
- `high_demand`: protected 4.5 kW addition at hours 20 and 21. Each slot requires 4.66 kWh versus a 4 kWh battery output limit and zero solar. Optimized shortfall is 1.32 kWh; optional work is deferred. More stored energy cannot remove this rate constraint.

## Run and verify

From repository root, after creating/activating a virtual environment:

```bash
python -m pip install -r backend/requirements-model.txt
python -m pytest backend/tests -q
PYTHONPATH=backend python -m app.model_demo scheduling
python3 scripts/check_plan.py
```

Verified: Python 3.12.5, NumPy 2.2.6, SciPy 1.15.3, Pytest 8.3.5 on local macOS. Python 3.11 is a supported target but has not been independently executed. 62 numerical tests passed in the final verification. No frontend build or browser checks apply to this numerical-only delivery.

Tests cover accounting, efficiencies, bounds/rates, curtailment, critical priority, impossible task deferral, windows, reserve relaxation, same-input comparisons, heuristic ties/limitations, determinism, malformed inputs, solver failures/timeouts, corrupt results, and eight seeded varied physical cases. See [acceptance status](ACCEPTANCE.md) for the latest count.

Recorded comparison times were approximately 0.277 seconds for the first case and 0.008–0.012 seconds subsequently, with numerical dependencies already imported. These are local model timings, not HTTP latency or guarantees; re-measure on the demo laptop.

## Person 2 handoff

These numerical handoff requirements have now been implemented in the API layer. The bullets below record the original integration requirements; use the [Person 2 handoff](PERSON_2_HANDOFF.md) for the current HTTP contract and run commands.

- Reuse the numerical interfaces; keep HTTP validation and explanation templates outside the solver. Import/preload SciPy during service startup so its cold import does not delay the first request.
- `load_inputs` is an integration example, not full startup validation of arbitrary edited JSON. Add strict Pydantic requests, configuration validation, endpoints, and exception mapping.
- `ScenarioId` now includes `scheduling`. Extend outer `SimulationResponse` with the heuristic `PlanResult` and comparison metadata; preserve existing fields. The CLI wrapper is not the complete HTTP response and has no warnings/recommendations prose.
- Comparison fields: `same_flexible_work_completed`, `battery_preserved_at_midnight_kwh`, `minimum_battery_improvement_kwh`, `evening_minimum_improvement_kwh`, `conversion_loss_reduction_kwh`, and `heuristic_matches_optimizer_metrics`.
- Validate API types, enum values, null/unknown values, configuration, and error envelopes independently. Numerical dataclasses do not replace API acceptance gates.
- `FlexibleTask.baseline_kwh` can request less than required energy when work cannot fit; the difference is explicit daily deferral. Committed demo baselines request all task energy.

## Person 3 handoff

Show before/after task timelines using actual hours and served kWh. Put the same-work flag beside the battery comparison and identify heuristic ties plainly. Separate midnight preservation, daily minimum, and conversion losses. Default to `scheduling`; keep the other presets for behavior/limitations. Never imply protected medical equipment should be disabled.

All inputs are synthetic. Divisible auxiliary laundry is a mathematical approximation, not a validated appliance cycle. Real refrigeration temperature, surges, degradation, uncertainty, and tomorrow's demand are omitted. No health outcome, operational readiness, or clinical use is established.
