# Claude Haiku demonstration

The current assistant is **Claude Haiku**, API model `claude-haiku-5-5`, using low
effort and native tool calls. This replaces Llama as the demo provider at the
user's request. No automatic Llama fallback is used. Old adapter code and dated
Llama evidence remain for provenance; they are not the current demonstration.

Claude chooses the existing tools and authors replies. Python owns forecast
conversion, the battery simulator, fixed/sunshine-first/MILP comparisons, recovery
metrics, source validation and confirmation. The energy model was not replaced.

## Run

Save these settings in the repository's git-ignored `.env.local`:

```dotenv
LIFELINE_AI_PROVIDER=claude
LIFELINE_CLAUDE_MODEL=claude-haiku-5-5
ANTHROPIC_API_KEY=your_key_here
```

Then, with dependencies installed:

```bash
npm --prefix frontend run build
LIFELINE_WEATHER_MODE=demo .venv/bin/python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000/`. `/api/agent/status` must report
`available: true`, `cloud_ai: true`, the Anthropic provider and the configured
Haiku model. Checking status uses authenticated model availability, not a billed
chat request. Never put the API key in frontend variables, browser code or chat.
For another checkout, set `LIFELINE_ENV_FILE` to the absolute settings file.

Windows PowerShell: set `$env:LIFELINE_WEATHER_MODE="demo"` and run
`.\.venv\Scripts\python.exe` without the POSIX environment prefix.

Demo weather is explicitly synthetic and works without Open-Meteo access; Claude
still requires internet and API access. The physical simulator and manual review
forms remain available if the assistant fails. No canned response or another
model silently replaces a failed request.

## Demo flow

1. Choose the clinic location, then explicitly autofill the example electrical
   setup or enter reviewed requirements. Tomorrow is selected in the clinic's
   timezone and displayed for review; setup no longer asks for a date.
2. Say “Hello.” A greeting should not run the energy calculator.
3. Ask “Can our clinic safely operate tomorrow given the weather forecast?”
   Read the computed electrical assessment and the **synthetic demo weather**
   label. This is not a clinical safety verdict or a live forecast claim.
4. Ask about a vaccination campaign with its actual local window and existing
   equipment. Review and explicitly confirm any draft. Shared equipment is
   counted once; event duration does not invent device electricity use.
5. Inspect Overview: current outlook, recommended action and before/after,
   hourly solar/supplied/missing energy with the synchronized battery, followed
   by editable requirements and weather. Pending changes are excluded from
   current results until confirmed.
6. Compare computed recovery alternatives or test reduced sunshine. Selecting
   hypothetical hardware is not installing or adopting it. Unfinished work and
   remaining shortages stay visible; parts costs are explicitly not estimated.

“Today at 10 AM” conflicts with a session configured for tomorrow. The assistant
must explain both clinic-local dates before asking for further activity details;
it cannot silently move the session or confirmed activities to another day.

## Reproduce genuine inference

```bash
.venv/bin/python scripts/benchmark_session_pipeline.py --provider claude --cases conversation,assessment,vaccination,proposal,recovery,followup,history --output /private/tmp/lifeline-claude-check.json
```

The seven cases use actual Claude calls, explicit synthetic weather and real
numerical calculations in isolated sessions. The fixture conversation for the
multi-turn case is declared, not claimed as prior genuine inference. Failed
attempts remain evidence. Test transports in the browser/backend suites are
separate from this genuine-provider check.

The benchmark records complete HTTP latency, native model call counts, actual
reported usage, weather, numerical/MILP runtime, serialization and persistence.
Claude does not report Ollama prompt-evaluation/generation nanoseconds; they are
not fabricated. Numerical phase timings overlap, so their totals are not summed.

Public progress appears before the final validated answer. It is not a first
model token or a completed answer. See [response timing definitions](AGENT_RESPONSE_PIPELINE.md)
and [frontend measurements](../frontend/UX_AND_RESPONSE_TIMING.md).

See [the measured API results and failed attempts](HAIKU_VALIDATION.md) and [genuine browser evidence](evidence/claude-genuine-browser.json).

## Boundaries

Claude requires a valid key, API availability, network access and usage credit.
An external service cannot be guaranteed to always work. Native output can still
require correction or be rejected. API requests are bounded, failures preserve
canonical state, and an interrupted stream is never automatically replayed.

The initial real runs exposed source-validation false positives: full English
dates, units before closing parentheses, battery output confused with storage,
negated safety disclaimers and explicit non-adoption statements. Targeted
regressions cover these plus affirmative false guarantees and results borrowed
from a different tested size. Reported measurements are targeted integration
evidence, not clinical validation or a comprehensive new model score.

Official references: [Haiku model](https://platform.claude.com/docs/en/models/haiku-5-5/overview),
[tool use](https://platform.claude.com/docs/en/agents-and-tools/tool-use/overview),
[latency guidance](https://platform.claude.com/docs/en/test-and-evaluate/strengthen-guardrails/reduce-latency).
