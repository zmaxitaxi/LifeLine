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
