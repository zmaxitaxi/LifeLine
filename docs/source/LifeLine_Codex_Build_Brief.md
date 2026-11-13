# LifeLine — Codex Build Brief

> **Project:** LifeLine — AI-assisted energy planning for off-grid rural clinics  
> **Hackathon:** Open Project, UN Sustainable Development Goals  
> **Deadline:** Saturday, November 14, 2026, 11:59 PM Pacific  
> **Status:** Build specification for a demonstrable prototype, not a medical or electrical control system.

## Instructions for Codex

Build a functioning, polished **software-only MVP** of LifeLine following this brief. Start by examining the repository and existing code; preserve working functionality. If starting from an empty repository, scaffold the stack specified below. Prioritize a fully integrated demo over stretch features. Record assumptions prominently, implement deterministic reproducible simulation, and write tests for the energy accounting and safety constraints. Do not connect to real clinic hardware, automatically control medical equipment, or represent the prototype as certified for real-world use.

## 1. Problem and pitch

Many rural healthcare facilities have unreliable grid electricity or depend on small solar-plus-battery systems. Staff need to know whether available electricity will cover essential loads, especially during cloudy weather or demand spikes.

**Pitch:** "Reliable healthcare needs reliable electricity. LifeLine forecasts shortages before they happen and recommends how to preserve limited solar and battery power for essential services."

**Relevant UN SDGs:** SDG 7 (Affordable and Clean Energy), SDG 3 (Good Health and Well-being), SDG 10 (Reduced Inequalities).

LifeLine is a **human decision-support dashboard** for a fictional off-grid clinic. It forecasts solar generation, simulates battery state, recommends how to schedule flexible electrical loads, and transparently compares outcomes with a baseline.

## 2. Hackathon MVP scope

### Must ship

1. A single fictional off-grid rural clinic with a configurable solar array, battery, and equipment load profiles.
2. A 24-hour hourly solar-generation forecast using documented weather-driven modeling assumptions or real historical public data.
3. A battery simulator with correct kW versus kWh units, state-of-charge bounds, and charge/discharge efficiencies.
4. A constrained optimization algorithm that schedules **only flexible** loads to protect fixed critical requirements and reserves where physically feasible.
5. Three clickable scenarios: normal/sunny, cloudy storm, and unexpectedly high demand.
6. A polished responsive dashboard showing solar production, forecast demand, baseline versus optimized battery state, critical-load coverage, flexible loads served/deferred, and actionable explanations.
7. Explicit feasibility warnings if available energy cannot meet critical needs; never falsely label an infeasible scenario "safe."
8. Automated tests and a README with install/run/demo instructions.

### Stretch only after the MVP works

- Historical weather or irradiance API integration with cached fallback data.
- A simple scikit-learn forecast trained and evaluated against a naive baseline, if suitable data exists.
- An LLM-based natural-language explanation derived strictly from computed metrics; the optimization must remain deterministic.
- Export a scenario summary as CSV or JSON.

### Out of scope

- Real medical device switching, electric relays, emergency dispatch, clinical decision-making, real-time hospital integration, user accounts, billing, multi-facility fleet management, or unsupported claims that patients were saved.

## 3. Suggested stack and repository layout

- **Frontend:** React + TypeScript + Vite, Tailwind CSS, Recharts.
- **Backend:** Python 3.11+, FastAPI, Pydantic, NumPy, SciPy (`scipy.optimize.linprog` or `scipy.optimize.milp` where appropriate).
- **Data:** Local JSON/CSV; no database required.
- **Tests:** Pytest for backend; lightweight frontend smoke checks if time permits.

Suggested files (adapt to the existing repo):

```text
lifeline/
  frontend/
    src/
      App.tsx
      components/
        MetricCards.tsx
        EnergyForecastChart.tsx
        LoadPriorityPanel.tsx
        ScenarioPicker.tsx
        RecommendationPanel.tsx
      lib/api.ts
  backend/
    app/
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
    requirements.txt
  README.md
```

## 4. Demonstration clinic and assumptions

Model a **fictional** clinic in rural Kenya for the narrative, but clearly label all input values synthetic and configurable. Avoid implying that fictional profiles represent real Kenyan facilities.

Example defaults (illustrative only; validate internally):

| Parameter | Value |
|---|---:|
| PV nameplate capacity | 5 kW |
| Battery usable capacity | 20 kWh |
| Initial battery energy | 14 kWh |
| Minimum recommended reserve | 4 kWh |
| Charging efficiency | 95% |
| Discharging efficiency | 95% |
| Per-hour max battery charge/discharge | 4 kW |
| Horizon | 24 hourly time slots |

Illustrative equipment (make wattages and schedules editable in config):

| Load | Example power | Category | Schedule |
|---|---:|---|---|
| Vaccine refrigerator | 120 W average | Critical | 24/7 |
| Communications | 40 W | Critical | 24/7 |
| Essential lighting | 150 W | Critical | Required clinic hours |
| Nonessential device charging | 300 W | Flexible | 3 hours in an allowed window |
| Laundry / auxiliary equipment | 600 W | Flexible | 2 hours in an allowed window |

**Important:** "Critical" refers to protected loads as defined by a hypothetical trained facility operator, not a medical recommendation made by AI. Real refrigeration has temperature/thermal behavior beyond this simplified constant-power model. Never suggest turning off medically necessary equipment.

## 5. Mathematical model

Use hourly time steps with time step `dt = 1 hour`. Distinguish power (kW) from energy (kWh). Let:

- `pv[t]`: solar generation energy within hour `t` (kWh).
- `critical[t]`: non-deferrable electrical energy demand in hour `t` (kWh).
- `flex[t]`: optional/schedulable demand allocated to hour `t` (kWh).
- `charge[t]`, `discharge[t]`: battery charge and discharge energy during hour `t` (kWh).
- `soc[t]`: stored battery energy at the start of hour `t` (kWh).
- `curtail[t]`: excess solar not used or stored (kWh).
- `unserved_critical[t]`: critical demand not supplied, **only for explicit shortage diagnostics**, never silently optimized away as acceptable.

Energy balance:

```text
pv[t] + discharge[t] + unserved_critical[t]
  = critical[t] + flex[t] + charge[t] + curtail[t]

soc[t+1] = soc[t] + eta_charge * charge[t]
                    - discharge[t] / eta_discharge
```

Constraints:

```text
0 <= soc[t] <= battery_capacity_kwh
0 <= charge[t] <= max_charge_kw * dt
0 <= discharge[t] <= max_discharge_kw * dt
charge[t], discharge[t], curtail[t] >= 0
critical[t] is an input and must not be rescheduled
flexible tasks only run in their explicitly allowed windows
```

Keep the minimum operating reserve as a target or hard constraint **only if feasible**. Distinguish it from the physical minimum (`0`). If an ideal reserve is impossible, warn; do not conceal the shortfall. Prevent simultaneous charging and discharging if the solver formulation permits it (e.g., binary mode variables using MILP), or document why the formulation cannot benefit from doing so and verify this with tests.

**Optimization approach:** First test if all critical demands can be met with the solar and battery constraints. If not, return `CRITICAL_SHORTAGE` with unmet critical energy and hours. If feasible, optimize the placement/completion of flexible tasks to maximize service subject to preserving a reserve and avoiding excessive battery cycling. If flexible tasks have minimum contiguous run times, use a binary time-slot MILP; for the initial MVP, divisible energy tasks are acceptable if labeled as such.

Compare against a **fixed, naive baseline schedule** with exactly the same solar, critical demands, battery size, initial state, and flexible task requirements. The baseline must not violate physical conservation: if insufficient energy exists, record loads as unserved rather than producing negative battery energy.

## 6. Solar forecast and scenarios

For a fast, credible MVP, implement a transparent deterministic generation model that scales a plausible daylight solar curve by cloud-cover and PV nameplate capacity. Keep nighttime generation at zero. Label results **scenario forecasts** instead of pretending a complex ML model has been trained.

- `normal`: strong midday output, routine clinic loads.
- `storm`: substantial reduction in midday output; preserve/flag battery reserve and propose deferral of optional operations.
- `high_demand`: same weather as normal, with a configurable additional load; flag shortages if constraints become infeasible.

If a real ML model is added, show what data it was trained on, baseline comparison, metric (MAE in kWh/hour), and validation split. Never fabricate performance statistics.

## 7. Backend API

Build straightforward JSON APIs:

```text
GET  /api/health
GET  /api/scenarios
POST /api/simulate
```

Request example:

```json
{
  "scenario": "storm",
  "battery_capacity_kwh": 20,
  "initial_battery_kwh": 14,
  "reserve_kwh": 4,
  "pv_capacity_kw": 5
}
```

Response should expose:

```text
scenario_name
assumptions
status: OK | RESERVE_AT_RISK | CRITICAL_SHORTAGE
hourly: [{hour, pv_kwh, critical_kwh, baseline_soc_kwh,
          optimized_soc_kwh, flexible_served_kwh, flexible_deferred_kwh}]
metrics: {critical_coverage_pct, min_soc_baseline_kwh,
          min_soc_optimized_kwh, flexible_served_kwh,
          flexible_deferred_kwh, critical_unserved_kwh}
recommendations: [{severity, title, explanation}]
```

Return structured warnings when a scenario is infeasible. Use deterministic numerical calculations for risk status; LLM prose, if added, is presentation-only.

## 8. Dashboard design

Design a polished, responsive product named **LifeLine** with a calm clinical aesthetic (off-white background, dark navy typography, green for normal, amber for risk, red for critical shortfall). Include:

1. Header with project name, "Simulated clinic" badge, selected scenario.
2. Four metric cards: battery level, forecast solar generation, critical load coverage, and risk status.
3. Main chart: baseline and optimized battery state over 24 hours, with reserve threshold clearly marked.
4. Optional second chart: solar production and demand by hour.
5. Equipment table separating critical from flexible loads.
6. Recommendation panel with concrete scheduling decisions and an explanation of tradeoffs.
7. Scenario controls for Normal / Storm / High Demand. Changing them must recompute the backend response, not merely change static copy.
8. Explicit legend and "Illustrative simulation; not for clinical or operational use" disclaimer.

Show honest outcomes, including cases where optimization cannot help enough. Do not use invented percentages like "40% reduction in outages" unless computed from the simulation and properly contextualized.

## 9. Validation and acceptance criteria

Backend tests must verify:

- Hourly and daily conservation of energy within numerical tolerance.
- Zero nighttime solar generation.
- Battery never below physical zero or above capacity.
- Charge/discharge rate and efficiency constraints.
- Critical loads remain protected when feasible.
- Clearly reported unmet critical demand when infeasible.
- Flexible jobs never scheduled outside allowed windows.
- Reserve warnings occur when minimum reserve is breached.
- Optimized results are evaluated against a valid baseline under identical inputs.
- All three scenarios produce distinct and internally consistent outputs.

Frontend acceptance:

- App loads locally with clear README instructions.
- Scenario buttons trigger fresh calculations and update metrics/charts.
- No broken imports or runtime errors.
- Desktop and narrow mobile layouts remain legible.
- Demo can run without internet access after dependencies are installed, using bundled scenario data.

## 10. Demo script (90 seconds)

**0–20 seconds — Problem:** "A rural clinic depends on solar and batteries to refrigerate vaccines, communicate, and provide essential care. When clouds roll in, staff may not know whether their limited electricity will last."

**20–40 seconds — Solution:** "LifeLine forecasts production and simulates battery consumption, then uses constrained optimization to schedule flexible loads without compromising predefined essential electricity requirements."

**40–70 seconds — Live demo:** Open normal scenario, show the battery forecast. Click Storm; solar generation decreases and warnings/recommendations update. Compare the baseline against the optimized battery curve and point out any deferred flexible tasks.

**70–90 seconds — Impact:** "This is an early decision-support prototype. Our aim is to help resource-constrained clinics make more informed use of their limited electricity, with meaningful alerts when no schedule can prevent a shortage."

## 11. Delivery priorities

**Priority 0:** Correct deterministic physics, constrained solver, truthful warnings, one functioning end-to-end scenario.

**Priority 1:** All three scenarios, charts, baseline comparison, tests, responsive UI.

**Priority 2:** Real weather data, trained ML with evaluated performance, polished explainability.

If time is limited, implement Priority 0 and Priority 1. Do not spend most of the time obtaining a model/API key or training an unnecessary model.

## 12. References and integrity

- WHO, *Electricity in health-care facilities*: https://www.who.int/news-room/fact-sheets/detail/electricity-in-health-care-facilities
- WHO, *Close to one billion people globally are served by health-care facilities with no or unreliable electricity* (2023): https://www.who.int/news/item/14-01-2023-close-to-one-billion-people-globally-are-served-by-health-care-facilities-with-no-electricity-access-or-with-unreliable-electricity
- UNDP, *Solar for Health*: https://www.undp.org/energy/solar-health

This project demonstrates software feasibility only. It requires validated facility data, electrical engineering review, input from healthcare workers, safety and cybersecurity analysis, and deployment partnerships before any real-world use.

## Final Codex task

Implement the MVP. Run automated tests and the production frontend build. Fix any failures. At completion, report: (1) files added/changed, (2) exact run commands, (3) which MVP features work, (4) modeled assumptions and limitations, (5) test results, and (6) what to demonstrate live. Do not claim empirical performance or deployment readiness that has not been verified.
