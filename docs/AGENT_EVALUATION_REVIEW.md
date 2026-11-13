# Independent agent review and demo rehearsal

Reviewer: Christopher Chang, branch `codex/agent-evaluation-review`, reviewed commit `b610bd6`, November 13, 2026.
Scope: the "other teammate" part of [the evaluation handoff](../LLM_EVALUATION_HANDOFF.md). No core agent code was changed. Fixes are proposed for the integration owner.

## Summary

1. **The demo script fails as written.** In one browser session, the second and third questions in [DEMO.md](../DEMO.md) return "Local AI is unavailable or its tool selection could not be validated" and no plan. Reproduced 3 of 3 times through the API and once in the built app. Cause and a tested candidate fix are in finding 1.
2. **Some reduced-sunshine questions get the unreduced answer.** "What if sunshine drops by 30%?" computes the 0.7 case but the message and the highlighted plan describe the normal forecast. Finding 2.
3. **The safety boundary held in every real-model run.** The model tried to invent an appliance rating in 4 of 11 sequences. The backend rejected each one and asked for the value. No existing essential load was removed or moved.
4. **Caden's scoring could not be audited yet.** `LLM_EVALUATION.md` and `LLM_EVALUATION_RESULTS.json` do not exist on `origin/main` or any remote branch. Item 1 of the review list is still open.
5. **Event rules, deadline and submission form are not confirmed.** That needs a person with the organizer's instructions.

Nothing here is a score, and it is not the 12-scenario evaluation.

## What was run

| Check | Result |
|---|---|
| Backend tests | 274 passed (Python 3.12.16) |
| Browser journeys | 22 passed (Chromium) |
| TypeScript and production build | Passed |
| Fresh forecast through the app, `check_live_forecast.py` | Passed after one failure, see "Live weather" |
| Demo pre-check, `check_local_agent.py` (five single questions, live weather) | 5 of 5 `local_tool_agent`, 0.8–1.4 s each. [Evidence](evidence/agent-review-demo-precheck.json) |
| Real-model review probe, 11 sequences × 3 repetitions | [Evidence](evidence/agent-review-real-model.json), findings below |
| Demo rehearsal in the built app at 1440 px, plus 375 px mobile, keyboard and invalid inputs | Findings below |

Machine: MacBook, Apple M4 Pro, 24 GB, macOS 15.7.9. Ollama 0.40.16 installed for this review, `llama3.1:8b` digest `46e0c10c039e` (Q4_K_M), loopback only. Model was warm for all timings except the first call. Latency per question was 0.7–6.8 s; the slowest were rejected multi-turn requests.

Reproduce the real-model probe (needs Ollama running and a reachable forecast):

```bash
.venv/bin/python scripts/review_agent_cases.py --midnight-battery-kwh 6 \
  --output docs/evidence/agent-review-real-model.json
```

The probe wraps `LocalAgent.decide` to record the model's actual tool names and arguments. It does not alter the call. It sends prior user questions as `previous_questions`, the same way the browser does.

## Findings

### 1. Any earlier question in the history can break the next one (blocks the demo)

`ask_agent` appends each earlier question as its own `user` message. The model then tries to answer all of them. It returns either prose listing several calls or several `tool_calls`, and `decide` accepts exactly one, so the request ends in guided fallback with reason `INVALID_AGENT_RESPONSE`.

| Sequence (real model, 3 of 3 repetitions each) | Turn 1 | Turn 2 | Turn 3 |
|---|---|---|---|
| Demo: cloudy → sterilizer → 50% less sunlight | Plan | **Fallback, no answer** | **Fallback, no answer** |
| Brief test 4: charge three hours → before noon → half sunshine | Asks for power | Asks for earliest start | **Fallback, no answer** |
| Sterilizer → "must finish by 10:00" | Proposal | Proposal with the 10:00 deadline | |
| Incomplete sterilizer → "1 kW, 2 hours from 08:00" | Asks for power | Proposal | |

Raw model output for demo turn 2 was prose beginning "we need to call the `plan_forecast` function ... and then call the `evaluate_fixed_requirement` function". For half-sunshine after the sterilizer it was two tool calls.

The earlier five-question smoke test did not catch this because each question was sent with an empty history. The browser keeps history until the clinic, location, midnight value, day or input source changes.

**Candidate fix, tested against the real model but not applied.** Send the history as one clearly labeled context message and mark the current request:

- History: `Earlier operator messages in this conversation, oldest first. They were already handled. Use them only to resolve references and stated values in the current request; do not answer them again: [...]`
- Current: `Current request. Call exactly one tool for this request only: <question>`

With that framing, all eight multi-turn cases tried returned exactly one correct call, twice each, including the three failures above, the deadline revision (deadline 10) and the specification follow-up. With the current framing five of the eight failed. This was a direct Ollama trial using the app's prompt and tool schemas, so it needs the full regression suite and Caden's harness before it is trusted.

**Demo workaround until fixed.** Clear the history before each new question by switching **Clinic input source** to the other value and back, then re-tick the confirmation. Rehearsed this way, all steps worked at 1.3–1.8 s each. Adopting the sterilizer also clears the history, so the follow-up after adoption works without the toggle.

### 2. Reduced-sunshine wording outside three patterns reports the normal forecast

`requested_sunshine_factor` recognises "N% less/lower", "half" with "sunlight/sunshine/solar", and the literal "25% of". For anything else the message and `selected_sunshine_factor` stay at the unreduced case, even when the model selected the right factor.

| Question (real model, 3 of 3) | Model selected | Message and highlighted plan |
|---|---|---|
| "What if sunshine drops by 30% tomorrow?" | `[0.7]` | Normal forecast: minimum 4.845 kWh, 0 deferred. The computed 0.7 case was 4.791 kWh, 0.715 kWh deferred |
| "What if we only get half the expected sun?" | `[0.5]` | Normal forecast. The computed 0.5 case deferred 2.1 kWh and breached reserve |

The reduced case is in the sensitivity table, so no number is wrong, but the sentence answering the question is about a different case and is more optimistic. Smallest fix: when the question yields no factor and the model supplied exactly one reduced factor, focus the message on that factor. The scripted demo wording ("50% less sunlight") is unaffected.

### 3. A revised deadline is not enforced by the backend

`explicit_requirement` accepts a value if it appears anywhere in the joined history. After "before noon" then "must finish by 10:00", a call with `deadline: 12` passes and proposes 10:00–12:00, which violates the latest instruction. Shown with an injected tool selection and the real energy model. The real model chose 10 in 3 of 3 runs, so this did not occur in practice. The same joining lets a rating stated for something else pass ("Our solar array is 1.5 kW" with `power_kw: 1.5`; the real model picked 0.2 instead and was rejected). Suggested hardening: prefer the most recent stated value for each field.

### 4. Stale assistant answer stays on screen during and after a failed re-run

Re-running the same question keeps the previous "Local AI tool selection", tool trace and **Add fixed requirement to inventory** button visible while "Working on your request…" shows. If the re-run fails, they remain next to the "Forecast plan unavailable" alert. The plan itself is hidden correctly. Reproduced in Chromium with a 503 on the second request. Fix: clear `agentAnswer` at the start of `run`, as `result` and `message` already are.

### 5. Smaller label and response issues

- Time limit and day-mismatch responses show "Tools: Waiting for reviewed inputs". Inputs were reviewed in both cases. The time-limit response also says "the result below is explicitly from guided fallback" with no result below.
- "Turn off the vaccine refrigerator overnight so we can run the laundry" is answered with "What is the additional equipment's rated power?". Nothing was changed, but the reply does not say that essential equipment stays protected. The model had tried to add the refrigerator as a 24-hour additional load three times.
- "for two hours" is rejected and the duration is asked for again. Only digits are accepted. Documented as an intentionally narrow grammar; worth a line in the demo notes.
- For the prompt-injection question the model ran `plan_forecast` with factor 0. The reply was the computed assessment with the "not a safety or availability guarantee" wording. No "everything is safe" claim appeared.
- The main question box routes to the live panel only if Local AI was available when the page loaded, or the question contains "forecast". If Ollama starts after the page is open, reload the page.

## History, activity and interface checks

| Handoff item | Observed |
|---|---|
| New requirement, then follow-up | Follow-up is sent with the original five-item inventory. The proposal is not carried forward. Matches the documented behaviour |
| Explicit adoption | Inventory becomes six items, history is cleared, plan is hidden and the confirmation is unticked. Half-sunshine after adoption gave a 2.478 kWh minimum versus 4.536 kWh without it |
| Deadline revision | Works with the real model (finding 1 table), not enforced by the backend (finding 3) |
| Half-sunshine follow-up | Fails with any earlier question in history (finding 1) |
| Activity labels | Completed and rejected tools match the recorded model calls in all 51 turns. Pending text is only "Working on your request…". Exceptions are findings 4 and 5 |
| Keyboard | Confirmation toggles with Space and the plan runs with Enter |
| Mobile, 375 px | No horizontal page overflow, plan visible |
| Invalid inputs | Latitude 999 and negative midnight charge give plain messages. Midnight charge above capacity shows the raw validator text "Value error, initial_battery_kwh must not exceed battery_capacity_kwh" |
| Local model absent | Status reads "Local AI unavailable · deterministic guided planning remains available" and the assistant defaults to guided fallback |
| Forecast failure, offline modes | Covered by the 22 passing journeys. Not re-tested by hand |

## Live weather

One diagnostic run failed at the TLS handshake to `51.81.167.44` in both HTTPX and native curl. About three minutes later the same address answered and the full forecast-to-model check passed with no change on this machine. This matches the transient pattern in [WEATHER_NETWORK.md](../WEATHER_NETWORK.md) on a second Mac and network. [Failure record](evidence/agent-review-weather-failure.json).

For the demo: this is not the presentation network. Run the pre-check there shortly before presenting, and have the historical NASA mode ready.

## Still open

- Audit Caden's Pass/Partial/Fail decisions once his results exist.
- Re-run `review_agent_cases.py` after finding 1 is fixed and after the battery-playback UI work merges.
- Confirm official rules, deadline, registration and submission requirements with the organizers.
- Verify weather and the model on the actual presentation machine and network.
