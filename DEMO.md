# Two-minute LifeLine demonstration

## Energy recovery backend demonstration

The dedicated backend branch adds calculated recovery comparisons. The separate UI chat owns their chat-first presentation; no frontend navigation is redesigned here.

Start the existing backend as below, then run:

```bash
.venv/bin/python scripts/run_recovery_demo.py
.venv/bin/python scripts/run_recovery_demo.py --live
.venv/bin/python scripts/check_recovery_agent.py --output /private/tmp/lifeline-recovery-agent-check.json
```

The first command explicitly uses bundled NASA POWER Kisumu weather for **14 January 2025**, with illustrative equipment requirements. It calculates the existing schedule and every intervention on demand. The second replaces that historical profile with an actual Open-Meteo forecast; results vary with the date and weather. The third verifies six questions through real installed Llama native tool calls and numerical tools; Ollama must be running. It is an integration smoke, not a comprehensive evaluation score.

In the recorded historical run, protected demand is 14.340 kWh. The existing schedule leaves **1.320 kWh essential energy unserved** and **0.300 kWh flexible work unfinished**. Its 4 kW battery output cannot supply the 4.66 kW protected requirement during two evening hours. The smallest tested resolving output is **5 kW**, with the same 14 kWh initial energy, solar profile, 20 kWh storage and protected requirements. Essential shortage becomes **0**, all **2.100 kWh** flexible work completes, and minimum battery energy is **9.684 kWh**. Extra battery capacity alone leaves the output shortage unchanged. [Computed evidence](docs/evidence/recovery-historical-demo.json).

Show why the bottleneck matters, then review allowed operating times and the hypothetical output change. This does not establish an inverter product rating, installability or clinical safety. The backend cannot install hardware, authorize purchases or control equipment. The 5 kW result is the smallest **tested** candidate, not certified sizing or a cost optimum. Scheduling-only results follow the existing policy that optional work is disabled when protected demand remains unserved; unfinished work is reported honestly.

The real-model smoke also asks about another battery, more panels, moving flexible equipment inside allowed hours, the smallest tested resolving change and 50% lower sunshine. A preferred afternoon time is not promised unless the computed schedule actually uses it. [Native calls, actual forecast and metrics](docs/evidence/recovery-agent-live-smoke.json).

Windows: replace `.venv/bin/python` with `.\.venv\Scripts\python.exe`. Temporary output paths can be changed to a local writable file.

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

**Live-weather update, November 13:** the Mac's normal connection recovered without code or network-setting changes. Fresh actual weather and the complete forecast-to-model calculation passed at **12:35 PM Pacific**. [Diagnosis and recovery](WEATHER_NETWORK.md). Earlier failures were TLS-handshake stalls before HTTP, not an established Mac/Windows application defect. Check the presentation network again; no uptime guarantee is implied. The separate five-question local-LLM replay remains a replay, not a fresh-weather or comprehensive LLM evaluation.

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

This runs the actual local LLM and numerical model using a dated forecast snapshot. It does not configure the running application to use a stale forecast. Evidence: [local-agent replay](docs/evidence/local-agent-recorded-weather-run.json), [earlier actual retrieval](docs/evidence/live-forecast-run.json), [earlier failed connection](docs/evidence/current-live-weather-check.json), [fresh Mac recovery](docs/evidence/mac-weather-live-recovery.json). No presentation video has been recorded by this task.
