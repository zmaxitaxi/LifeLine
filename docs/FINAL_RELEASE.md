# Working hackathon demo release

The local demo runs at `http://127.0.0.1:8020/` using **actual local
llama3.1:8b**, explicitly **synthetic sample weather**, and the unchanged real
PV/battery simulator, sunshine-first heuristic and MILP. No LLM invents energy
calculations. The user authorized sample weather after live Open-Meteo access
failed. No hidden fallback or clinical safety claim is made.

## Delivered workflow

- Startup asks for location and electrical components first. An explicit
  Autofill demo setup button is available on the electrical step; custom setup
  adds no example devices and never calculates automatically. Existing saved
  work is explicitly resumable. Unknown hardware ratings stay unknown.
- AI Assistant and four-panel Clinic Overview retain the professional style.
- Activities/equipment can be drafted in chat or manually, edited and reviewed
  before confirmation. Shared physical devices are counted once.
- Solar/storage/start energy/current reading/technical limits can be reviewed
  inside the same session. Current readings never silently become midnight
  assumptions; capacity changes preserve absolute stored energy.
- The model chooses native tools and authors replies. Ordinary conversation
  need not calculate or display every alternative. Result cards refer to actual
  current generations and intentionally selected tested options.
- Confirmed changes recalculate the model; exact-selected explanation is
  read-only. Stale/conflicting results, unavailable inference and failed storage
  have explicit recovery paths. Manual forms remain usable without Llama.
- Private atomic snapshots retain sessions, receipts and recent conversation.
  The latest Vaccination draft and canonical state were preserved during rollout.
  One late ephemeral greeting was backed up privately but was not imported into
  server history; complete preservation of all old UI-only messages is not claimed.

## Verification

| Check | Result / scope |
|---|---|
| Backend | 503 tests pass, Python 3.12; one upstream deprecation warning |
| Frontend | 46/46 Chromium journeys pass; desktop, narrow preview and phone |
| TypeScript / build | Pass; built app and API serve from durable checkout |
| Deployed preview | Read-only browser smoke passes: setup-first blank entry, explicit autofill/resume, source labels, preserved canonical work, four panels and both editors; no page errors |
| Primary genuine Llama | Exact clinic-weather question passes in 44.32s with sample weather, native calculator and computed response |
| Genuine settings | Proposal and same-draft correction pass in 22.50s / 23.88s; no weather/adoption, separate reading preserved |
| Genuine activities | Four checks pass, including same-draft correction, confirmed requirement retention and read-only effective pump runtime; explicit confirmation is idempotent |

Browser weather/model transports are test fixtures. Separate genuine artifacts
prove actual inference: [primary](evidence/unforced-primary-synthetic-demo.json),
[settings](evidence/unforced-energy-real-model.json),
[activities/runtime](evidence/unforced-activity-synthetic-demo.json).
Earlier failed real attempts remain recorded. These are integration journeys,
not a new comprehensive language-model score. The teammates' earlier 87.5/100
evaluation covers a different tool set.

## Calculated scheduling value

The [default sample-weather proof](evidence/demo-weather-scheduling-proof.json)
uses identical weather, equipment, starting energy and limits for every schedule.
All serve **5.34 kWh essential demand** and **2.1 kWh flexible work**.

| Metric | Fixed | Sunshine-first | MILP |
|---|---:|---:|---:|
| Final battery, kWh | 4.584532 | 5.681938 | 5.699534 |
| Minimum battery, kWh | 4.584532 | 4.952953 | 4.952953 |
| Conversion losses, kWh | 0.383497 | 0.232908 | 0.215311 |

MILP preserves **1.115003 kWh** more at midnight than fixed scheduling and
removes its reserve breaches. Sunshine-first is nearly as good. This is modeled
sample-data value, not measured savings at a real clinic.

## Exact local launch

From the final checkout, with Ollama running:

```bash
LIFELINE_WEATHER_MODE=demo \
LIFELINE_STATE_PATH=/Users/maxli/Documents/ChatGPT/LifeLine/.local/final-planning-state.json \
.venv/bin/python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8020
```

The preserved working source is at
`/Users/maxli/Documents/ChatGPT/LifeLine/.worktrees/final-product`; the original
dirty checkout remains intact. New clones can use the portable commands in
[DEMO.md](../DEMO.md). Do not start a second worker against the same state file.
Do not run competing genuine model tests during a user's live demo turn.

## Practical limits

Llama responses are variable and can require retries. Observed activity turns
took roughly 25–84 seconds; this release does not promise instant replies or
claim performance optimization. Actual live-weather access remains available
with `LIFELINE_WEATHER_MODE=live`, but the Mac route currently stalls during TLS
before HTTP; [dated diagnosis](../WEATHER_NETWORK.md). Demo weather is not a
geographic prediction, and seven-day display rows are not seven-day energy plans.
Field calibration, medical-cycle validation, clinical approval, real impact,
multi-user deployment and official hackathon submission remain outside these
engineering checks.
