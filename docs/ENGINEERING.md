# Engineering and APIs

React/Vite uses shadcn/ui, Tailwind, Recharts and Lucide. FastAPI validates the clinic inputs and runs the fixed schedule, sunshine-first heuristic and SciPy MILP using the same forecast, equipment requirements, starting energy and physical limits. Claude Haiku handles conversation and selects native tools. Python owns weather retrieval, arithmetic, schedules and verification.

## Physical model and scheduling

The simulator has 24 hourly slots and 25 stored-energy boundaries. Rates are kW and energy is kWh. Let `p` be estimated solar energy, `d` battery discharge delivered to the bus, `q` charging energy drawn from the bus, `c` critical demand, `u` unserved critical energy, `f` served flexible energy, `w` curtailed solar, and `e` stored energy.

```text
p[t] + d[t] = c[t] - u[t] + f[t] + q[t] + w[t]
e[t+1] = e[t] + charge_efficiency*q[t] - d[t]/discharge_efficiency
conversion_loss = (1-charge_efficiency)*sum(q)
                + (1/discharge_efficiency-1)*sum(d)
```

The battery stays within capacity and charge/output limits, with mutually exclusive charging and discharging. Critical hours stay fixed. Flexible allocations obey operator-defined windows, hourly power and total required energy. Allocations model divisible work, so actual appliance cycles and service deadlines need separate review. The optimizer minimizes essential shortfall first, then protects the strongest feasible reserve up to the target, maximizes flexible work, preserves end-of-day energy and minimizes cycling. In a critical shortage the diagnostic solution defers flexible work. The reserve check includes the initial state. Daily minimum, evening minimum and end-of-day energy are separate metrics.

Modeled shortages and reserve breaches are successful calculations with diagnostic statuses; solver failures return HTTP 503. Zero essential demand gives no coverage percentage. Presets report shortages separately from deferred flexible work. The independent checks verify physical accounting and applicable limits before results are exposed.

The recovery planner tests bounded changes to timing, generation, storage, output and expressly designated optional work. It holds absolute starting kWh, reserve and original demand fixed when comparing alternatives. Postponed work remains in the original-work denominator. Rankings consider essential shortfalls, reserve and unfinished work before modeled change size. The best tested option can still leave a deficit. Electricity prices, equipment selection and installation sizing require separate inputs and review.

## API reference

| Surface | Routes and contracts |
|---|---|
| Core and examples | `GET /api/health`, `GET /api/scenarios`, `POST /api/simulate`, `GET /api/demos/competing-windows`. [Simulation types](../contracts/api.ts), [presets](../contracts/scenarios.json), [computed example payload](../contracts/examples/scheduling.response.json). |
| Forecasts and sensitivities | `GET /api/forecast/locations`, `GET /api/forecast`, `POST /api/forecast/plan`, `GET /api/weather/outlook`. [Forecast types](../contracts/forecast.ts), [outlook types](../contracts/weather.ts). |
| Recovery comparison | `POST /api/recovery/plan`, `GET /api/demos/recovery`. [Recovery types](../contracts/recovery.ts). |
| Session planning and chat | `/api/planning/sessions`, including activity and energy proposals, confirmations, recovery selection, conversation and `/{id}/agent/stream`. [Planning types](../contracts/planning.ts), [request/response examples](../contracts/examples). |
| Preserved stateless assistant and tools | `/api/agent`, `/api/planner`, and `/api/assistant`. [Agent types](../contracts/agent.ts). The guided planner and offline rule-based editor are separate from primary session chat. |

The [OpenAPI schema](../contracts/openapi.json) captures exact routes and schemas. A running app serves `/openapi.json` and Swagger at `/docs`. Strict payloads reject invalid fields and incorrect numeric types. Omitted simulation overrides use preset values and explicit zero is honored. Capacity edits do not silently clamp the starting charge or reserve.

```bash
curl -X POST http://127.0.0.1:8000/api/simulate \
  -H 'Content-Type: application/json' \
  -d '{"scenario":"scheduling"}'
```

The response supplies baseline, heuristic and optimized allocations, hourly battery trajectories, provenance, warnings and metrics. To regenerate checked-in schemas and examples, use `python scripts/export_api_contract.py` and `python scripts/export_planning_examples.py` with the development dependencies installed.

## Assistant, review and saved state

- **Model and stream.** The primary session chat uses Claude Haiku with server-only credentials. It sees the clinic configuration and bounded conversation context. SSE yields fixed progress phases and a final validated result. A failed reply exposes a retry while preserving available canonical state. The legacy local adapter is retained separately.
- **Activity drafts.** Reusing an existing device preserves one physical load. Event duration alone adds no electrical demand. Shared flexible runtime is the maximum confirmed daily requirement and baseline requirement, rather than a sum across references. Existing device requirements and new device specifications must be reviewed explicitly.
- **Energy drafts.** `/energy-proposals` stages patches for PV, battery, midnight assumption, reserve, efficiencies and charge/output limits. A timestamped current state-of-charge reading is separate from `initial_battery_kwh`. Capacity changes preserve absolute starting energy unless explicitly reviewed as part of the edit.
- **Confirmation.** Only a human confirmation can adopt a proposal. Writes carry a revision and confirmation is idempotent. A stale draft requires review. Confirmed inputs recalculate even when forecast or solver failure prevents a new result. Choosing an alternative for comparison does not adopt hardware or work changes.
- **Persistence.** The backend atomically saves reviewed inputs, drafts, dated results, receipts and recent chat. Invalid snapshots surface a startup error; failed saves roll back and report an error. Interrupted calculations cannot restore as current. Use one backend process per state file. The prototype has no shared accounts or multi-worker database.
- **Privacy.** Use configuration and equipment descriptions in chat. Patient data is outside the intended workflow. Keep private state and credentials out of Git.

## Development entry points

- [Main app and routes](../backend/app/main.py), [model dispatch](../backend/app/energy_simulator.py), [optimizer](../backend/app/optimizer.py), [heuristic](../backend/app/heuristic.py), [recovery planner](../backend/app/recovery_planner.py).
- [Session routes](../backend/app/planning_routes.py), [activity/settings state](../backend/app/planning_state.py), [persistence](../backend/app/planning_persistence.py), [provider](../backend/app/agent_provider.py), [session agent](../backend/app/planning_agent.py).
- [Planning frontend](../frontend/src/features/planning), [backend tests](../backend/tests), [CI workflow](../.github/workflows/ci.yml).

Run `npm --prefix frontend run dev` beside the backend for development. For a nondefault backend port, set `LIFELINE_API_PORT` for the frontend dev server. A desktop browser is optional for numerical-only checks. With the model dependencies installed, run `PYTHONPATH=backend python -m app.model_demo scheduling` from the root. Other preset IDs are `normal`, `storm`, and `high_demand`.

Use [the saved-state migration utility](../scripts/migrate_planning_snapshot.py) only for intentional migration of a legacy preview export and transcript. It preserves the original inputs and refuses to overwrite a destination snapshot.
