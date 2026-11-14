# Claude Haiku validation and response measurements

Current provider: **claude-haiku-5-5**, actual Anthropic API inference, with explicitly synthetic demo weather and the unchanged numerical engine. No Llama fallback is used.

## Observed journeys

The final seven-case batch passed six checks. Recovery failed source validation in 10.71 seconds; after the shared-outcome correction, its targeted rerun passed in 6.92 seconds. All seven journey types have targeted successful evidence across these runs. This is not a perfect batch result, a comprehensive accuracy score, or a latency guarantee. Earlier failed provider/format attempts remain recorded.

| Journey | Previous Llama baseline | Haiku batch | Model calls | Successful domain tools |
|---|---|---|---:|---:|
| Greeting | 63.70s / fail | 1.41s / pass | 1 | 0 |
| Tomorrow assessment | 40.14s / pass | 3.87s / pass | 2 | 1 |
| Today/date conflict | 100.03s / fail | 1.87s / pass | 1 | 0 |
| Valid vaccination draft | Not measured | 5.63s / pass | 2 | 1 |
| Recovery recommendation | 100.14s / fail | 10.71s / fail; corrected rerun 6.92s / pass | 4 | 1 |
| Selected-plan explanation | 100.04s / fail | 3.92s / pass | 2 | 1 |
| Conversation history | 100.00s / fail | 5.59s / pass | 2 | 0 |

The valid vaccination draft links the existing refrigerator at 10:00–15:00 and remains unconfirmed. The conflicting today request makes no changes. The selected-plan explanation reuses its calculation without weather retrieval or numerical recomputation. The multi-turn history is an explicit seeded fixture, not claimed as prior model inference. New unspecified devices may correctly need ratings; asking for them is not itself a failure.

Sources: [original baseline](evidence/pipeline-before.json), [failed local optimization](evidence/pipeline-comparison.json), [Haiku seven-case batch](evidence/pipeline-claude-final.json), [corrected recovery](evidence/pipeline-claude-shared-outcome-check.json). The earlier local optimization did not establish reliable conversation; faster failures were not counted as successful speedups.

## Timing and correctness scope

The baseline and provider checks use the same explicitly declared clinic fixture, weather and physics for paired cases; the valid proposal adds the scheduling preset as a separately declared case. Provider, prompts and application validation changed, so these are application-level observations, not an isolated hardware/model speed comparison. Runs were sequential; the final batch had no competing browser fixture or model inference. Earlier Llama runs had cold-load/cancellation and browser-CPU overlap limits documented in their paired report.

The runner wraps actual model HTTP, status retrieval, weather, numerical comparisons/MILP, response serialization, conversation persistence and total request time. Model-native prompt evaluation, generation and loading durations are present for Ollama. Claude provides token usage but not those nanosecond durations; unknown provider timings are not invented. Tool selection occurs inside the same model call as generation and cannot be independently timed as a separate model operation. Orchestration residual includes validation and tool/context preparation; it is not a precise tool-selection time. Numerical/MILP timings overlap, so phase totals must not be summed.

These API timings use the compatible nonstreaming endpoint: first completed assistant content equals final HTTP completion. The UI uses SSE for earlier fixed public activity events and adopts only the final validated result. Server event emission, browser DOM commit, model first token and final reply are different measurements. See [pipeline definitions](AGENT_RESPONSE_PIPELINE.md).

## Reproduce

```bash
.venv/bin/python scripts/benchmark_session_pipeline.py --provider claude --cases conversation,assessment,vaccination,proposal,recovery,followup,history --output /private/tmp/lifeline-haiku-check.json
```

The key must be in the git-ignored server settings. This makes genuine billed API requests; it never changes the active demo clinic. Backend/browser fixture suites do not establish genuine provider latency. A validation failure is preserved as failure evidence; no hardcoded energy narrative replaces it.

## Remaining limits

Native output and strict source checks can still require correction or a retry. External API availability and network access cannot be guaranteed. Results are electrical simulations, not forecast-accuracy studies, measured clinic savings, clinical safety findings, certified sizing or evidence of installed changes. Prices remain unestimated without verified rates. The teammates’ earlier local-model evaluation score does not transfer to Claude.

## Genuine browser visibility

A separate real browser run against the final memory-only preview passed with
actual Haiku and labeled sample weather: Hello completed in 2.272s (one model
call), and assessment in 6.685s (three model calls, one actual numerical tool).
First public-progress DOM commits were 34.8ms and 23.4ms; final answer DOM
commits were 2225.7ms and 6647.7ms. No clinic changes were adopted, hourly chart
values matched the backend, and there were no page errors. These are actual DOM
commit proxies, not pixel-paint or token timings.
[Full evidence](evidence/claude-genuine-browser.json).

## Full vaccination-to-recovery presentation rehearsal

The subsequent full browser workflow uses a fresh scheduling example with actual
Haiku, sample weather and private persistent test state. It covers explicit
activity and energy confirmations, rejected revisions, shared devices, recovery
selection, exact schedule explanation, page reload and backend-restart recovery.
See [the three-prompt two-minute guide](../DEMO_2_MINUTES.md) for the exact setup,
words, clicks, expected computed values and remaining network/model risks.

A repeated short path failed on a true statement that essential demand was met
while flexible work remained unfinished. Source verification now separates these
clauses, retains per-option reserve targets, disambiguates minimum battery from
storage changes, and preserves parenthetical original capacities. Both true and
false cases are regression-tested, including incorrect all-work coverage and
wrong battery-direction language. Existing schedule allocations are now passed
through as source facts; no schedule is invented by Haiku. This follow-up does
not retroactively turn the earlier seven-case batch into a perfect result.
