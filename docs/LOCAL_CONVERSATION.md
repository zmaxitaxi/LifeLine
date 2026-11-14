# Local conversation and grounded explanations

The session agent uses the existing local `llama3.1:8b` for both validated tool selection and the complete user-facing reply. Greetings, thanks and general capability questions use genuine model-authored prose. Planning actions are followed by a separate local composition call; its full `message` is displayed unchanged after validation. Python does not assemble a successful reply from fixed fact clauses. Missing local inference or invalid prose returns an explicit retry message and preserves completed state changes; there is no silent deterministic narrative substitute.

HTTP/TypeScript contracts are unchanged. Session responses remain `SessionAgentResponse.message + state`. New strict native tools:

```json
{"name":"conversational_reply","arguments":{"kind":"greeting|thanks|help","message":"Model-authored plain English"}}
{"name":"explain_current_plan","arguments":{}}
{"name":"compose_planning_reply","arguments":{"message":"Complete model-authored explanation","fact_references":["essential_summary","scope","option_output","option_battery","option_scheduling"]}}
```

`conversational_reply.message` is 3–450 characters. `compose_planning_reply.message` is 12–1400 characters, and `fact_references` contains 1–10 distinct IDs from the per-call enum. The composition tool is offered separately after real tools complete. Its context is JSON in the user message with `verified_facts`, `required_references` and `recovery_options`. Test transports must handle this additional call; `backend/tests/test_local_agent.py:agent_with` demonstrates a clearly synthetic fixture. Public `tool_calls` continues to list the completed planning actions; raw native composition calls are recorded by the smoke script.

Conversational intent is model-selected for ordinary variants too. Conservative input/output checks prevent an operational or numerical request from using a social reply to bypass calculators. Valid social turns fetch no weather, change no planning revisions and never confirm anything. Existing stateless routes and their compatibility fallback remain available.

`explain_current_plan` reads a fresh current result without recomputation, weather retrieval or selection changes. Its synthesis compares the existing `simulation.baseline` with the exact `selected_recovery_intervention_id`, including that particular size and its actual before/after configuration and metrics. It does not silently substitute a recommended or highest-ranked same-kind option. Broad recovery explanations offer a compact highest-ranked tested alternative per kind; the complete options remain in state.

Quantities must match current cited tool facts with units; local clock hours and operating durations are distinct. Power/energy unit conversions are checked. Unknown quantities, source IDs, metric-label substitutions, repetitive prose, clinical assurances and equipment-control instructions are rejected. These checks constrain model prose; they are not a universal semantic proof. Llama can still need a retry or fail to produce an acceptable explanation. The total session response is bounded to 90 seconds; composition has its own 45-second budget and at most two attempts.

Native equipment handling supports explicit nurse terms essential/critical and optional/nonessential/flexible while retaining separate divisibility permission. Explicit device runtime uses `required_duration_hours`; event duration alone never creates runtime. Model-invented kWh is discarded when only rating and hours were supplied, leaving Python to derive energy. Explicit conflicting kWh is rejected. Reviewed duration revisions reuse known confirmed device specifications. Equipment association requires physical identity; “vaccine campaign” alone cannot match a vaccine refrigerator, while an unambiguous “fridge” can.

Verification:

```sh
.venv/bin/python -m pytest backend/tests/test_planning_agent.py backend/tests/test_planning_conversation.py -q
.venv/bin/python scripts/check_conversation_agent.py --output docs/evidence/conversation-agent-real-model.json
.venv/bin/python scripts/check_activity_agent.py --output docs/evidence/activity-agent-real-model.json
```

Real local runs verified authored Hello/thanks/help and ordinary greeting/help variants with zero weather/state changes. A real Open-Meteo/recovery run produced authored comparisons of the 1.200 kWh baseline deficit with output/rescheduling/storage alternatives; an exact selected 2.4 kW option was explained read-only with zero extra weather calls. Failures during development exposed model-invented interpretations, identifier leakage, repeated paragraphs and quantity-label mistakes; guards rejected these rather than displaying them. Smoke evidence records raw calls and whether the backend was dirty, so individual successful native cases should not be mistaken for universal model reliability.
