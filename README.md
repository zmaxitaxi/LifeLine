# LifeLine

Energy scheduling for a fictional solar-powered clinic. LifeLine compares an existing equipment schedule, a sunshine-first heuristic, and a constrained MILP schedule using identical physical inputs.

**Persons 1 and 2 are implemented: numerical model, FastAPI endpoints, validation, and explanations. Person 3's dashboard remains to be built.**

## Run the API

From the repository root with Python 3.11+ (locally verified on 3.12.5):

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r backend/requirements-dev.txt
python -m pytest backend/tests -q
python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

Open [API docs](http://127.0.0.1:8000/docs) or [OpenAPI JSON](http://127.0.0.1:8000/openapi.json). The JSON endpoints work without external services after installation; the optional Swagger UI uses externally hosted JavaScript/CSS.

In another terminal:

```bash
curl http://127.0.0.1:8000/api/health
curl http://127.0.0.1:8000/api/scenarios
curl -X POST http://127.0.0.1:8000/api/simulate \
  -H 'Content-Type: application/json' \
  -d '{"scenario":"scheduling"}'
```

`POST /api/simulate` returns full `baseline`, `heuristic`, and `optimized` plans, computed `comparison` metrics, effective inputs/equipment, assumptions, warnings scoped to each plan, and deterministic recommendations. All four presets calculate fresh results; no development fixture is used by the routes.

Omit overrides to use a preset's defaults; explicit zero is honored. Invalid values, unknown fields, numeric strings, booleans, and explicit null return structured 422 errors. Battery capacity changes never silently clamp initial energy or reserve. Solver failures return 503, distinct from successful simulations reporting reserve risk or critical shortages (HTTP 200).

Runtime-only installation uses `backend/requirements.txt`; development requirements include tests and the example exporter. Dependencies are pinned. Backend CI checks Python 3.11 and 3.12; check the [workflow results](https://github.com/zmaxitaxi/LifeLine/actions) for remote status.

## Run the model

Python 3.11+ is required; verified here with Python 3.12.5, NumPy 2.2.6, SciPy 1.15.3, and Pytest 8.3.5.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r backend/requirements-model.txt
python -m pytest backend/tests -q
PYTHONPATH=backend python -m app.model_demo scheduling
```

The final command returns complete hourly JSON for all three schedules and computed comparisons. Replace `scheduling` with `normal`, `storm`, or `high_demand` to inspect limitations. No API keys, external services, or internet connection are needed after dependency installation.

## Verified primary demonstration

The `scheduling` preset uses a synthetic 1.5 kW solar array, 8 kWh battery, 6 kWh initial battery, and 4.8 kWh reserve target. The existing schedule runs optional device charging and auxiliary laundry in the evening. Both alternatives move that work into sunshine.

| Computed metric | Existing schedule | Sunshine-first | MILP |
|---|---:|---:|---:|
| Flexible work completed | 2.100 kWh | 2.100 kWh | 2.100 kWh |
| Critical energy coverage | 100% | 100% | 100% |
| Minimum battery across all 25 boundaries | 4.618 kWh | 4.986 kWh | 4.986 kWh |
| Minimum evening battery, 18:00–24:00 | 4.618 kWh | 6.828 kWh | 6.828 kWh |
| Battery at midnight | 4.618 kWh | 6.828 kWh | 6.828 kWh |
| Battery conversion losses | 0.378 kWh | 0.268 kWh | 0.268 kWh |
| Status | Reserve at risk | Within modeled limits | Within modeled limits |

The improvement is **2.211 kWh more stored energy at midnight**, **0.368 kWh higher daily minimum**, and **0.111 kWh less conversion loss**, with the same work completed. These are distinct metrics; do not label the midnight difference as the daily minimum improvement.

**Sunshine-first matches the optimizer's key metrics in this primary case.** A separate constrained-window test demonstrates an advantage for the MILP. No general superiority or empirical clinic benefit is claimed.

Storm still cannot maintain reserve when optional work is deferred. High Demand still has 1.320 kWh critical shortfall due to an hourly discharge limit. Their battery improvements come with less flexible work completed; do not present those as the same-work demonstration.

## Implementation and handoff

- [Person 1 handoff, interfaces, results, limitations](docs/PERSON_1_HANDOFF.md)
- [Person 2 API handoff and Person 3 integration instructions](docs/PERSON_2_HANDOFF.md)
- [Machine-readable calculated evidence](docs/evidence/person-1-results.json)
- [Updated build brief](docs/BUILD_BRIEF.md)
- [Three-person responsibilities](docs/TEAM_PLAN.md)
- [Review and current readiness](docs/REVIEW.md)
- [Acceptance checklist and remaining API/UI gates](docs/ACCEPTANCE.md)

The original [source brief](docs/source/LifeLine_Codex_Build_Brief.md) is preserved unchanged. Numerical presets are in [contracts/scenarios.json](contracts/scenarios.json); API shapes are in [contracts/api.ts](contracts/api.ts) and [OpenAPI](contracts/openapi.json). A [computed scheduling response](contracts/examples/scheduling.response.json) is available for frontend development, not as a live fallback. Regenerate both artifacts with `python scripts/export_api_contract.py` after installing development requirements.

Run the independent reference calibration check:

```bash
python3 scripts/check_plan.py
```

This checks reference dispatch and inputs, separately from the optimizer's tests.

## Remaining work

Person 3 should build the interactive equipment schedule comparison using the real API, with cancellation/loading/error states, editable inputs, all four presets, and responsive charts. Use a Vite `/api` proxy to `http://127.0.0.1:8000`; direct cross-origin requests are not enabled. Frontend build/browser/full-application release checks remain pending.

The current suite has **177 passing tests** (62 model tests plus 115 API/configuration/contract checks), verified in the workspace and a clean source copy with a fresh virtual environment. Live localhost requests confirm all four statuses and the primary improvement. See [HTTP evidence](docs/evidence/person-2-http-results.json).

The supplied hackathon deadline is Saturday, November 14, 2026, 11:59 PM America/Los_Angeles; event rules have not been independently verified. The prototype supports investigation of SDG 7 and SDG 3; it does not demonstrate measured health outcomes.

All clinic inputs are synthetic. Illustrative simulation; not for clinical or operational use. No medical equipment control, hardware integration, or real-world certification.
