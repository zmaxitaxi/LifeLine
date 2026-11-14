# LifeLine demonstration

**Presenting now? Follow [the rehearsed two-minute guide](DEMO_2_MINUTES.md)** for the exact clinic setup, three copy-paste Haiku prompts, clicks, expected results and recovery steps.

LifeLine is a clinic electricity planning prototype, aligned with SDGs 7 and 3.
Claude Haiku (`claude-haiku-5-5`) authors conversation and selects native tools through the Anthropic API; Python
uses explicit sample weather and computes every energy result. A server-side Anthropic API key and internet are required for the assistant.
Do not claim clinical validation, guaranteed electricity or measured clinic savings.

## Exact startup commands

From the repository root, with dependencies already installed:

```bash
npm --prefix frontend run build
LIFELINE_WEATHER_MODE=demo .venv/bin/python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

Save `ANTHROPIC_API_KEY=...` in the repository's git-ignored `.env.local` first.
Use `LIFELINE_AI_PROVIDER=claude` and `LIFELINE_CLAUDE_MODEL=claude-haiku-5-5`.
Open [LifeLine](http://127.0.0.1:8000/) and check
[agent status](http://127.0.0.1:8000/api/agent/status): `available` and `cloud_ai`
must be true, with the Anthropic provider and Haiku model. No Llama process or
model download is needed. [Full Claude setup and verification](docs/CLAUDE_DEMO.md).

The production app saves sessions and recent chat in `.local/planning-state.json`.
For a stable location when launching different checkouts, set
`LIFELINE_STATE_PATH` to an absolute writable file. Use one backend process.
`LIFELINE_STATE_PATH=:memory:` deliberately disables persistence. A restart
retains dated results; it does not turn saved weather into a newly fetched forecast.

Windows: set `$env:LIFELINE_WEATHER_MODE="demo"`, omit the POSIX prefix and replace `.venv/bin/python` with `.\.venv\Scripts\python.exe`.
See [README](README.md) for first-time dependency installation.

## Two-minute story

1. **Configure:** enter a clinic name and choose its location first. On the
   electrical step, click **Autofill demo setup**, review its editable battery,
   solar, midnight-charge assumption and example equipment, then open the example
   clinic. Alternatively enter real ratings; that custom path adds no example
   devices or automatic calculation. Existing work is explicitly resumable.
2. **Describe work:** ask, “We have a Vaccination campaign from 10 AM to 3 PM
   using the existing refrigerator.” Review the proposed activity. A reference
   to the existing refrigerator does not create another refrigerator. Use the
   explicit confirmation control; chat alone cannot confirm it.
3. **Calculate:** ask, “Can our clinic safely operate tomorrow given the weather
   forecast?” Show the **synthetic demo weather** label, location, selected date,
   assumed timezone and generation time. Explain essential coverage, the battery minimum, any
   unfinished work and limits as computed findings, not a medical safety verdict.
4. **Compare:** show the relevant before/after schedule or tested recovery
   alternative, then the battery timeline. Point to the device/hour changes and
   computed quantities from this run. Explaining a selected option should not
   fetch weather, rerun the solver or reset the selection.
5. **Stress-test:** ask, “Test the confirmed clinic with 50% less sunshine.” Show
   the newly calculated deficit/reserve. If extra supply or output is needed,
   say so. More empty battery capacity cannot repair every shortage.

Claude uses the network; live weather additionally requires Open-Meteo access. Simple greetings and
discussion do not require a calculation. Ideas remain unevaluated until a tool
calculates them. Primary chat model failures show a retry and retain the state;
do not present a template or prerecorded answer as a genuine model reply. The primary demo never silently substitutes Llama.

The current default scheduling demo completes all **2.1 kWh** flexible work and
all **5.34 kWh** essential demand in every schedule. MILP preserves **1.115 kWh**
more energy at midnight and improves the minimum by **0.368 kWh**, removing the
baseline's modeled reserve breaches. Sunshine-first is nearly as good: its final
battery is **5.682 kWh**, versus **5.700 kWh** for MILP and **4.585 kWh** fixed.
These are freshly calculated sample-weather results, not measured clinic savings.
[Inputs, schedules and metrics](docs/evidence/demo-weather-scheduling-proof.json).

In Overview, edit an existing activity, change its time or an explicitly reviewed
device requirement, and confirm. The prior activity stays active until then.
For a configured flexible device, **daily device runtime** is a minimum total-day
work budget, not extra work per activity. Shared references preserve the largest
confirmed requirement and the original baseline work, using one physical device.
Event duration alone never changes electrical demand.

Overview puts the current outlook and recommended action first, followed by the hourly energy chart with its battery, editable requirements, and labeled weather. Other computed alternatives remain expandable. Only the selected supported planning day has
calculated hourly energy. Other dates remain weather information, not invented
seven-day electricity predictions.

## Energy recovery backend demonstration

```bash
.venv/bin/python scripts/run_recovery_demo.py
.venv/bin/python scripts/run_recovery_demo.py --live
.venv/bin/python scripts/check_recovery_agent.py --output /private/tmp/lifeline-recovery-agent-check.json
```

The first command explicitly uses bundled NASA POWER Kisumu weather for
**14 January 2025** and illustrative clinic requirements. The second retrieves
actual Open-Meteo weather; results vary. The third tests the legacy stateless
recovery tool integration with actual local Llama. It is a targeted smoke, not a
new comprehensive evaluation of the primary session chat.

The recorded historical example requests **14.340 kWh** of protected energy.
The existing plan leaves **1.320 kWh** essential demand and **0.300 kWh** flexible
work unfinished. The 4 kW battery output limit is below a 4.66 kW protected
evening load. A hypothetical **5 kW** output limit, the smallest tested resolving
candidate, removes that essential deficit and completes all **2.100 kWh** flexible
work. Minimum battery energy becomes **9.684 kWh**. Solar, 20 kWh capacity,
14 kWh absolute initial energy and equipment requirements remain identical.
Extra storage alone leaves the output bottleneck. This is a modeled comparison,
not certified equipment sizing, a purchase recommendation or installation proof.
[Computed evidence](docs/evidence/recovery-historical-demo.json).

## Scheduling proof and honest fallback

The original synthetic scheduling example completes the same **2.1 kWh** of
flexible work with the fixed, sunshine-first and MILP schedules. Scheduling
preserves **2.211 kWh** more stored energy at midnight and improves the daily
minimum by **0.368 kWh**. Sunshine-first ties MILP; say that openly.

The competing-window benchmark completes **3.8 kWh**, versus **2.770 kWh** fixed
and **3.470 kWh** sunshine-first. Reversing greedy task order closes that gap.
[Inputs, calculations and caveats](STRONGEST_DEMO.md).

If live weather fails, show the error and use the explicitly historical recovery
command or `POST /api/simulate` with a synthetic scenario. These numerical APIs
work offline after installation. Never describe them as a live forecast. Historical
evidence and recorded Llama replays retain their original dates and provenance.
No presentation video or official submission is implied by these checks.

## Historical local-inference checks (not the current demo)

The older Llama runner and evidence are retained for provenance. Do not use it for the Claude-only presentation. To verify the current provider, run the six-case command in [Claude setup](docs/CLAUDE_DEMO.md). The legacy command below is historical:

```bash
.venv/bin/python scripts/check_conversation_agent.py \
  --weather synthetic-demo --sections primary \
  --output /private/tmp/lifeline-native-conversation-check.json
```

The runner uses actual local model inference and explicitly synthetic demo weather,
records native content/calls and timings, and checks review boundaries, repeated
confirmation, selected-plan explanation and effective device runtime. It does
not install hardware or alter the preview's saved session. Run it without
competing model requests. Omit `--sections primary` for the longer full journey.
`--weather live` explicitly exercises actual Open-Meteo access. `--sections conversation`, `--sections energy`, or
`--sections activity` isolates a section. A failed real run is a failed check;
neither canned prose nor an undisclosed weather substitution replaces it.
