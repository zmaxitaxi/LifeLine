# Two-minute LifeLine demonstration

**Default assistant: Llama 3.1 8B running locally through Ollama.** It understands questions and chooses validated tools. Python computes energy figures, schedules, assessments and explanations. Deterministic guided fallback is labeled when used.

## Start and check

If Ollama is not already running, in a separate terminal:

```bash
OLLAMA_HOST=127.0.0.1:11434 OLLAMA_NO_CLOUD=1 ollama serve
```

On a fresh machine, follow the [setup instructions](../README.md#run-the-complete-demo), install Ollama and download the model with `ollama pull llama3.1:8b`. The default application needs no cloud AI key.

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

Check the actual presentation network and warm the model before rehearsing. Forecasts and latency vary; the two-minute timing below is a guide. Dated availability incidents and smoke runs are in the [development record](DEVELOPMENT.md#historical-verification-evidence).

## Live storyline

| Time | On screen | Say/do |
|---|---|---|
| 0–15 s | Simple mode, example clinic and location | “A clinic technician needs to know what tomorrow's limited solar/battery system can support. This equipment is illustrative, not a partner clinic's measured inventory.” |
| 15–40 s | Ask “We expect cloudy weather tomorrow. Will we have enough electricity?” | Review location, equipment, hardware and the explicit midnight-charge assumption. Confirm and calculate. Show **Local AI ready**, tool trace, actual forecast date/source/timezone/retrieval time. Leave time for model startup and network latency. |
| 40–65 s | Computed assessment and Before → After schedule | Point to actual tasks moved, work completion, essential coverage and the battery result from this run. Do not promise clinical safety or guaranteed power. |
| 65–90 s | Ask “Run an additional 1 kW sterilizer for 2 hours from 08:00 before noon.” | These are explicitly illustrative operator-supplied values. The tool compares fixed consecutive hourly demand at every allowed start and shows deferred work or shortages. It does not validate a sterilization cycle. Existing essential hours stay fixed. The proposal is hypothetical until **Add fixed requirement to inventory** is clicked. |
| 90–110 s | Ask “What happens if we receive 50% less sunlight?” | Read the computed reduced-sunshine result. Without adopting the proposal, this still uses the original inventory. If showing adoption, click the button, reconfirm inputs and recalculate first. Show the actual reserve/shortage warning. |
| 110–120 s | Limits and next step | “LifeLine makes energy constraints understandable. Next is a technician-reviewed inventory and measured-data pilot. No clinical validation or measured health benefit is claimed.” |

For an optional follow-up, ask “What happens if we receive 50% less sunlight?” and read the calculated result. An incomplete sterilizer request should ask for missing rated power, duration and operating window; a hypothetical consecutive-load calculation does not certify a medical cycle or silently change the inventory. Do not rehearse against fixed live numerical values.

## When weather is unavailable

If live weather is unavailable, show the error openly, select **historical NASA weather** or **synthetic sunshine**, and use the local example planner. Historical/synthetic simulation and the rule-based assistant work offline after installation. These are different data modes, not replacement live forecasts.

The model CLI also runs without a weather service:

```bash
PYTHONPATH=backend .venv/bin/python -m app.model_demo scheduling
```

The [benchmark](BENCHMARK.md) records the equal-work battery example and honest heuristic tie. Use **Detailed mode → Load competing-window example** for the constructed work-completion case. Reversing greedy task order removes its heuristic gap. See [inputs and caveats](DEVELOPMENT.md#constructed-demonstration-findings).

To repeat the explicitly labeled recorded-forecast local-AI verification:

```bash
.venv/bin/python scripts/check_local_agent.py --midnight-battery-kwh 6 \
  --recorded-forecast docs/evidence/live-forecast-run.json
```

This runs the actual local LLM and numerical model using a dated snapshot. It does not configure the application to use a stale forecast or count as fresh-live verification. The [earlier replay](evidence/local-agent-recorded-weather-run.json) is a five-question integration sample, not the [comprehensive evaluation](DEVELOPMENT.md#local-llm-evaluation).
