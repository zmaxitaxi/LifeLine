# Native conversation and scoped results

**Current demo:** Claude Haiku (`claude-haiku-5-5`) uses the same session tools, source checks and explicit confirmation boundary. The Llama descriptions and runs below are retained as dated implementation/evaluation history, not the current provider or an automatic fallback. See [Claude setup and latest verification](CLAUDE_DEMO.md).

Session chat uses the existing local `llama3.1:8b`. The model may return ordinary authored content or one native tool call. There is no greeting/help keyword router, explanation-only tool subset, mandatory synthesis tool, or fixed number of options to discuss. All tools valid for the current state remain available. Direct replies can greet, clarify or discuss unevaluated ideas without fetching weather, calculating, staging changes or displaying result cards.

`LocalAgent.session_turn(messages, toolset=...)` returns either `{"type":"message","content":"..."}` or `{"type":"tool_call","call":{"name":"...","arguments":{...}},"content":"..."}`. The existing strict single-tool `decide()` method remains unchanged for stateless compatibility. Successful direct content is returned unchanged after claim validation. Actual domain tool output is fed back into the same ordinary conversation so the model can answer, ask or choose another relevant action. The last twelve persisted user/assistant messages, bounded by character count, support conversational references.

The optional native presentation tool has this schema:

```json
{"name":"respond_to_user","arguments":{"message":"The whole authored reply","fact_references":[],"presentation":{"kind":"conversation","option_ids":[],"show_schedule":false}}}
```

Only `message` is required (1–2400 characters). `fact_references` is an optional list of current source IDs; it is not printed. Presentation kind is `conversation`, `activity_review`, `energy_review`, `calculation` or `explanation`. Direct content defaults to conversation. An explicitly chosen review requires an actual pending proposal; computed presentation requires a fresh current result. Option IDs must belong to that result. The backend binds `input_revision` and `generation` itself; the model cannot invent them. A model can show one relevant tested option, several, only a schedule or none. The application never attaches every option merely because a result exists.

`explain_current_plan` remains read-only and exposes the exact selected option against its existing baseline, without refreshing weather, recalculating or resetting selection. No input regex forces that tool: the model chooses it. `recompute_clinic_plan` performs actual forecast/model work when the model requests a new calculation. Activity and energy-setting tools stage reviewed proposals only. Confirmation/rejection remains an explicit HTTP operator action.

Known clinic settings, device facts, drafts, explicit operator quantities and current verified result facts ground numerical replies. Unknown quantities, unit mismatches, unsupported calculated outcomes, false claims of state changes, clinical guarantees and equipment-control instructions are rejected. General conditional ideas are allowed without pretending they were evaluated. A current result is required for a computed outcome. These checks constrain prose but cannot prove every possible semantic interpretation; a local model may still need clarification or retry. Invalid inference or a timeout returns an explicit retry with completed state changes preserved, never a deterministic replacement narrative.

Nurse terminology, explicit device runtime, shared-device references and existing essential protections are preserved. Existing-device runtime constraints require both physical device identity and explicit device operating duration. Event duration does not imply electrical runtime. Native energy settings use the separately owned `energy_settings_agent` helper; percentages and rated work arithmetic remain Python calculations, and present readings remain distinct from day-start assumptions.

Validation:

```sh
.venv/bin/python -m pytest backend/tests/test_planning_agent.py backend/tests/test_planning_conversation.py backend/tests/test_local_agent.py -q
```

Real-inference evidence is recorded separately from the implementation commit. Test transports deliberately synthesize model replies for regressions and are not evidence of genuine local inference.

Genuine inference observations (unforced native protocol):

- The energy-settings proposal and same-draft correction passed with the real local model: 22.50 seconds and 23.88 seconds, with zero weather calls. Python converted the proposed 12 kWh battery's 50% day-start assumption to 6 kWh and its separate 20% current reading to 2.4 kWh. Changing the starting assumption to 40% produced 4.8 kWh without changing the current reading or active configuration.
- Initial exact clinic/weather question attempts printed a malformed function-call envelope as ordinary content (including Python `True`). Nothing was executed from this text. Explicit native-channel/JSON correction subsequently produced a genuine native calculator call. The live forecast attempt then returned `FORECAST_UNAVAILABLE`; no computed result was claimed. Those failed artifacts remain failure evidence.
- Ordinary greeting, help and unevaluated-idea turns used genuine model-authored content with no weather or state changes. Some initial wording echoed the question; the output guard now rejects a full request echo. Authored text can still be awkward or require retry.

Failed calculation status and its public code are supplied back to the model without private provider text or speculative diagnoses. An unavailable result requested by the model can be handled conversationally; actual state revision conflicts still propagate. Plain replies and computed explanations retain numerical/source and confirmation checks. Recorded timings measure complete local HTTP turns, not just token generation. They are observations, not latency guarantees.

The user subsequently authorized filler weather for a demo. `scripts/check_conversation_agent.py --weather synthetic-demo` explicitly labels that evidence **SYNTHETIC DEMO WEATHER; actual local Llama, real existing physics**. Such a run is not proof of live weather access. Forecast source/data-kind labels are passed to the model; there is no hidden fallback in this agent.

The exact primary question, “Can our clinic safely operate tomorrow given the weather forecast?”, passed on implementation `3493063` with **synthetic demo weather**, genuine `llama3.1:8b` native tools and the unchanged numerical engine. It took 44.32 seconds and one demo-weather service call. The model chose `recompute_clinic_plan`, received actual modeled metrics, then used the read-only `explain_current_plan` after clinical-decision wording was rejected. Its final authored reply reported the verified 1.200 kWh essential-energy shortfall and 6.000 kWh lowest battery level. This validates the electrical demo path, not clinical safety or live forecast availability. `docs/evidence/unforced-primary-synthetic-demo.json` records actual native turns, source labels and calculated metrics. Earlier failed demo attempts remain separate artifacts; they exposed negative-outcome wording false positives and inappropriate clarification, which were corrected with targeted regressions. This is observed success, not a claim that every inference will succeed without retries.

The supplemental genuine activity journey also completed with labeled synthetic demo weather: campaign proposal 81.94 seconds, same-draft 10 AM correction 25.22 seconds, confirmed-campaign 50%-sunshine recomputation 83.56 seconds, and read-only confirmed pump-runtime explanation 55.10 seconds. Explicit HTTP confirmation and its idempotent repeat produced one confirmed activity; the refrigerator remained one physical demand. The manually reviewed pump requirement was correctly reported as “at least 3 hours” with zero weather calls or mutation. The full artifact is `docs/evidence/unforced-activity-synthetic-demo.json`. Invalid native arguments and an invented numerical explanation were rejected before the final authored replies. These observed retries and variable response times remain relevant demo limitations; no speed optimization was added.

The later six-case paired pipeline benchmark is a stronger warning than the earlier single passing demo. `scripts/benchmark_session_pipeline.py` measures actual local `llama3.1:8b`, explicitly synthetic demo weather and the real numerical engine. `docs/evidence/pipeline-before.json`, `pipeline-after.json` and `pipeline-comparison.json` retain every actual attempt, provider token/timing metrics, stage measurements and manual adjudication. The baseline behavior is commit `387b1ce`; the after run includes the compact native context patch `fd1f60b` and parent telemetry/persistence safeguards.

| Case | Before seconds / calls | After seconds / calls | Observed outcome |
|---|---:|---:|---|
| Hello | 63.70 / 5 | 48.30 / 4 | Both failed the intended greeting behavior |
| Tomorrow assessment | 40.14 / 4 | 21.33 / 4 | Before passed; after rejected repeated native string `False` |
| Today vaccination vs selected tomorrow | 100.03 / 7 | 22.12 / 2 | After authored date-review clarification with no mutation/power question; prose did not explicitly restate both dates |
| Recovery | 100.14 / 5 | 72.65 / 4 | Neither produced a validated final reply |
| Exact selected plan | 100.04 / 5 | 58.73 / 4 | Read-only selection retained; neither explanation passed validation |
| History follow-up | 100.00 / 6 | 99.06 / 4 | Neither produced a validated final reply |

Shorter failed requests are not successful speedups. The patch reduces repeated context, omits unknown native nulls before strict validation, supplies clinic-local calendar facts, preserves only the latest tool snapshot/correction and bounds native calls to four. It preserves all tool choices and rejects truncated output. These changes passed 515 backend tests, but they did not make the local model reliably conversational in the measured run. Natural full-date formatting, capitalized native boolean strings and invented unsupported activity fields remained observed failure causes. No fabricated numbers or clinical decisions were substituted for rejected replies.

Provider inference dominated the measured time. For baseline Hello, model HTTP time was 63.55 of 63.70 seconds; numerical work was about 0.034 seconds and weather about 0.0005 seconds. Provider prefill/decode/load timings are actual returned metrics, with missing metrics for cancelled calls left unestimated. MILP timing is nested inside numerical timing. Orchestration residual includes context construction, validation and other work; it is not a separately measured model tool-selection time. These paired calls use the nonstreaming endpoint, so final-content visibility is HTTP completion; they do not measure browser paint or new stream first-progress visibility. The first baseline model request included cold-load time, while the after model was warm. No statistical latency or reliability guarantee follows from one sequential run per version.
