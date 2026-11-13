# Three-person implementation plan

The roles below are ready to assign to actual teammates. Each person owns a bounded part of the repository and reviews another person's work. The three people are human implementation owners; these labels do not imply that three separate contributors have joined or that frontend integration is complete.

The supplied deadline is **Saturday, November 14, 2026, 11:59 PM America/Los_Angeles (PST)**. All times in this plan use that timezone. Person 2 must verify event rules. Target a completed demo at 8:00 PM Saturday and submission by 10:30 PM, leaving 89 minutes before the stated deadline.

## Current progress

Person 1’s numerical modules, sunshine-first heuristic, scheduling-improvement preset, CLI, comparison metrics, and model tests are implemented on `codex/energy-model`. See [PERSON_1_HANDOFF.md](PERSON_1_HANDOFF.md). A2–A7 have implementation/test evidence; A1’s units and interfaces are documented for Person 2 review. Person 2’s backend integration is now implemented and checked against Person 1’s outputs. See [PERSON_2_HANDOFF.md](PERSON_2_HANDOFF.md). Person 3’s dashboard and frontend integration remain pending.

B1–B7 backend deliverables are implemented: endpoints, strict validation, real model orchestration, computed examples, explanations, pinned dependencies, backend CI, clean-install checks, and live HTTP evidence. Frontend version coordination, browser/built-preview checks, and complete release rehearsal await Person 3. Event rules still need an authoritative source.

The primary demo now compares the same amount of completed work under an existing schedule, sunshine-first, and MILP. Keep Normal, Storm, and High Demand as additional behavior/limitation presets.

## Ownership

| Person | Primary ownership | Shared review duty | Avoid editing independently |
|---|---|---|---|
| 1 — Energy and optimization | `backend/app/solar_forecast.py`, `energy_simulator.py`, `optimizer.py`; model tests | Review Person 2's config validation, units, and serialization | Frontend, routes, shared contract |
| 2 — API and integration lead | `main.py`, `models.py`, `scenarios.py`, `explanations.py`; API tests; dependency files; CI; README; release checklist; shared contracts | Review Person 3's API usage and error states | Optimizer internals and UI styling |
| 3 — Dashboard and demo | Entire `frontend/`, including package scripts and lockfile; browser checks; demo script/screenshots | Review Person 1's outputs for understandable labels and truthful claims | Backend internals and shared contracts |

Person 3 creates the frontend dependency files; Person 2 coordinates their versions and CI. Person 2 is the only integration owner for root/shared files. Contract changes are discussed with both consuming owners and committed with corresponding frontend/backend changes; do not let each person invent a separate response format.

## Person 1 — Energy model and optimizer

Work in `codex/energy-model` after the shared foundation is on `main`.

| Order | Work item | Completion evidence |
|---|---|---|
| A1 | Read the shared config and freeze units/time semantics with Person 2 | Agreed 24-slot/25-boundary examples and no undocumented electrical conversion |
| A2 | Implement deterministic solar generation and hourly critical profiles | Nighttime zero, correct units, preset totals match planning checker |
| A3 | Implement pure physical dispatch and naive baseline | No negative battery; priorities, rates, losses, curtailment, and unmet energy checked |
| A4 | Implement critical feasibility and shortage diagnostics | High Demand reports 1.320 kWh shortfall at hours 20 and 21 with flexible work deferred |
| A5 | Implement feasible reserve floor and flexible scheduling | Storm remains amber, Normal serves its work, all windows respected |
| A6 | Add terminal-state/cycling objectives and deterministic ordering | Repeated runs agree within tolerance on the pinned environment |
| A7 | Add meaningful edge-case and accounting tests | T01–T12, T17, and T18 in the acceptance matrix pass |

First handoff: forecast, fixed baseline, and critical-only results for all four presets, callable without FastAPI. Second handoff: full optimized result and structured diagnostic data. Do not return human prose from the numeric solver; give Person 2 facts for templates.

## Person 2 — API, validation, and integration

Work in `codex/api-integration`; coordinate merges into `main`.

| Order | Work item | Completion evidence |
|---|---|---|
| B1 | Scaffold backend, dependency files, repo commands, and CI; agree frontend versions with Person 3 | Clean install and initial CI commands work |
| B2 | Mirror `contracts/api.ts` in Pydantic; resolve shared config and validate overrides | Invalid requests return agreed 422 envelope; explicit zero preserved |
| B3 | Build health/scenario endpoints and the simulate orchestration | Resolved preset and override values match what the UI displays |
| B4 | Provide temporary UI development fixtures matching the contract | Marked fixture-only, physically valid examples; not represented as live solver output |
| B5 | Wire Person 1's functions and return both complete plans | No separate model constants or duplicate simulator in routes |
| B6 | Build computed metrics, warnings, and explanation templates | No unsupported benefit claims; baseline and optimized warnings stay separate |
| B7 | Verify API errors, integration, clean setup, offline run, and release checklist | T13–T16 and end-to-end gates pass; README contains verified commands |

First handoff: health, scenarios, exact request/response examples, and validation behavior. Remove or isolate fixture mode before release. API exceptions are technical failures, never synthetic critical-shortage results. Coordinate cross-cutting changes early; keep an integration branch usable throughout Friday and Saturday.

## Person 3 — Dashboard and demonstration

Work in `codex/dashboard`.

| Order | Work item | Completion evidence |
|---|---|---|
| C1 | Scaffold React/Vite/TypeScript and scripts; import shared API types | Typecheck and production build work |
| C2 | Build main screen, status hierarchy, controls, charts, equipment, assumptions | Complete readable screen using clearly marked development fixtures |
| C3 | Connect to the local API with cancellation and error handling | All four buttons trigger fresh POSTs; stale responses cannot overwrite selection |
| C4 | Make controls and chart semantics agree with effective configuration | Units, 25 battery boundaries, reserve line, requested versus served load are clear |
| C5 | Verify 375 px mobile, 1440 px desktop, keyboard use, contrast, loading and failure states | Screenshots and brief checklist evidence |
| C6 | Rehearse the 90-second demo against live backend results | Storm's lower starting battery and High Demand's power bottleneck are explained accurately |

First handoff: dashboard with agreed fixtures and full loading/error states. Second handoff: the same dashboard consuming real computed API responses, with fixture mode disabled in the release path.

## Schedule and integration gates

Suggested work is roughly 12–16 focused hours per person spread across Friday and Saturday, with buffer for setup and integration. This is an estimate, not a verified delivery promise. If a gate slips, remove stretch features and preserve correctness.

| Target | Person 1 | Person 2 | Person 3 | Gate |
|---|---|---|---|---|
| Thu Nov 12 / first shared session | Confirm units and objectives | Confirm contract and scaffold plan | Confirm UI fields and charts | Everyone agrees on shared files and role ownership |
| Fri Nov 13, noon | Forecast + baseline + critical check | Health/scenarios + validation + fixtures | Complete dashboard skeleton | Preset inputs and response shapes agree |
| Fri Nov 13, 6:00 PM | One optimized Normal scenario | Real simulate route and initial tests | Real API integration | **One complete end-to-end scenario**, no mock in that path |
| Sat Nov 14, noon | All presets + reserve/shortage tests | All API checks + CI | All scenarios and editable controls | Feature-complete MVP; defer stretch work |
| Sat Nov 14, 4:00 PM | Model edge-case fixes | Fresh clone, clean install, offline test | Desktop/mobile and failure-state fixes | Correctness and build gates pass |
| Sat Nov 14, 8:00 PM | Final physical-output review | Freeze release commit, document checks | Rehearse and capture fallback demo | Demo-ready release with known limitations recorded |
| Sat Nov 14, 10:30 PM | Available for submission fixes | Verify required submission fields/links | Final demo materials | Submission complete before the stated deadline |

The critical path is shared contract → physical model → real API → real dashboard → end-to-end checks. UI layout and endpoint scaffolding proceed in parallel, but Friday's real integration gate is mandatory.

## Handoff protocol

Each handoff includes changed files, exact commands run, observed results, and remaining limitations. Small pull requests are useful but not required by this planning delivery. Use one review partner and avoid concurrent edits to the same file.

Before merging code: run the relevant checks, verify one matching response against the contract, and keep `main` runnable once the application exists. Never force-push over another contributor's branch. A contract change requires an example and agreement from both consumers; an optimizer change requires energy and feasibility checks.

## Scope cuts if time is tight

Cut external weather, trained ML, LLM prose, export, custom animations, deployment, and the optional second chart first. Keep all four presets, the battery comparison, fixed/critical load distinction, truthful warnings, physical constraints, tests, and README setup instructions.

If only one scenario is integrated on Friday night, stop adding features and finish real integration. A static mock, an unchecked optimizer, or a UI that hides shortages does not satisfy the MVP.
