# LifeLine demonstration

LifeLine is a clinic electricity planning prototype, aligned with SDGs 7 and 3.
Llama 3.1 8B authors conversation and selects native tools locally; Python
retrieves weather and computes every energy result. No provider API key is needed.
Do not claim clinical validation, guaranteed electricity or measured clinic savings.

## Exact startup commands

From the repository root, with dependencies already installed:

```bash
ollama list
npm --prefix frontend run build
.venv/bin/python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

Open [LifeLine](http://127.0.0.1:8000/) and check
[agent status](http://127.0.0.1:8000/api/agent/status): `available` must be true.
On a fresh machine, install Ollama and run `ollama pull llama3.1:8b` first.
If Ollama is not running, start it in another terminal:

```bash
OLLAMA_HOST=127.0.0.1:11434 OLLAMA_NO_CLOUD=1 ollama serve
```

The production app saves sessions and recent chat in `.local/planning-state.json`.
For a stable location when launching different checkouts, set
`LIFELINE_STATE_PATH` to an absolute writable file. Use one backend process.
`LIFELINE_STATE_PATH=:memory:` deliberately disables persistence. A restart
retains dated results; it does not turn saved weather into a newly fetched forecast.

Windows: replace `.venv/bin/python` with `.\.venv\Scripts\python.exe`.
See [README](README.md) for first-time dependency installation.

## Two-minute story

1. **Configure:** select a clinic/location. In **Clinic Overview → Power setup**,
   show battery/solar capacity and the explicit midnight starting-energy
   assumption. A timestamped current reading is separate. Review a change before
   confirming it; capacity changes retain absolute stored energy unless edited.
2. **Describe work:** ask, “We have a Vaccination campaign from 10 AM to 3 PM
   using the existing refrigerator.” Review the proposed activity. A reference
   to the existing refrigerator does not create another refrigerator. Use the
   explicit confirmation control; chat alone cannot confirm it.
3. **Calculate:** ask, “Can our clinic safely operate tomorrow given the weather
   forecast?” Show the actual forecast source, location, selected date, timezone
   and retrieval time. Explain essential coverage, the battery minimum, any
   unfinished work and limits as computed findings, not a medical safety verdict.
4. **Compare:** show the relevant before/after schedule or tested recovery
   alternative, then the battery timeline. Point to the device/hour changes and
   computed quantities from this run. Explaining a selected option should not
   fetch weather, rerun the solver or reset the selection.
5. **Stress-test:** ask, “Test the confirmed clinic with 50% less sunshine.” Show
   the newly calculated deficit/reserve. If extra supply or output is needed,
   say so. More empty battery capacity cannot repair every shortage.

Allow time for cold-start inference and network retrieval. Simple greetings and
discussion do not require a calculation. Ideas remain unevaluated until a tool
calculates them. Primary chat model failures show a retry and retain the state;
do not present a template or prerecorded answer as a genuine model reply.

In Overview, edit an existing activity, change its time or an explicitly reviewed
device requirement, and confirm. The prior activity stays active until then.
For a configured flexible device, **daily device runtime** is a minimum total-day
work budget, not extra work per activity. Shared references preserve the largest
confirmed requirement and the original baseline work, using one physical device.
Event duration alone never changes electrical demand.

The four Overview panels show activities/equipment, battery energy, plan choices
and real current/seven-day weather. Only the selected supported planning day has
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

## Reproduce primary native conversation checks

With Ollama running and the network available, use an isolated local test session:

```bash
.venv/bin/python scripts/check_conversation_agent.py \
  --output /private/tmp/lifeline-native-conversation-check.json
```

The runner uses actual local model inference and actual Open-Meteo weather,
records native content/calls and timings, and checks review boundaries, repeated
confirmation, selected-plan explanation and effective device runtime. It does
not install hardware or alter the preview's saved session. Run it without
competing model requests. `--sections conversation`, `--sections energy`, or
`--sections activity` isolates a section. A failed real run is a failed check;
neither canned prose nor synthetic forecasts replace it.
