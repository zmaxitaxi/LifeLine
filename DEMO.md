# Two-minute LifeLine demonstration

**Current assistant: Llama 3.1 8B running locally through Ollama.** It understands questions and chooses validated tools. Python computes energy figures, schedules, assessments and explanations. Deterministic offline/guided modes remain as explicit fallbacks; they are not the primary local AI.

## Start and check

If Ollama is not already running, in a separate terminal:

```bash
OLLAMA_HOST=127.0.0.1:11434 OLLAMA_NO_CLOUD=1 ollama serve
```

On a fresh machine, install Ollama and download the model with `ollama pull llama3.1:8b`. This Mac already has both. No Anthropic, OpenAI or Wajo key is needed for the application.

From the repository root:

```bash
npm --prefix frontend run build
.venv/bin/python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

Open [LifeLine](http://127.0.0.1:8000/). Check [agent status](http://127.0.0.1:8000/api/agent/status): `available` must be true. In the weather panel, **Planning assistant** must show **Local AI · validated tools**. If the model is unavailable, the UI labels deterministic fallback; do not present it as an LLM run.

Before presenting, verify fresh weather and the agent:

```bash
.venv/bin/python scripts/check_local_agent.py --midnight-battery-kwh 6
```

**Current verification limitation:** the final November 13 check could not connect to Open-Meteo's API hostname. Earlier actual retrieval is recorded, and the final five-question real-LLM test passed with an explicitly replayed actual forecast. That replay does not establish current live availability and is never silently used by the app. Recheck before presenting; do not call a recording or replay “live.”

## Live storyline

| Time | On screen | Say/do |
|---|---|---|
| 0–15 s | Simple mode, example clinic and location | “A clinic technician needs to know what tomorrow's limited solar/battery system can support. This equipment is illustrative, not a partner clinic's measured inventory.” |
| 15–40 s | Ask “We expect cloudy weather tomorrow. Will we have enough electricity?” | Review location, equipment, hardware and the explicit midnight-charge assumption. Confirm and calculate. Show **Local AI ready**, tool trace, actual forecast date/source/timezone/retrieval time. Leave time for model startup and network latency. |
| 40–65 s | Computed assessment and Before → After schedule | Point to actual tasks moved, work completion, essential coverage and the battery result from this run. Do not promise clinical safety or guaranteed power. |
| 65–90 s | Ask “Run an additional 1 kW sterilizer for 2 hours from 08:00 before noon.” | These are explicitly illustrative operator-supplied values. The tool compares fixed consecutive hourly demand at every allowed start and shows deferred work or shortages. It does not validate a sterilization cycle. Existing essential hours stay fixed. The proposal is hypothetical until **Add fixed requirement to inventory** is clicked. |
| 90–110 s | Ask “What happens if we receive 50% less sunlight?” | Read the computed reduced-sunshine result. Without adopting the proposal, this still uses the original inventory. If showing adoption, click the button, reconfirm inputs and recalculate first. Show the actual reserve/shortage warning. |
| 110–120 s | Limits and next step | “LifeLine makes energy constraints understandable. Next is a technician-reviewed inventory and measured-data pilot. No clinical validation or measured health benefit is claimed.” |

An incomplete sterilization question triggers clarification for missing nameplate power, runtime and permitted start. Do not rehearse against fixed live numerical values: forecasts change.

## Reliable offline demonstration

If live weather is unavailable, show the error openly, select **historical NASA weather** or **synthetic sunshine**, and use the local example planner. Historical/synthetic simulation and the rule-based assistant work offline after installation. These are different data modes, not replacement live forecasts.

Original equal-work example: both alternatives complete 2.1 kWh and preserve 2.211 kWh more at midnight than the fixed schedule. Sunshine-first ties MILP. Distinguish midnight gain from the 0.368 kWh daily-minimum gain.

For the constrained-work example, choose **Detailed mode → Load competing-window example**. The actual model completes all 3.8 kWh; the fixed schedule leaves 1.030 kWh unfinished and sunshine-first leaves 0.330 kWh unfinished. Essential demand/reserve are protected. Reversing greedy task order closes the completion gap. See [full inputs and caveats](STRONGEST_DEMO.md).

To repeat the explicitly labeled recorded-forecast local-AI verification:

```bash
.venv/bin/python scripts/check_local_agent.py --midnight-battery-kwh 6 \
  --recorded-forecast docs/evidence/live-forecast-run.json
```

This runs the actual local LLM and numerical model using a dated forecast snapshot. It does not configure the running application to use a stale forecast. Evidence: [local-agent replay](docs/evidence/local-agent-recorded-weather-run.json), [earlier actual retrieval](docs/evidence/live-forecast-run.json), [current availability check](docs/evidence/current-live-weather-check.json). No presentation video has been recorded by this task.
