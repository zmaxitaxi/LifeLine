# Person 2 — API and backend integration

The FastAPI backend now wraps the existing numerical model without changing its physics, solver priorities, or scenario values. All routes use fresh computed results. The dashboard, frontend dependency setup, frontend CI, and browser/release checks remain Person 3 work.

## Implemented interfaces

| Endpoint | Response | Behavior |
|---|---|---|
| `GET /api/health` | `HealthResponse` | Available after startup validates configuration and imports SciPy |
| `GET /api/scenarios` | `ScenarioListResponse` | Four presets, complete resolved defaults, descriptions, synthetic provenance, expected default status |
| `POST /api/simulate` | `SimulationResponse` | Validates overrides; runs baseline, sunshine-first, and MILP from identical inputs; returns computed comparisons and explanations |
| `GET /openapi.json` | OpenAPI schema | Machine-readable endpoint/response schema |
| `GET /docs` | Swagger UI | Optional interactive API explorer; its JavaScript/CSS require internet access |

`backend/app/models.py` mirrors [contracts/api.ts](../contracts/api.ts). `scenarios.py` validates bundled JSON on startup and maps it to Person 1's numerical dataclasses. `explanations.py` builds deterministic prose from computed results. `main.py` provides startup, routes, error handling, and orchestration. The CLI/model code remains unchanged.

The response keeps the original fields and adds required `heuristic: PlanResult` and `comparison: ComparisonMetrics`. Warning `plan` also accepts `heuristic`. Optional recommendation `task_id` and `hours` may be null; the required `critical_coverage_pct` is null only when the critical-demand denominator is zero. No non-finite JSON numbers are published.

## Run and test

From repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r backend/requirements-dev.txt
python -m pytest backend/tests -q
python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

Example request in another terminal:

```bash
curl -X POST http://127.0.0.1:8000/api/simulate \
  -H 'Content-Type: application/json' \
  -d '{"scenario":"scheduling"}'
```

The service must run from the source tree with `contracts/scenarios.json` present. The default path is resolved relative to the module, not the working directory. Editing configuration requires restarting the service; every request uses the validated startup snapshot. No database, credentials, weather API, LLM, authentication, or hosting infrastructure is required.

## Input resolution and validation

Resolution order: common defaults → selected preset overrides → explicitly supplied request overrides. Explicit zeros are preserved. Nulls, unknown fields, invalid scenarios, booleans/numeric strings as numbers, non-finite values, and out-of-range values are rejected. Additional protected load may only be overridden for High Demand, including when set to zero.

The effective battery capacity must contain both initial energy and reserve. A smaller capacity with incompatible inherited defaults returns 422; neither inherited value is silently clamped. Integer JSON values are accepted for numeric power/energy fields. Error `details` contain locations/messages/types without reflecting raw inputs or Pydantic exception objects.

Startup validates four unique preset IDs, finite/ranged defaults and cloud profiles, 24-slot weather, fixed time/daylight settings, unique equipment IDs, valid/unique hours, task power and energy constraints, baseline windows, and additional-load scope. Malformed configuration stops startup. A valid task energy requirement that exceeds its window's capacity remains deferrable rather than being misclassified as malformed.

## Risk and technical failures

- HTTP 200 can have `OK`, `RESERVE_AT_RISK`, or `CRITICAL_SHORTAGE`. Top-level status is the optimized plan's computed status, never the preset's `expected_status` label.
- 422 `INVALID_REQUEST`: request/merged configuration validation. The same envelope is also used for 404/405 invalid routes/methods with their appropriate HTTP status.
- 503 `SOLVER_UNAVAILABLE`, `SOLVER_TIME_LIMIT`, or `NUMERICAL_ERROR`: no verified calculation is available; no plan/risk fields are returned.
- 500 `INTERNAL_ERROR`: unexpected failures/invalid response shapes, without stack traces in the response.

Each plan retains its own critical, reserve, and optional-work warnings. In the primary case, baseline reserve warnings remain visible even though the optimized plan is `OK`. Storm and High Demand explicitly disclose different work completion; do not frame their battery gains as same-work benefits. High Demand explains the computed discharge bottleneck without recommending changes to medical priorities.

The service imports SciPy at startup. Numerical work runs in a worker thread; an asynchronous lock permits one comparison at a time per process, avoiding competing solver threads while allowing non-computational endpoints to run. The existing solver's 5-second budget excludes startup import, queue wait, and HTTP serialization; it is not a complete HTTP deadline. This is a local demo service, not a production concurrency/load-tested deployment.

## Verification and evidence

**177 tests pass**: the original 62 numerical tests and 115 API/configuration/contract checks. Coverage includes the actual model through HTTP, independent energy accounting, all presets, overrides/reset behavior, error envelopes, raw non-finite/malformed JSON, invalid startup files, zero critical demand, fresh computations, real solver-timeout propagation, corrupt results, schema snapshot parity, and physically valid frontend example data. An outbound-connection-blocked test exercises all four simulations.

Tests passed in the workspace and an isolated source copy with a new virtual environment installed from `backend/requirements-dev.txt`; `pip check` found no broken requirements. Local environment: Python 3.12.5, FastAPI 0.115.12, Pydantic 2.14.3, Uvicorn 0.34.2, NumPy 2.2.6, SciPy 1.15.3. A dependency-level Starlette/AnyIO deprecation warning is present in tests and does not affect results.

Live Uvicorn requests over localhost verified health, scenario listing, OpenAPI, all four simulation outcomes, and a 422 error. Warm request times in this run were approximately 0.011–0.029 seconds; these are local observations, not guarantees. See [HTTP evidence](evidence/person-2-http-results.json).

Backend [CI](../.github/workflows/ci.yml) installs pinned dependencies, runs `pip check`, all backend tests, and reference calibration under Python 3.11/3.12 on Linux. See [GitHub Actions](https://github.com/zmaxitaxi/LifeLine/actions) for the actual remote result. Local verification used Python 3.12 only.

## Person 3: integrate the dashboard

1. Fetch `/api/scenarios`; default to `scheduling`. Use returned defaults to populate controls. Switching/resetting should reload those defaults rather than keep old overrides.
2. POST the selected ID plus edited values to `/api/simulate`. Use an `AbortController` or request sequence guard; do not display a stale response under a different scenario label.
3. Use the actual `flexible_tasks[].allocations` from each plan for before/after equipment timelines. Each allocation has `hour` and `served_kwh`. Show requested/served/deferred work per task.
4. Show `comparison.same_flexible_work_completed` and `heuristic_matches_optimizer_metrics`. Distinguish midnight preservation, full-day minimum improvement, and conversion-loss reduction; do not sum these numbers or hard-code the primary result.
5. Construct the battery chart from the first hourly `soc_start_kwh` plus all 24 `soc_end_kwh` values. Boundary indices are 0–24; shortage slots are 0–23.
6. Display warnings for all plans, returned assumptions, and the illustrative-use disclaimer. Treat non-200 responses as unavailable/invalid input, not a healthy zero-filled result.
7. Use Vite development and preview `/api` proxies to `http://127.0.0.1:8000`. No CORS middleware is needed with that same-origin path. No frontend or proxy configuration is created by this backend delivery.

The [OpenAPI snapshot](../contracts/openapi.json) and [computed scheduling response](../contracts/examples/scheduling.response.json) support frontend development. The example is documentation-only; never use it as an undisclosed fallback for a failed API call. Regenerate with `python scripts/export_api_contract.py`; tests check schema parity and example physical validity. JSON endpoints need no runtime external network; Swagger UI's external assets are optional.

Remaining release work: frontend, responsive/browser checks, integration screenshots, built-preview connectivity, full application offline execution, final rehearsal, and event-specific submission/deadline verification. No field effectiveness, clinical outcome, or operational readiness is established.
