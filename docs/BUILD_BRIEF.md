# LifeLine — detailed implementation specification

Version 1.0, November 12, 2026. This refines the [supplied brief](source/LifeLine_Codex_Build_Brief.md). If this handoff and the source differ, use the decisions here and in the committed contracts for the planned implementation. The numerical model and Person 2’s FastAPI integration are implemented. Dashboard sections remain build targets. See [PERSON_1_HANDOFF.md](PERSON_1_HANDOFF.md) and [PERSON_2_HANDOFF.md](PERSON_2_HANDOFF.md) for executed checks and integration interfaces.

## 1. Outcome and limits

Build a local, software-only decision-support dashboard for one fictional rural Kenyan clinic. Show a deterministic 24-hour scenario forecast, a physically valid baseline, and a schedule for flexible loads. Make both successful planning and unavoidable critical shortages visible.

Pitch: “Reliable healthcare needs reliable electricity. LifeLine forecasts shortages before they happen and recommends how to preserve limited solar and battery power for essential services.”

Relevant UN goals: SDG 7, SDG 3, and SDG 10. The prototype illustrates a possible contribution; it does not measure progress toward those goals.

Critical loads are supplied by a hypothetical facility operator. The software does not infer medical priorities. All clinic data is synthetic. No real devices, medical equipment switching, clinical decisions, accounts, database, payment system, or dispatch service are in scope.

## 2. Stack and repository structure

Use React, TypeScript, Vite, Tailwind CSS, and Recharts for the frontend. Use Python 3.11, FastAPI, Pydantic, NumPy, SciPy MILP, and Pytest for the backend. Keep the pure energy model independent of FastAPI and UI code. No LLM, external credentials, or runtime network service is required.

Backend versions and transitive dependencies are pinned in `backend/requirements.txt` and `requirements-dev.txt`. Person 3 still owns frontend dependencies. Target Node 22.12+ within Node 22 and the Vite version compatible with that environment. Do not spend the hackathon upgrading stacks or introducing a database.

Planned implementation layout:

```text
contracts/
  api.ts                      # shared API shapes, already provided
  scenarios.json              # synthetic input profiles, already provided
frontend/
  src/
    App.tsx
    components/
      MetricCards.tsx
      BatteryForecastChart.tsx
      EnergyForecastChart.tsx
      EquipmentTable.tsx
      ScenarioPicker.tsx
      RecommendationPanel.tsx
      SimulationControls.tsx
    lib/api.ts
  package.json
  package-lock.json
  vite.config.ts
backend/
  app/
    __init__.py
    main.py
    models.py
    scenarios.py
    solar_forecast.py
    energy_simulator.py
    optimizer.py
    explanations.py
  tests/
    test_energy_balance.py
    test_optimizer.py
    test_scenarios.py
    test_api.py
  requirements.txt
  requirements-dev.txt
.github/workflows/ci.yml
```

Existing docs, contracts, and the planning checker stay at repository root. Avoid an extra nested `lifeline/` directory. Resolve the shared JSON relative to a module/repository path, not the shell's working directory. If packaging the backend, include a copy of that configuration as package data and verify parity.

## 3. Canonical inputs and units

The authoritative numerical inputs are in [scenarios.json](../contracts/scenarios.json). Equipment must be editable in that configuration without changing simulator code. The MVP UI must expose PV capacity, battery capacity, initial energy, reserve, and the High Demand additional load; other electrical settings may remain in config.

| Common input | Default | Meaning |
|---|---:|---|
| PV capacity | 5 kW | Nameplate power |
| PV performance ratio | 0.80 | Synthetic lumped conversion/loss factor |
| Battery capacity | 20 kWh | Maximum modeled stored energy |
| Initial energy | 14 kWh, Storm 6 kWh | Stored energy at boundary 0 |
| Reserve | 4 kWh | Desired stored-energy floor, not physical zero |
| Charge efficiency | 0.95 | Stored energy added per input kWh |
| Discharge efficiency | 0.95 | Output energy per stored kWh removed |
| Maximum charge / discharge | 4 / 4 kW | Limits measured on the modeled external energy bus |
| Step and horizon | 1 h / 24 h | Slots 0 through 23; boundaries 0 through 24 |
| Local clock | Africa/Nairobi | Fixed fictional day, no live clock required |

All demand and PV values in the equations are **energy in kWh per slot**. Input powers are converted using `energy = power_kw * dt_hours`. A battery level in kWh differs from its percentage `100 * energy / capacity`. All arithmetic uses unrounded values; round only display text.

Electrical bus abstraction: PV, critical demand, flexible demand, charging input, and discharging output share one idealized bus. The performance ratio includes simplified PV/inverter effects; do not apply a second unspecified inverter efficiency. No grid, generator, self-discharge, degradation, temperature dynamics, surge currents, or sub-hour events are modeled.

## 4. Loads and fixed baseline

| ID | Category | Power | Hours or requirement |
|---|---|---:|---|
| `vaccine_refrigerator` | Critical | 0.120 kW average | All 24 slots |
| `communications` | Critical | 0.040 kW | All 24 slots |
| `essential_lighting` | Critical | 0.150 kW | Slots 8–17, meaning 08:00–18:00 |
| `device_charging` | Flexible, divisible | Up to 0.300 kW | 0.900 kWh within slots 8–20; baseline slots 18, 19, 20 |
| `auxiliary_laundry` | Flexible, divisible approximation | Up to 0.600 kW | 1.200 kWh within slots 10–19; baseline slots 18, 19 |
| `additional_protected_load` | Critical, High Demand only | 4.500 kW default | Slots 20 and 21 |

The laundry name is illustrative: the MVP treats its energy as divisible and interruptible. Do not depict it as a validated appliance cycle. Contiguous jobs require a later binary task-start model and are out of the initial build.

The naive baseline uses these fixed requested flexible schedules. Within each hour it serves critical demand first, then requested flexible demand, then stores remaining solar and curtails any excess. It can discharge to physical zero without protecting the recommended reserve. It never moves missed baseline work into another hour. Record unmet critical demand and unserved flexible energy separately.

For each scenario, baseline and optimization receive the exact same resolved configuration, weather, load profiles, and task energy requirements. A baseline is a comparator, not a claim about actual clinic behavior.

## 5. Forecast and four presets

For the midpoint of hour `t`, with synthetic daylight from 06:00 to 18:00:

```text
shape[t] = sin(pi * ((t + 0.5) - 6) / 12)   if 6 <= t < 18
           0                                 otherwise
pv[t] = pv_capacity_kw * 0.80 * shape[t] * cloud_factor[t] * dt
```

Cloud factors lie in `[0, 1]`. All nighttime PV is exactly zero. This is a scenario forecast, not a fitted model, astronomical irradiance calculation, or real weather prediction.

| ID | Cloud factor | Starting energy | Added protected load | Expected optimized status with defaults |
|---|---:|---:|---|---|
| `scheduling` | 1.00 | 6 kWh | None; 1.5 kW PV, 8 kWh capacity, 4.8 kWh reserve | `OK` |
| `normal` | 1.00 | 14 kWh | None | `OK` |
| `storm` | 0.08 | 6 kWh | None | `RESERVE_AT_RISK` |
| `high_demand` | 1.00 | 14 kWh | 4.5 kW in slots 20 and 21 | `CRITICAL_SHORTAGE` |

Show Storm's lower initial battery beside its lower sunshine. It represents synthetic depletion from preceding cloudy days; the preceding days are not simulated. Do not attribute all differences between presets to optimization or cloud cover alone. For High Demand, explain the per-hour discharge limit: daily energy alone cannot prove feasibility.

Scenario selection loads that preset's defaults and requests a fresh simulation. Apply user overrides only after selecting the preset. “Reset” restores the selected preset; switching presets resets edited values so the intended demo is reproducible. Show all effective values returned by the backend.

The primary demo is `scheduling`: both alternatives complete the same 2.1 kWh of work, improve the daily minimum by 0.368421 kWh, retain 2.210526 kWh more at midnight, and reduce conversion losses by 0.110526 kWh. Sunshine-first ties the MILP on these metrics. The existing schedule runs flexible work in evening hours; alternatives use allowed daytime hours. All physical inputs and requirements are identical across comparisons. Results are synthetic, not empirical clinic benefits.

## 6. Physical model

Let `e[0..24]` denote stored energy. For each slot `t`, `p` is PV energy, `c` is requested critical energy, `f` is total served flexible energy, `q` is charge input, `d` is discharge output, `w` is curtailed PV, and `u` is unmet critical energy:

```text
p[t] + d[t] = (c[t] - u[t]) + f[t] + q[t] + w[t]
e[t+1] = e[t] + eta_charge*q[t] - d[t]/eta_discharge

e[0] = initial_battery_kwh
0 <= e[t] <= battery_capacity_kwh                for all 25 boundaries
0 <= u[t] <= c[t]
0 <= w[t] <= p[t]
0 <= q[t] <= max_charge_kw * dt * z[t]
0 <= d[t] <= max_discharge_kw * dt * (1-z[t])
z[t] in {0,1}
```

For every flexible task `j`, introduce served-energy allocations `x[j,t]`:

```text
x[j,t] = 0                                      outside allowed_hours[j]
0 <= x[j,t] <= max_power_kw[j] * dt              inside allowed_hours[j]
sum_t x[j,t] <= required_energy_kwh[j]
f[t] = sum_j x[j,t]
deferred[j] = required_energy_kwh[j] - sum_t x[j,t]
```

Deferral means unserved within this 24-hour horizon. Do not claim a feasible next-day schedule. Critical inputs are immutable during optimization. Battery charge/discharge limits are shared across every load, not available separately for each device. `w <= p` and exclusive battery mode prevent treating discharged battery energy as curtailed solar.

Use absolute `1e-6 kWh` tolerance for energy assertions and status thresholds. Validate raw physical results before rounding or suppressing tiny numerical residue in output. Do not silently clamp a materially infeasible result into valid bounds.

## 7. Optimization priorities and failures

Use a small SciPy MILP with 24 battery-mode binaries and continuous divisible task allocations. Build the solver in separate stages with earlier objective values fixed within tolerance. Avoid a single arbitrary weighted sum that can exchange critical coverage for flexible service.

1. **Critical feasibility.** Force all flexible allocations to zero and minimize total unmet critical energy. If the optimal total exceeds tolerance, critical demand is infeasible under the model. Keep flexible tasks fully deferred and return a diagnostic plan minimizing unmet critical demand, then improving reserve/end energy and avoiding needless cycling. Never return an `OK` result for this branch.
2. **Feasible reserve.** When critical demand is fully feasible, fix `u = 0`. With flexible work still disabled, maximize a floor variable `r` satisfying `0 <= r <= reserve_kwh` and `e[b] >= r` for all 25 boundaries. This finds the strongest feasible floor up to the requested target. If the initial state is already below reserve, include that boundary in the warning.
3. **Flexible service.** Enable the task allocations, enforce the previous floor, and maximize their total served kWh. All flexible task weights are equal for the MVP. No medical prioritization is inferred from task labels.
4. **End-of-day energy.** Preserve the maximum flexible service and maximize `e[24]`. This discourages unnecessary end-of-horizon depletion; it does not guarantee tomorrow's coverage.
5. **Cycling and tie handling.** Preserve those objectives and minimize `sum(q + d)`. Use stable task/hour ordering and a documented final fixed ordering preference for equivalent task allocations. Pin the solver environment and test repeatability there. Do not promise bit-identical schedules across solver versions or platforms; compare invariant metrics within tolerance.

When a stage fixes an earlier optimum, control tolerance accumulation: final results must still obey the primary critical/reserve rules at `1e-6`. If that cannot be established, reject the solution as a numerical error instead of publishing it.

An infeasible “zero-unmet” formulation is distinct from an unexpected infeasible diagnostic formulation: with shortage slack and no flexible service the physical model should always admit a plan for valid inputs. A timeout, import failure, unbounded result, or inconsistent diagnostic model is a technical error. Return a structured 503 and display an unavailable state. Do not convert solver status codes directly into clinic risk statuses. Require a successfully verified optimum for the planned MVP responses; do not silently use a non-optimal incumbent.

Budget at most 5 seconds total for the solve stages and pass the remaining time budget to each stage. The release target is under 2 seconds for presets on the demo laptop, to be measured. If this is missed, remove optional features and optimize formulation; do not weaken the physical constraints.

## 8. Status, metrics, and explanations

Compute a status separately for each plan from its actual dispatch:

```text
CRITICAL_SHORTAGE if total critical_unserved_kwh > 1e-6
RESERVE_AT_RISK   else if min(e[0..24]) < reserve_kwh - 1e-6
OK               otherwise
```

The top-level response status equals the optimized plan's status. Baseline warnings remain visible even when optimization resolves them. `OK` means the modeled critical demand and reserve target were met for this horizon; use UI text “Within modeled limits,” not “Safe.” Flexible deferral generates a separate notice and may coexist with any status.

Daily metrics use full precision:

- Solar generation: `sum(pv)`; requested critical demand: `sum(critical)`.
- Critical unserved: `sum(u)`; energy-weighted coverage: `100 * (sum(c)-sum(u))/sum(c)`.
- If requested critical demand is zero, coverage is `null` and the UI shows “N/A.”
- Minimum battery includes all 25 boundaries; final battery is `e[24]`.
- Flexible requested is the sum of task requirements; served is the sum of allocations; deferred is requested minus served.
- Shortage hours contain slots with unmet critical energy above tolerance. Reserve breach boundaries contain boundary indices with stored energy below reserve minus tolerance.
- Battery conversion loss is `(1-eta_charge)*sum(q) + (1/eta_discharge-1)*sum(d)`.

For a daily cross-check:

```text
initial_energy + total_pv
  = final_energy + critical_served + flexible_served + curtailed + conversion_loss
```

Recommendation prose comes from templates populated with computed facts. Include task, served/deferred kWh, actual allocated hours, and the reserve or rate constraint that explains a decision. For High Demand say that no flexible schedule can cover the modeled shortfall at the given output limit. Do not suggest disabling critical equipment or make medical response recommendations.

Only claim improvements calculated from matching plans, such as the difference in minimum battery kWh. Skip relative percentages when a denominator is zero or an improvement is absent. No lives-saved, emissions, cost, or outage-reduction claims are supported by this model.

## 9. API contract

Use [contracts/api.ts](../contracts/api.ts) and [OpenAPI](../contracts/openapi.json) for exact fields. `backend/app/models.py` now mirrors the contract with runtime Pydantic validation. The response includes all three plans, computed comparison metrics, warnings for baseline/heuristic/optimized, and deterministic recommendations. Nullable recommendation metadata is documented in the TypeScript contract.

| Method and path | Success | Purpose |
|---|---|---|
| `GET /api/health` | 200 `HealthResponse` | Local service health and API version |
| `GET /api/scenarios` | 200 `ScenarioListResponse` | Four choices, complete defaults, and synthetic descriptions |
| `POST /api/simulate` | 200 `SimulationResponse` | Resolve overrides, calculate all three plans, return comparisons and diagnostics |

Request example:

```json
{
  "scenario": "storm",
  "battery_capacity_kwh": 20,
  "initial_battery_kwh": 6,
  "reserve_kwh": 4,
  "pv_capacity_kw": 5
}
```

Omitted fields use selected-preset defaults. Explicit zero is never treated as missing. Reject explicit `null`, booleans as numeric values, non-finite numbers, unknown properties, and invalid scenario names. Permit JSON integers where real numeric values are expected.

| Input | Inclusive limits |
|---|---|
| Battery capacity | `0 < value <= 200` kWh |
| Initial energy and reserve | `0 <= value <= resolved battery capacity` |
| PV capacity | `0 <= value <= 100` kW |
| Charge and discharge limits | `0 <= value <= 100` kW |
| Efficiencies | `0 < value <= 1` |
| Additional protected load | `0 <= value <= 10` kW; override accepted only for `high_demand` |

If a smaller battery is supplied without a compatible initial-energy/reserve override, return 422 rather than silently shrinking either value. Validate bundled task IDs, profile lengths, allowed slots, task requirements, and baseline allocations at startup. Reject malformed configuration loudly; an impossible flexible energy request may be deferred, but malformed windows and schedules are configuration errors.

Critical shortage and reserve risk are successful simulation responses (HTTP 200). Validation errors are 422 in the shared error envelope. Timeouts, unavailable solver, and unverifiable numerical results are 503. Unexpected application failures are 500 without leaking stack traces. Add a FastAPI validation exception handler so errors match the contract instead of an unplanned default body.

Return the resolved configuration, equipment profiles, and assumptions with every result. The 24 hourly records contain explicit start/end battery state; the chart uses boundary 0 plus all 24 end states. Task deferral is per day, not spread into invented hourly deferral values.

## 10. Dashboard and interactions

Use an off-white background, dark navy text, green/amber/red status accents, clear typography, and restrained cards. The dashboard must work at 1440 px and 375 px widths without horizontal page scrolling.

1. Header: LifeLine, “Simulated clinic,” selected scenario, fictional Kenya context, and synthetic-data label.
2. Scenario buttons: Scheduling improvement (default) / Normal / Storm / High Demand, selected state, keyboard operation, and a visible recalculation indicator.
3. Editable controls: PV capacity, battery capacity, initial kWh, reserve kWh, and additional kW for High Demand. Submit changes explicitly; show units, validation errors, and reset.
4. Four metric cards: initial battery kWh and %, total scenario solar kWh, critical coverage %, and optimized risk status. Show minimum and final battery in the chart summary so the initial-level card is unambiguous.
5. Centerpiece: before/after equipment timelines with actual served allocations, the same-work flag, and sunshine-first comparison. Show computed midnight preservation separately from daily minimum improvement and conversion-loss reduction. Clearly acknowledge heuristic ties. Battery chart: 25 boundaries labeled 00:00 through 24:00; baseline and optimized energy in kWh; reserve reference line. Include keyboard/readable summary text and distinguish lines by dash pattern as well as color.
6. Energy chart: solar and requested critical plus planned flexible demand per hourly slot. Label requested versus served explicitly; do not hide unserved demand by plotting only consumption.
7. Equipment table: category, power, required/allowed hours, requested energy, served/deferred energy, and optimized allocations. Clearly label divisible flexible approximations.
8. Recommendation panel: computed explanations, critical shortage hours/kWh, reserve breaches, deferred tasks, and baseline comparison.
9. Assumptions section and the visible text “Illustrative simulation; not for clinical or operational use.” No unnecessary internal stack details in the product screen.

On scenario changes, cancel an older request with `AbortController` or ignore it by a monotonically increasing request sequence. Never let a late Normal response overwrite a selected Storm scenario. While recalculating, make any retained results visibly stale and disable misleading controls. Show a retry action on failure and a clear unavailable state instead of zero-filled or apparently healthy results. Use only local assets/fonts for offline use.

Use a Vite `/api` proxy to `http://127.0.0.1:8000` during development. Document a local preview path for the built frontend and configure the preview proxy or backend static serving so a production build can still reach the API. Browser-only static hosting does not run the Python backend.

## 11. Delivery and release

Ship all four scenarios, valid baseline and optimized dispatches, editable controls, clear explanations, responsive layout, automated model/API tests, and verified README commands. Use [TEAM_PLAN.md](TEAM_PLAN.md) for owners and [ACCEPTANCE.md](ACCEPTANCE.md) for required evidence.

External weather, trained forecasting, LLM explanations, CSV export, multi-clinic support, and public hosting are stretch work only after the release gates pass. The core demo must remain deterministic and able to run offline after dependencies are installed.

## Implemented numerical handoff

`compare_schedules(ModelInput)` returns existing, sunshine-first, and optimized `PlanResult` objects with computed comparison fields. The shared scenario enum adds `scheduling`; Person 2 has extended the HTTP response with heuristic/comparison fields while retaining existing data. Routes, strict configuration/override validation, error mapping, and computed explanation templates are implemented. The dashboard remains unimplemented. Requirements, examples, and exact run commands are in the [API handoff](PERSON_2_HANDOFF.md).
