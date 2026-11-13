# Final objective checklist

Updated November 13, 2026. This is the status of the final brief, not a claim of clinical deployment. The user's later instruction selected local AI instead of Claude.

| Brief objective | Status | Evidence / remaining limit |
|---|---|---|
| 1. Investigate Wajo | Complete within scope | Authenticated MCP discovery, typed schemas, read-only listing and isolated no-action greeting succeeded. Python connectivity verified. Costs, restricted custom-tool orchestration and production embedding remain unvalidated. [Decision and evidence](WAJO_INVESTIGATION.md). |
| 2. Genuine AI assistant | Implemented and locally tested | Llama 3.1 8B/Ollama chooses validated tools for forecasts, missing-input clarification, consecutive fixed-load proposals and capacity search. Python owns calculations and explanations. Original priorities cannot be changed by agent tools. Explicit UI adoption changes the inventory. Deterministic fallback preserved. |
| 3. Real-world problem research | Desk research complete; field validation open | WHO/World Bank/SEforALL/UNDP support reliability and load-assessment needs. Evidence does not establish clinic adoption or sufficient movable demand. Positioning is broader reliability/capacity support with scheduling as an action. [Research](RESEARCH.md), [gaps](VALIDATION_GAPS.md). |
| 4. Stronger demo | Complete computationally | Original equal-work battery example retained with an honest heuristic tie. New window/output-limit example completes all 3.8 kWh versus 2.770 fixed / 3.470 sunshine-first. Reversing greedy task order closes the gap. Identical-input regression tests; [results](STRONGEST_DEMO.md). |
| 5. Energy/data audit | Verified within stated model; device validation open | Conservation, state/rate/capacity/efficiency constraints, essential protection, windows, unmet demand, timezone/radiation alignment, missing data, failure/cache behavior and fair comparisons tested. Divisible loads are not appliance cycles. New fixed consecutive-hour checks do not certify medical treatment or starting surges. |
| 6. Simple user experience | Implemented; final browser regression recorded below | Simple default retained; location, input source, midnight review, assessment/actions, Before → After, visible limits and conversation. Detailed/Advanced retain existing functionality. Keyboard/mobile tests and explicit stale-result invalidation; no formal accessibility certification. |
| 7. Operational credibility | Documentation complete; pilot open | Initial user is an energy technician with a facility manager. Explicit input provenance/review. [Input acquisition and prototype → pilot → future pathway](OPERATIONS.md). No partner clinic, interview or measured benefit claimed. |
| 8. Hackathon story and submission materials | Prepared; actual submission open | Updated [two-minute demo](DEMO.md), [submission text](SUBMISSION.md), README, architecture, research and validation gaps. Public searches found the organization's site but not an official event rubric/submission form. No organizer message, submission, hosted deployment or video was made. |
| 9. Final verification | Automated/local checks pass as recorded; fresh weather unavailable in latest attempt | Earlier actual Open-Meteo integration succeeded. Current final check cannot connect to API hostname; typed unavailable response and explicit offline modes verified. Five real local-LLM journeys passed with an explicitly replayed earlier actual forecast, not a new live retrieval. |

## Verification evidence

- Backend: **266 tests passed** with Python 3.12; one upstream Starlette/AnyIO deprecation warning. CI also targets Python 3.11.
- Frontend: production build and TypeScript pass; **22 Chromium journeys passed** in the final complete run, including explicit adoption and selected lower-sunshine schedules.
- Real local model: all five targeted questions completed through actual local Llama inference and real numerical calculations in [recorded-weather replay evidence](docs/evidence/local-agent-recorded-weather-run.json). A small integration sample, not a general language-model benchmark.
- Live weather: [earlier successful retrieval](docs/evidence/live-forecast-run.json); [latest failed availability check](docs/evidence/current-live-weather-check.json). No invented or unlabeled substitute weather.
- Wajo: [sanitized authenticated evidence](docs/evidence/wajo-investigation.json). The app does not load/use the Wajo key.
- Stronger benchmark: [computed input, schedules and metrics](docs/evidence/competing-windows.json). Runtime endpoints do not read the result fixture.
- Credentials: ignored local configuration only. Tracked/untracked release files, bundles and Git history were checked against the actual local key: no matches; `.env.local` is ignored, untracked and mode 0600. [Scan evidence](docs/evidence/credential-check.json). No credential values were printed.

## What remains before presentation/submission

1. Recheck fresh Open-Meteo retrieval on the presentation network. Run `.venv/bin/python scripts/check_local_agent.py --midnight-battery-kwh 6`; it must report local-tool-agent results, not fallback. If unavailable, disclose it and deliberately present historical/synthetic mode. Recorded tests are never described as current live weather.
2. Warm the local model, rehearse the two-minute demo on the final build, and keep the original heuristic tie plus unavoidable-shortage explanation ready.
3. Confirm official rules, eligibility, team registration, exact deadline/timezone, submission URL, required video/hosting and AI/data-source attribution. The user-supplied deadline is November 14, 2026, 11:59 PM Pacific; public organization pages did not verify event-specific rules.
4. Submit through the official form and retain confirmation. Nothing has been submitted automatically. Choose a project license if required; shadcn component licensing is already retained, but a repository-wide license has not been selected by the user.
5. After the hackathon, obtain practitioner feedback and permitted equipment/generation/battery measurements before any operational pilot or impact claim.
