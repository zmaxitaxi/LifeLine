# LifeLine

LifeLine helps clinic staff compare electricity schedules and understand shortages before making decisions. It combines clearly labeled weather inputs, the existing physical battery simulator and MILP, and a local Llama assistant. It supports SDG 7 and SDG 3 through energy-planning decision support; it does not guarantee electricity or control medical equipment.

**Ready-to-demo mode:** launch with `LIFELINE_WEATHER_MODE=demo` to use explicit synthetic sample weather offline. Llama and all numerical calculations remain real. The user authorized this mode after the Mac's Open-Meteo TLS route failed again. Use `live` for actual forecasts when reachable; there is no hidden substitution. [Sample assumptions](docs/DEMO_WEATHER.md), [network evidence](WEATHER_NETWORK.md), [final release checks](docs/FINAL_RELEASE.md).

**Local AI is implemented:** Llama 3.1 8B through Ollama authors conversation, selects validated tools and explains their results. Python computes all schedules and energy figures. No cloud AI key is required. See the [current demo](DEMO.md), [architecture](ARCHITECTURE.md), [Wajo investigation](WAJO_INVESTIGATION.md) and [objective checklist](FINAL_CHECKLIST.md).

Live weather planning still retrieves today's/tomorrow's Open-Meteo forecasts when reachable; historical NASA and synthetic APIs remain available. Earlier live success and the later TLS-handshake failure are dated separately in [the network investigation](WEATHER_NETWORK.md). Sample weather and recorded forecasts are never presented as a newly fetched live forecast.

LifeLine is an offline-capable electricity planning prototype for staff supporting resource-constrained healthcare clinics. It helps check equipment requirements and compare schedules and infrastructure alternatives; it does not guarantee power or control medical devices.

The application has two pages: **AI Assistant** for conversation and reviewed proposals, and **Clinic Overview** for activities/equipment, battery forecasts, tested plans and labeled weather inputs. Use **Power setup** to review solar/battery capacity, the explicit midnight-charge assumption, a separate timestamped current reading, and expandable technical limits. Edits remain proposals until confirmed; confirmed changes recalculate using the same physical model.

Startup asks for clinic name/location, then electrical inputs, then review. Fields
start blank; **Autofill demo setup** is an explicit secondary option after
choosing a location. A custom setup adds no preset equipment and calculates
nothing automatically. Saved work is available through an explicit **Resume**
choice. Add and review the clinic's equipment before assessing essential power;
zero configured demand is not evidence of reliable electricity.

Before → After scheduling, battery forecasts and relevant tested alternatives explain what changes. Full fixed/sunshine-first/MILP calculations remain available through the numerical contracts. Recovery compares scheduling, solar, storage and battery output with the same weather and absolute starting energy. The seven-day weather outlook is weather information; electrical calculations cover the selected supported 24-hour day, not a week-long reliability prediction.

The primary local assistant uses **Llama 3.1 8B through Ollama** for conversation and native tool selection. Python owns weather retrieval, unit conversion, schedules and numerical verification. Activity and energy-setting changes require explicit operator confirmation. Hypothetical recovery hardware is not installed or adopted by selecting a comparison. The primary chat reports model failure with a retry; legacy rule-based/guided APIs remain separate. Forecasts require internet; explicitly selected historical/synthetic simulation works offline after installation. See [recovery](RECOVERY_PLANNER.md), [activity contracts](docs/ACTIVITY_PLANNING.md), [local conversation](docs/LOCAL_CONVERSATION.md), and [settings/persistence](docs/ENERGY_SETTINGS_AND_LOCAL_STATE.md).

## Run the complete demo

From the repository root, install dependencies and build the dashboard:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r backend/requirements-dev.txt
npm --prefix frontend ci
npm --prefix frontend run build
LIFELINE_WEATHER_MODE=demo python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

On Windows PowerShell, create the environment with `python -m venv .venv`. Skip the `source` line and use `.\.venv\Scripts\python.exe` for the remaining Python commands. Set `$env:LIFELINE_WEATHER_MODE="demo"` before the server command instead of its POSIX environment prefix. The pinned requirements install the IANA timezone data used by the forecast planner on Windows.

Open [LifeLine](http://127.0.0.1:8000/). Build before starting the backend; it serves `frontend/dist` and the API from one local origin. Synthetic/historical planning works offline after installation; fresh forecasts require internet. The optional Swagger explorer uses external assets.

For local AI, install/start Ollama and ensure `ollama list` includes `llama3.1:8b` (already installed on this Mac). If it is not running, use a separate terminal:

```bash
OLLAMA_HOST=127.0.0.1:11434 OLLAMA_NO_CLOUD=1 ollama serve
```

On a fresh machine, `ollama pull llama3.1:8b` downloads the model first. The app accepts only an installed local model with tool capability; cloud records are rejected. `LIFELINE_LOCAL_MODEL` in the backend process environment can select another installed tool-capable model, requiring separate validation. Weights are not bundled in Git. Check `GET /api/agent/status` and **Local AI ready** in the weather panel. Local inference needs memory and may have a slow cold start. No Anthropic setup is needed.

For development, run the backend as above and `npm --prefix frontend run dev` in another terminal; open [localhost:5173](http://127.0.0.1:5173/). `npm --prefix frontend run preview` serves the build on port 4173 with an API proxy.

Workflow: choose a clinic example → ask a question → review and confirm proposed changes → compare the calculated result → test reduced sunshine. Existing activities can be revised through reviewed proposals without adding another physical device. Power settings can be edited manually even when the language model is unavailable. Failed calculations preserve confirmed inputs and expose a retry; outdated results are not presented as the current plan. Equipment is capped at 20 physical devices to bound the prototype's solve size.

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

The backend suite verifies physics, forecast conversion, native tool boundaries, reviewed activity/settings edits and restart recovery. Browser journeys exercise the actual Python API and model with explicitly injected test weather/model transport; real Llama/live-weather evidence is recorded separately. See [the objective checklist](FINAL_CHECKLIST.md) for the latest verification scope. TypeScript/production build and end-to-end checks are required. CI covers Python 3.11/3.12 and Chromium; remote results are in [Actions](https://github.com/zmaxitaxi/LifeLine/actions).

For an isolated local backend, set `LIFELINE_API_PORT` for the frontend and Playwright commands, and start the backend on that port. The default remains 8000. Playwright uses the repo's `.venv` on Windows and Unix, and writes artifacts to `lifeline-playwright-results` in the OS temporary directory unless `LIFELINE_TEST_OUTPUT` is set.

Read [RESEARCH.md](RESEARCH.md), [DATA_SOURCES.md](DATA_SOURCES.md), [PRODUCT_VALIDATION.md](PRODUCT_VALIDATION.md), [computed benchmark](BENCHMARK.md), [demo script](DEMO.md), and [UI verification](docs/FRONTEND_VALIDATION.md). No user interviews, deployment partnerships, measured clinic savings, health outcomes, or guaranteed availability are claimed.

Forecast integration adds 37 independently testable backend checks and four browser checks. A real forecast/browser/model run is recorded in [weather validation evidence](docs/evidence/live-forecast-run.json). These check integration and calculations, not forecast accuracy or clinical outcomes. Forecast browser fixtures invoke the actual Python API/model with injected test weather and are never application fallbacks.

Local-agent contract tests use injected model/weather transport and real numerical calculations. A separate run exercised the actual installed Llama model on five questions using an earlier actual forecast, clearly labeled [recorded replay](docs/evidence/local-agent-recorded-weather-run.json). Repeat fresh live verification with `.venv/bin/python scripts/check_local_agent.py --midnight-battery-kwh 6` when the forecast endpoint is reachable. The prompt sample is not a general language-model evaluation.

## Run the API

From the repository root with Python 3.11+ (locally verified on 3.12.5):

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r backend/requirements-dev.txt
python -m pytest backend/tests -q
python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

Open [API docs](http://127.0.0.1:8000/docs) or [OpenAPI JSON](http://127.0.0.1:8000/openapi.json). Synthetic/historical numerical endpoints work without external services after installation; actual forecasts require internet and model chat requires local Ollama. The optional Swagger UI uses externally hosted JavaScript/CSS.

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

The new **Detailed mode → Load competing-window example** completes 3.8 kWh, versus 2.770 kWh for the existing schedule and 3.470 kWh for sunshine-first, under identical inputs. Essential demand/reserve are protected. This is an unequal-work comparison. Reversing greedy task order closes its completion gap. See [complete inputs, results and caveats](STRONGEST_DEMO.md).

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

The earlier Person 2 milestone had 177 tests; a later milestone had 241 backend/17 browser tests. Current checks and external gaps are recorded above and in [the final checklist](FINAL_CHECKLIST.md). [Person 2 HTTP evidence](docs/evidence/person-2-http-results.json) remains a historical record.

The supplied hackathon deadline is Saturday, November 14, 2026, 11:59 PM America/Los_Angeles; event rules have not been independently verified. The prototype supports investigation of SDG 7 and SDG 3; it does not demonstrate measured health outcomes.

Demo equipment requirements are illustrative; custom requirements are user-entered. The historical weather option uses documented satellite-derived inputs. Illustrative simulation; not for clinical or operational use. No medical equipment control, hardware integration, or real-world certification.

Frontend implementation uses official shadcn/ui source components (Base UI primitives), Tailwind CSS, Recharts, and Lucide React. Cards, buttons, fields, numeric inputs, native selects, hour checkboxes, sunshine slider, disclosures, status badges, and the comparison table share this foundation. The energy model, API, and computed scheduling workflow remain intact. See [hackathon submission checklist](HACKATHON_CHECKLIST.md) for the remaining eligibility/submission questions from the user-supplied event slide.
