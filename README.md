# LifeLine

LifeLine is an offline-capable electricity planning prototype for staff supporting resource-constrained healthcare clinics. It helps check equipment requirements and compare schedules and infrastructure alternatives; it does not guarantee power or control medical devices.

Live weather planning retrieves today's/tomorrow's Open-Meteo forecasts when reachable; historical NASA and synthetic planning remain available. Weather source, local day, retrieval time and cache/failure status are disclosed. See [weather integration and availability](docs/LIVE_WEATHER.md).

**The interactive application is implemented:** editable clinic/equipment, computed reliability assessment, three operating schedules, battery charts, adverse-weather testing, and Capacity Explorer. It reuses the original simulator, MILP, and FastAPI architecture.

The shadcn/ui + Tailwind interface opens in **Simple mode**: choose a demonstration clinic, ask a question, or choose **Plan tomorrow’s electricity**, **Prepare for cloudy weather**, or **Check battery reliability**. A plan shows an overall assessment, its main limitation, at most three actions, and an equipment timeline. Exact model values and warnings are expandable. **Detailed mode** retains equipment editing, all three schedules, battery charts, computed comparisons, capacity alternatives, and JSON export. **Advanced settings** contains solar/battery capacities, charge, reserve, power limits, efficiencies, sunshine adjustments, and model details.

The primary **local AI assistant** retrieves reviewed configuration and chooses forecast, consecutive-load, capacity or clarification tools. It cannot change existing medical priorities, generate weather, calculate energy independently or control equipment. A hypothetical additional appliance must be explicitly adopted before the inventory changes. Generated prose is not used as numerical evidence. The original **rule-based offline assistant** and **deterministic guided fallback** remain labeled separately. Forecasts require internet; synthetic/historical planning works locally after installation.

## Run the complete demo

From the repository root, install dependencies and build the frontend:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r backend/requirements-dev.txt
npm --prefix frontend ci
npm --prefix frontend run build
python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

On Windows PowerShell, create the environment with `python -m venv .venv`. Skip the `source` line and use `.\.venv\Scripts\python.exe` for the remaining Python commands. The pinned requirements install the IANA timezone data used by the forecast planner on Windows.

Open [LifeLine](http://127.0.0.1:8000/). Build before starting the backend; it serves `frontend/dist` and the API from one local origin. Synthetic/historical planning works offline after installation; fresh forecasts require internet. The optional Swagger explorer uses external assets.

For local AI, install/start Ollama and ensure `ollama list` includes `llama3.1:8b`. If it is not running, use a separate terminal:

```bash
OLLAMA_HOST=127.0.0.1:11434 OLLAMA_NO_CLOUD=1 ollama serve
```

On a fresh machine, `ollama pull llama3.1:8b` downloads the model first. The app accepts only an installed local model with tool capability; cloud records are rejected. `LIFELINE_LOCAL_MODEL` in the backend process environment can select another installed tool-capable model, requiring separate validation. Weights are not bundled in Git. Check `GET /api/agent/status` and **Local AI ready** in the weather panel. Local inference needs memory and may have a slow cold start. No Anthropic setup is needed.

For development, run the backend as above and `npm --prefix frontend run dev` in another terminal; open [localhost:5173](http://127.0.0.1:5173/). `npm --prefix frontend run preview` serves the build on port 4173 with an API proxy.

Workflow: choose a clinic example → ask or choose an action → read the assessment and timeline → change a requirement → inspect updated results. Valid edits recalculate after a short debounce once a plan exists. Previous results are hidden while inputs differ or a conversational requirement is unresolved. Invalid requirements have plain-language errors. If the assistant endpoint fails, **Retry with local planner** runs the entered requirements directly. Equipment is capped at 20 rows to bound the local prototype's solve size.

Critical hours stay fixed. Flexible duration × power defines energy; the selected existing start fills subsequent allowed slots, with partial-hour energy supported. Flexible work is divisible/interruptible, **not a validated appliance cycle**. Users supply critical/flexible classification; the app does not make medical priorities.

Select synthetic weather or the bundled NASA POWER historical day for Kisumu. The latter is satellite-derived irradiance, not measured clinic production or a live forecast. Demand remains synthetic/user-entered. See [data provenance](docs/DATA_SOURCES.md).

Capacity Explorer runs a new complete calculation with proposed solar, battery, initial energy, and output limit, holding equipment/weather fixed. It reports remaining critical deficits and constraints. It does not provide certified sizing, costs, or installation instructions.

## Tests and evidence

With the virtual environment active, run from the repository root:

```bash
python -m pytest backend/tests -q
python scripts/check_plan.py
npm --prefix frontend run build
cd frontend
npx playwright install chromium
npm run test:e2e
```

The backend and Chromium suites cover physical accounting, strict API contracts, local-model tool calling, missing-input clarification, protected equipment, requirement adoption, capacity search, weather failures, stale responses and deterministic fallback. Model/weather transports are injected for repeatability; calculations use the actual Python simulator and optimizer. TypeScript and production-build checks are required. CI covers Python 3.11/3.12 and Chromium; remote results are in [Actions](https://github.com/zmaxitaxi/LifeLine/actions).

For an isolated local backend, set `LIFELINE_API_PORT` for the frontend and Playwright commands, and start the backend on that port. The default remains 8000. Playwright uses the repo's `.venv` on Windows and Unix, and writes artifacts to `lifeline-playwright-results` in the OS temporary directory unless `LIFELINE_TEST_OUTPUT` is set.

See [development issues and process](docs/DEVELOPMENT.md) for acceptance criteria, artifact regeneration, release checks, the comprehensive LLM evaluation requirements and dated verification evidence. A five-question real-model replay is a small integration sample, not a comprehensive evaluation or fresh-weather pass. Repeat live verification against a running backend with `python scripts/check_local_agent.py --midnight-battery-kwh 6`.

## API and model

The setup above starts the API and built frontend together. Open [API docs](http://127.0.0.1:8000/docs) or [OpenAPI JSON](http://127.0.0.1:8000/openapi.json). Runtime-only dependencies are in `backend/requirements.txt`; model-only dependencies are in `backend/requirements-model.txt`.

```bash
curl http://127.0.0.1:8000/api/health
curl -X POST http://127.0.0.1:8000/api/simulate \
  -H 'Content-Type: application/json' \
  -d '{"scenario":"scheduling"}'

# Direct numerical comparison, without a running API or weather service:
PYTHONPATH=backend python -m app.model_demo scheduling
```

`POST /api/simulate` calculates full baseline, sunshine-first and optimized plans using identical inputs. It returns effective configuration, diagnosis, comparison metrics and per-plan warnings. Omitted values use preset defaults; explicit zero is honored; invalid requests return structured 422 errors. A verified physical shortage is HTTP 200, while solver failure is 503. See the [architecture and contract](docs/ARCHITECTURE.md#http-contract-and-errors).

The synthetic `scheduling` benchmark completes the same 2.100 kWh of flexible work with all three methods. Sunshine-first and MILP both preserve 2.211 kWh more at midnight, improve the full-day minimum by 0.368 kWh and reduce conversion loss by 0.111 kWh. These are distinct modeled metrics; the simple heuristic ties the optimizer. The separate competing-window example demonstrates a work-completion difference that disappears when greedy task order is reversed. Full results and caveats are in the [benchmark](docs/BENCHMARK.md) and [development record](docs/DEVELOPMENT.md#constructed-demonstration-findings).

## Documentation

| Document | Purpose |
|---|---|
| [Development issues and process](docs/DEVELOPMENT.md) | Open issues, working process, test/release criteria, LLM evaluation and historical findings |
| [Architecture](docs/ARCHITECTURE.md) | Modules, physics, agent boundaries, validation and API contracts |
| [Data sources](docs/DATA_SOURCES.md) | Weather/equipment provenance, units, assumptions and attribution |
| [Live weather](docs/LIVE_WEATHER.md) | Forecast conversion, timezones, caching, failures and tools |
| [Operations](docs/OPERATIONS.md) | Intended users, input review and prototype-to-pilot pathway |
| [Research](docs/RESEARCH.md) | Source-backed problem context and unresolved product hypotheses |
| [Computed benchmark](docs/BENCHMARK.md) | Reproducible three-way numerical comparisons |
| [Demo](docs/DEMO.md) | Application walkthrough and verification commands |

Numerical presets are in [scenarios.json](contracts/scenarios.json); shared shapes are in [api.ts](contracts/api.ts), [forecast.ts](contracts/forecast.ts), [agent.ts](contracts/agent.ts) and [OpenAPI](contracts/openapi.json). The [calculated scheduling example](contracts/examples/scheduling.response.json) and [evidence files](docs/evidence/) support review and development; they are never undisclosed runtime fallbacks. Superseded briefs and handoffs are consolidated in the development record, with originals retained in Git history.

Demo requirements are illustrative; custom requirements are unverified operator inputs. No interviews, deployment partnerships, measured clinic savings, health outcomes or guaranteed availability are established. Further work requires practitioner feedback, measured facility inputs, multi-day uncertainty evaluation and electrical/clinical review. Drafts remain in browser memory; there are no saved accounts or device integration. Illustrative simulation; not for clinical or operational use.
