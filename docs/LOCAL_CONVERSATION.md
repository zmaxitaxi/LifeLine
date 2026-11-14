# Natural local conversation and scoped results

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
