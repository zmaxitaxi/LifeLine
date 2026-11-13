# LifeLine

LifeLine is an offline-capable energy reliability planning prototype for technicians and managers supporting resource-constrained healthcare facilities. It helps assess configured requirements and compare scheduling and infrastructure alternatives; it does not guarantee power or control medical devices.

**The interactive application is implemented:** editable clinic/equipment, computed reliability assessment, three operating schedules, battery charts, adverse-weather testing, and Capacity Explorer. It reuses the original simulator, MILP, and FastAPI architecture.

The shadcn/ui + Tailwind interface leads with measured stored-energy improvement and a simple **Before → After** equipment schedule. Coverage, completed work, and conversion losses are smaller supporting metrics. Expand **Detailed analysis** for the 24-hour timeline, battery forecasts, and full sunshine-first comparison. Advanced power/efficiency settings start collapsed; mobile clinic configuration is collapsible so the result appears immediately. Shortages and unequal work completion receive explicit warnings rather than a success claim.

## Run the complete demo

From the repository root, install dependencies and build the dashboard:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r backend/requirements-dev.txt
npm --prefix frontend ci
npm --prefix frontend run build
python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

Open [LifeLine](http://127.0.0.1:8000/). Build before starting the backend; it serves `frontend/dist` and the API from one local origin. No internet is needed for the application after dependencies/datasets are installed. The optional Swagger API explorer uses external assets.

For development, run the backend as above and `npm --prefix frontend run dev` in another terminal; open [localhost:5173](http://127.0.0.1:5173/). `npm --prefix frontend run preview` serves the build on port 4173 with an API proxy.

Workflow: configure infrastructure and equipment → assess reliability → compare actual hourly equipment schedules → test adverse weather → explore a proposed system. Valid changes recalculate after a short debounce; the Generate button recalculates immediately. Existing results are marked stale while inputs differ. Equipment is capped at 20 rows to bound the local prototype's solve size.

Critical hours stay fixed. Flexible duration × power defines energy; the selected existing start fills subsequent allowed slots, with partial-hour energy supported. Flexible work is divisible/interruptible, **not a validated appliance cycle**. Users supply critical/flexible classification; the app does not make medical priorities.

Select synthetic weather or the bundled NASA POWER historical day for Kisumu. The latter is satellite-derived irradiance, not measured clinic production or a live forecast. Demand remains synthetic/user-entered. See [data provenance](DATA_SOURCES.md).

Capacity Explorer runs a new complete calculation with proposed solar, battery, initial energy, and output limit, holding equipment/weather fixed. It reports remaining critical deficits and constraints. It does not provide certified sizing, costs, or installation instructions.

## Tests and evidence

```bash
python -m pytest backend/tests -q
python scripts/check_plan.py
python scripts/prepare_weather.py
python scripts/benchmark.py
npm --prefix frontend run build
cd frontend
npx playwright install chromium
npm run test:e2e
```

Verified locally: **194 backend tests**, **7 Chromium end-to-end tests**, TypeScript/production build, and built-dashboard/API integration. Browser tests include unfamiliar equipment, adding/removing loads, power/duration editing, preset switching, validation/reset, capacity bottlenecks, mobile layout, failure recovery, and bundled historical data with external requests blocked. Backend CI covers Python 3.11/3.12; frontend CI builds and exercises Chromium. Current remote results are available in [Actions](https://github.com/zmaxitaxi/LifeLine/actions).

Read [RESEARCH.md](RESEARCH.md), [DATA_SOURCES.md](DATA_SOURCES.md), [PRODUCT_VALIDATION.md](PRODUCT_VALIDATION.md), [computed benchmark](BENCHMARK.md), [demo script](DEMO.md), and [UI verification](docs/FRONTEND_VALIDATION.md). No user interviews, deployment partnerships, measured clinic savings, health outcomes, or guaranteed availability are claimed.

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

The dashboard now consumes the actual API with request cancellation/stale guards, configurable equipment, all four examples, historical weather, responsive charts, and a Capacity Explorer. Further work is practitioner validation, measured facility inputs, multi-day/uncertainty evaluation, and electrical/clinical review. Drafts are held in browser memory; export computed results as JSON. There is no saved account or device integration.

The earlier Person 2 milestone had 177 passing tests; the current suite has 194 backend tests plus 7 browser tests. See the current evidence above; [Person 2 HTTP evidence](docs/evidence/person-2-http-results.json) remains a historical record.

The supplied hackathon deadline is Saturday, November 14, 2026, 11:59 PM America/Los_Angeles; event rules have not been independently verified. The prototype supports investigation of SDG 7 and SDG 3; it does not demonstrate measured health outcomes.

Demo equipment requirements are illustrative; custom requirements are user-entered. The historical weather option uses documented satellite-derived inputs. Illustrative simulation; not for clinical or operational use. No medical equipment control, hardware integration, or real-world certification.

Frontend implementation uses official shadcn/ui source components (Base UI primitives), Tailwind CSS, Recharts, and Lucide React. Cards, buttons, fields, numeric inputs, native selects, hour checkboxes, sunshine slider, disclosures, status badges, and the comparison table share this foundation. The energy model, API, and computed scheduling workflow remain intact. See [hackathon submission checklist](HACKATHON_CHECKLIST.md) for the remaining eligibility/submission questions from the user-supplied event slide.
