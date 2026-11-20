# LifeLine

LifeLine helps staff at solar-powered clinics decide when to run flexible equipment and identify shortages that scheduling alone cannot resolve. It supports UN SDG 7 (Affordable and Clean Energy) and SDG 3 (Good Health and Well-Being). It is a decision-support prototype for electrical planning. Clinical use and electricity availability require independent verification.

**[Present LifeLine in two minutes](docs/DEMO.md)** · **[Engineering and APIs](docs/ENGINEERING.md)** · **[Weather and data sources](docs/WEATHER.md)** · **[Validation and project history](docs/VALIDATION.md)**

## Run locally

Install Python 3.11 or 3.12 and Node.js 22, the versions used in CI. From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r backend/requirements-dev.txt
npm --prefix frontend ci
npm --prefix frontend run build
```

Copy [.env.example](.env.example) to the git-ignored `.env.local` and set `ANTHROPIC_API_KEY`. The example selects Claude Haiku (`claude-haiku-5-5`). Its key stays on the server. Restart the backend after changing settings. A different checkout can use `LIFELINE_ENV_FILE` to point to the absolute path of the same private settings file.

```bash
LIFELINE_WEATHER_MODE=demo python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

Open [LifeLine](http://127.0.0.1:8000/). FastAPI serves the production frontend build and the API. In PowerShell, create the environment with `python -m venv .venv`, use `.\.venv\Scripts\python.exe` wherever the commands use `python`, and set `$env:LIFELINE_WEATHER_MODE="demo"` before starting the server.

Demo mode uses labeled synthetic weather. For actual Open-Meteo forecasts, restart with `LIFELINE_WEATHER_MODE=live`. After installation, manual planning with sample, synthetic, or bundled historical inputs can run offline. Haiku requires an API key and internet in either mode. Check model availability at [agent status](http://127.0.0.1:8000/api/agent/status).

The default single-process backend saves confirmed inputs, drafts, computed results, and recent chat to the git-ignored `.local/planning-state.json`. Set `LIFELINE_STATE_PATH` to use a separate file or `:memory:` for an unsaved session.

## Plan a clinic day

1. Create a clinic, choose a site or enter coordinates, and review its power setup. For a walkthrough, select **Autofill demo setup** after choosing Kisumu. A custom setup starts with an empty equipment inventory.
2. Review equipment power, essential hours, allowed flexible hours and required work. Review the planning date and assumed midnight battery charge.
3. Ask the assistant to assess the day or draft a change. The assistant calls validated tools and the simulator calculates the results. Review and confirm any proposed changes you want to adopt.
4. In **Clinic Overview**, compare current and proposed equipment hours, battery reserve, and unfinished work. Test lower sunshine and inspect hypothetical recovery options when scheduling is insufficient.

The sample-weather demo completes the same **2.100 kWh** of flexible work with full essential coverage. The optimized schedule preserves **1.115 kWh** more energy at midnight than the existing schedule. Sunshine-first comes close. These are computed results for the example inputs. The [validation report](docs/VALIDATION.md#computed-scheduling-results) includes the three-way comparison and separate benchmark scenarios.

## Verify locally

```bash
python -m pytest backend/tests -q
python scripts/check_plan.py
python scripts/benchmark.py
npm --prefix frontend run build
cd frontend
npx playwright install chromium
npm run test:e2e
```

See [CI runs](https://github.com/zmaxitaxi/LifeLine/actions) for remote verification.
