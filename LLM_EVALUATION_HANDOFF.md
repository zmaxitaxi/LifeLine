# Comprehensive local LLM evaluation handoff

Ownership confirmed by the user: **the two teammates own evaluation; this chat owns integration and fixes.** No comprehensive score has been produced yet. The five-question smoke test must not be presented as the requested 12-scenario, three-repeat evaluation.

## Shared starting point

- Pull integrated `main` before beginning; it includes Caden's Windows timezone data, portable Playwright interpreter and stable OpenAPI descriptions, alongside local-agent changes.
- Model: installed `llama3.1:8b`, Ollama, loopback `http://127.0.0.1:11434`. This Mac has 16 GB memory; actual inference was verified. Record your own hardware, runtime, model digest, context/options and cold/warm conditions.
- Existing endpoints: `GET /api/agent/status`, `GET /api/agent/tools`, `POST /api/agent/ask`. The latter uses a reviewed `AgentRequest` containing the current clinic, location, selected day, midnight-energy assumption, input basis, question and bounded `previous_questions`.
- Existing smoke script: `scripts/check_local_agent.py`. This is not the comprehensive harness. It supports fresh weather or an explicitly recorded actual forecast replay; never label replayed or synthetic weather as live.
- Relevant modules: `local_agent.py`, `agent_tools.py`, `agent_models.py`, `planner_tools.py`, `forecast_planner.py`, and the unchanged simulator/optimizer. Existing tests use injected transport; the requested evaluation must call the real installed model.

The integrated baseline `9aa223f` passed 266 backend tests, 22 browser journeys and the build in an isolated committed checkout. Separate chat-first UI/battery-playback work is in progress and excluded from this baseline. Pin the evaluated commit and rerun affected cases after that work merges.

## Caden: harness and real-model execution

Use a branch such as `codex/local-llm-evaluation`. Own the evaluation script, `LLM_EVALUATION.md`, `LLM_EVALUATION_RESULTS.json` and evaluation-specific regression tests. Preserve the existing architecture and tool permissions.

Run all 12 scenarios in [the original evaluation request](docs/source/Local_LLM_Evaluation_Brief.md) at least three times. Include the stated multi-turn sequence, focused specification follow-ups when missing, and multiple relevant histories. Test requirements must be explicit and labeled illustrative; do not let an evaluator silently supply a missing appliance rating and then award clarification credit.

Capture prompts, actual model selections and arguments, validated execution, tool outputs, final plan JSON, per-turn and per-scenario latency, and deterministic outcomes. The public tool trace currently contains names/status, not full arguments. Add non-invasive evaluation recording around the actual native model call/dispatcher if needed; never fabricate a trace or replace inference with a fixture. Saved artifacts should contain only test scenarios, not secrets or private clinic/patient data.

Define Pass/Partial/Fail criteria before scoring. Use the exact requested weights, repeat-level outcomes and explicit aggregation. Report tool-selection validity, numerical agreement with actual plan fields, retained requirements/deadlines, essential-load invariance, clarification quality, completion, and average/worst latency. A critical safety failure blocks a readiness recommendation regardless of weighted score.

Separate model/tool quality under controlled data from fresh-weather availability. If live weather is unavailable, record the dependency failure and run a second explicitly labeled replay/fixture-weather evaluation with the **real** model. Do not award a fresh-live-data pass for a replay. Caden's Windows run retrieved actual data; this Mac later had a TLS-handshake failure, then recovered without configuration changes and passed fresh forecast-to-model verification at 12:35 PM Pacific November 13. [Network investigation](WEATHER_NETWORK.md). Neither machine's result establishes worldwide provider availability.

Do not implement prompt-specific answers, silently switch providers, use another LLM as the sole judge, or broaden medical/device permissions. Claude benchmarking is optional only if credentials already exist; none is required for this handoff.

## Other teammate: independent review and demonstration

Use a separate branch such as `codex/agent-evaluation-review` and a review note rather than editing Caden's result file concurrently.

1. Audit the reported Pass/Partial/Fail decisions and critical failures against actual calls, arguments, numerical outputs and backend configuration. A plausible answer alone is insufficient.
2. Check history after a new requirement, deadline revision, half-sunshine follow-up and explicit requirement adoption. Current history is bounded user-question history, not a durable conversation/session store. Hypothetical proposals do not modify later requests until adopted.
3. Check that activity labels reflect actual execution. Completed tools are listed after results; the pending message says only “Working on your request.” Do not add invented fetch/solve stages.
4. Check keyboard/mobile behavior, invalid inputs, local-model failure, forecast failure and explicit offline modes. Preserve the current interface.
5. Rehearse `DEMO.md`, verify fresh weather on the actual presentation network, and record demo-machine/runtime details. Confirm official event rules, deadline, registration and required submission links/video/hosting. Do not submit or contact organizers automatically.

## Integration owner in this chat

Complete the merge with current main, keep the branch buildable, apply the smallest verified fixes from the teammates' findings, add meaningful regressions, rerun backend/build/browser checks, and update docs. Core agent changes should be coordinated by reproducible failing case to avoid divergent implementations.

Known limitations to test honestly: narrow tool coverage; no durable server conversation; fixed-hour additional-load proposals rather than arbitrary inventory editing; deterministic numerical renderer rather than free-form model explanations; capacity search does not compare new solar hardware automatically; one-day forecast model; no medical cycle validation. Missing functionality may be Partial/Fail even when the safety boundary holds.

No comprehensive results or score are claimed until the evaluation artifacts exist and actual runs support them.
