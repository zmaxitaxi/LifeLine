# Validation and release checklist

Current milestone: local Llama 3.1 8B/Ollama selects validated tools; Python computes all numerical answers. The suite contains 266 backend tests and 22 Chromium journeys. Current executed results, fresh-weather connectivity limits and genuine-local-model replay evidence are recorded in [the final checklist](../FINAL_CHECKLIST.md). Earlier milestone descriptions below are historical where they differ. No field or clinical validation is claimed.

## Current interactive MVP status

The configurable application is now implemented on the existing architecture. See [README](../README.md), [research](../RESEARCH.md), [data provenance](../DATA_SOURCES.md), [product validation](../PRODUCT_VALIDATION.md), [computed benchmarks](../BENCHMARK.md), [demo script](../DEMO.md), and [browser verification](FRONTEND_VALIDATION.md).

Working features: editable infrastructure/equipment and hours, automatic valid-input recalculation, three fair schedule comparisons, computed reliability diagnosis, historical NASA weather, adverse-condition testing, Capacity Explorer, and built frontend served with the API. Validation: 194 backend tests, 7 Chromium tests, TypeScript/build, mobile/desktop checks, and offline external-request blocking. No field/clinical outcome or guaranteed availability is established.


The numerical model, API, and interactive dashboard are implemented and tested. The earlier role-specific verification records below are historical; the current application evidence is in [frontend verification](FRONTEND_VALIDATION.md) and the [computed benchmark](../BENCHMARK.md). Hackathon submission and practitioner/clinical validation are separate remaining activities.

## Planning verification

- [x] Original brief reviewed and preserved verbatim.
- [x] Three human implementation roles and integration owner defined.
- [x] Exact synthetic presets and a shared API shape committed.
- [x] Physical dispatch checker verifies preset accounting and calibration without external dependencies.
- [x] Original contextual reference links checked.
- [ ] Event-specific rules and deadline independently verified.

## Current numerical verification

Model tests cover T01–T12 and T17, plus the numerical portion of T18. T13–T16 and the API portion of T18 pass in the API/configuration tests, including strict validation, solver failures, response schemas, fresh computations, and zero critical demand. The current suite has 194 backend tests (62 numerical, 115 API/configuration/contract, and 17 custom-clinic checks), plus seven browser tests. Tests additionally verify the primary same-work scheduling gain, an honest heuristic tie, a constrained-window advantage for MILP, corrupt output rejection, and a shared solve budget.

## Automated check matrix

Use independent assertions on solver outputs, rather than testing only the same helper that constructed the constraints. Unless otherwise stated, absolute energy tolerance is `1e-6 kWh`. Check full precision, not rounded UI values. Person 2 owns the release record; model ownership remains with Person 1.

| ID | Case | Expected assertion | Owner |
|---|---|---|---|
| T01 | Every hour of every preset, both plans | `pv + discharge = served critical + served flexible + charge + curtail`; nonnegative flow bounds | 1 |
| T02 | Daily energy across all presets | Initial battery + solar = final battery + served loads + curtailment + conversion losses | 1 |
| T03 | Normal and Storm solar | Exactly 24 slots; PV exactly zero outside slots 6–17; totals agree with committed inputs | 1 |
| T04 | Near-empty and full battery | All 25 states within `[0, capacity]`; initial value exact; capacity curtailment occurs correctly | 1 |
| T05 | Isolated charging and discharging | Efficiencies applied in the correct direction; external rate limits observed | 1 |
| T06 | Battery mode | No slot has positive charge and discharge simultaneously above tolerance | 1 |
| T07 | Feasible critical profile, including Normal | Critical schedule unchanged; 100% energy coverage; no critical slack used for flexible service | 1 |
| T08 | High Demand defaults | Critical-only and optimized unmet energy approximately 1.320 kWh; shortage slots `[20,21]`; status critical; flexible work fully deferred | 1 |
| T09 | Zero PV and zero initial battery | All critical energy reported unserved; no fabricated supply or negative battery | 1 |
| T10 | Flexible windows, task power/energy caps | All allocations within allowed slots; no per-slot or total over-service; per-task served + deferred = requirement | 1 |
| T11 | Reserve, including initially below target | Storm remains at risk; initial boundary counts; flexible service cannot worsen the feasible floor | 1 |
| T12 | Fair baseline and optimization objectives | Identical inputs; fixed baseline schedule; baseline may leave work unserved; ordered objective priorities respected | 1 |
| T13 | Health/scenarios/simulation API | Contract fields, finite JSON numbers, exactly four preset IDs, effective config, valid response models | 2 |
| T14 | Invalid request/configuration | Reject negative/out-of-range values, invalid enum, unknown fields, null, bool-as-number, NaN/infinity, initial/reserve above capacity, malformed slots | 2 |
| T15 | Defaults and overrides | Omitted fields use selected defaults; explicit zero honored; changing battery size does not silently clamp initial/reserve | 2 |
| T16 | Simulated solver failures | Time limit and numerical/solver failure return structured 503; never report healthy or shortage results without a verified solve | 2 |
| T17 | Repeat same request in pinned environment | Status and physical metrics agree within tolerance; deterministic task ordering observed | 1 |
| T18 | Zero critical-demand denominator and zero reserve | Coverage `null`/N/A when requested critical energy is zero; no NaN or division error; zero reserve accepted | 1 and 2 |

Randomized small valid inputs are useful as an additional accounting check if time allows. Do not replace targeted infeasibility and rate-limit cases with a large superficial test count.

## End-to-end gates

- [x] Backend pinned install, tests, and `pip check` verified in an isolated clean source copy/new virtual environment. Frontend pinned installation and build also verified locally.
- [x] README backend/frontend commands verified locally, including real Uvicorn HTTP calls and built-dashboard navigation. Rehearse on the final presentation laptop.
- [x] `.venv/bin/python -m pytest backend/tests -q`: 194 backend tests pass.
- [x] TypeScript check passes (also included in production build).
- [x] `npm --prefix frontend run build` passes.
- [x] Built frontend reaches the API from the same local server; Vite development/preview proxies are configured.
- [x] All four scenarios calculate fresh API results matching numerical expectations (HTTP and TestClient); UI scenario switching also verified.
- [x] Editable infrastructure/equipment/weather changes recalculate; Reset restores quick-start inputs.
- [x] Rapid switching and request sequence/abort handling verified.
- [x] Loading, validation, unavailable-backend/retry UI verified; backend timeout error mapping tested.
- [x] 375 px and 1440 px layouts inspected without page overflow; wide timeline/table scroll internally.
- [x] Keyboard controls, focus styling, and textual status labels verified; no formal accessibility audit.
- [x] Battery chart shows 25 boundaries, kWh, and reserve reference.
- [x] Served/deferred/unmet metrics and actual task allocations are visible.
- [x] Per-plan warning disclosure remains available independently of optimized status.
- [x] Storm starts with visibly depleted Current charge; the assumptions disclose that prior cloudy days are hypothetical and not simulated. The separate 25% sunshine control changes weather only.
- [x] Browser test blocks external requests while app assets and bundled historical weather calculations run; no physical network-disconnect test claimed.
- [x] Warm local HTTP responses measured at approximately 0.011–0.029 seconds; shared solve-budget failures verified as 503. Re-measure the complete app on the demo laptop.
- [ ] Rehearse against the release commit; confirm no development fixtures are used in the live path.
- [x] Disclaimer, input provenance, and modeling limitations are visible.
- [ ] Verify event requirements and submit the repository/demo materials before the stated deadline.

## Historical ninety-second demonstration

The current recommended walkthrough is the [two-minute interactive demo](../DEMO.md), including the primary battery result, Before → After schedule, expandable detail, and Capacity Explorer.

| Time | Action | Evidence and wording |
|---|---|---|
| 0–20 s | Explain the problem | Rural clinics need dependable electricity for essential services. LifeLine explores whether a simple planning tool can help reveal energy constraints. |
| 20–55 s | Show Scheduling improvement | Show existing evening task allocations, then the computed daytime schedule. Both complete 2.1 kWh. Identify 2.211 kWh more at midnight, 0.368 kWh higher daily minimum, and the heuristic tie. |
| 55–70 s | Select Storm | State that this preset changes cloud cover and starts with a depleted battery. Show full critical coverage, deferred optional work, and the remaining reserve warning. |
| 70–80 s | Select High Demand | Show hours 20 and 21 and the computed unmet critical energy. Explain that the 4 kW discharge limit cannot supply the 4.66 kW critical demand, even with stored energy available. |
| 80–90 s | State the scope | This is a deterministic decision-support prototype, with synthetic data and explicit limits; it does not control medical equipment. |

Use the actual release output in narration. If the computation differs after a model change, investigate and update the evidence; do not preserve a scripted number by changing the display alone. A short local screen recording of the working release is an optional presentation fallback, labeled as a recording.

## Release record

November 13, 2026 local verification covered the code candidate `aaa4de9df3b965829b131c44033e0359603b3469` on Windows NT build 26300, Python 3.13.5, SciPy 1.15.3, and Node 24.14.0. The test machine's use as the presentation laptop is unconfirmed.

| Check | Observed result |
|---|---|
| Clean dependency setup | Fresh `.venv` from `python -m venv .venv`. `python -m pip install -r backend/requirements-dev.txt`, `python -m pip check`, and `npm --prefix frontend ci --include=dev` succeeded. The Windows runtime now installs the pinned IANA database. |
| Backend and calibration | `python -m pytest backend/tests -q --tb=short` passed all 241 tests, including OpenAPI snapshot parity, structured solver errors, and forecast cache behavior. Starlette emitted one dependency deprecation warning. `python scripts/check_plan.py` passed all four reference presets. |
| Production build and Chromium | `npm --prefix frontend run build` passed TypeScript and Vite. After Chromium installation, `npm --prefix frontend run test:e2e` with `LIFELINE_API_PORT=8033` passed 17 tests, covering stale input, reset, failure/retry, keyboard/mobile, and built same-origin serving. |
| Local HTTP | Uvicorn on port 8034 served the built index, health, planning status, four scenarios, and three real plans per simulation. Explicit zero PV was preserved and an incompatible capacity returned structured 422. Scheduling and Normal were `OK`; Storm was `RESERVE_AT_RISK`. High Demand returned HTTP 200 with `CRITICAL_SHORTAGE` and 1.320 kWh of essential demand unmet. The slowest of the four observed preset requests was 38 ms on this machine. |
| Offline browser smoke | The built dashboard on port 8034 computed synthetic and bundled Kisumu historical plans with non-local browser requests blocked. |
| Live forecast | `python scripts/check_live_forecast.py --api-url http://127.0.0.1:8034 --midnight-battery-kwh 6` passed its energy-accounting assertions. Open-Meteo retrieved at `2026-11-13T17:48:29.869694Z` for November 14 in Africa/Nairobi. The modeled forecast had 7.844 kWh of solar and no flexible work deferred. The 50%-lower-sunshine case had 3.922 kWh of solar and 2.100 kWh deferred, with zero essential shortfall in both. Chromium verified the computed plan, attribution and sensitivity table using the cached result of that retrieval. |
| Hosted CI | The [baseline run for `f881eea`](https://github.com/zmaxitaxi/LifeLine/actions/runs/43399555064) passed Linux backend Python 3.11/3.12 and frontend Node 22 jobs. The local candidate is unpublished and has no hosted CI run. |

Pending release gates are team rehearsal on the presentation machine, confirmation of official event rules and required links, and submission confirmation. See the [submission checklist](../HACKATHON_CHECKLIST.md). The browser checks above are automated runs. Presentation screenshots were not captured.

Only call the MVP demo-ready after the required gates have evidence. Operational deployment would require separate validated facility data, engineering and healthcare review, and safety/cybersecurity work beyond this hackathon.

## Person 1 verification record

Python 3.12.5; NumPy 2.2.6; SciPy 1.15.3; Pytest 8.3.5. **62 numerical tests passed** (`.venv/bin/python -m pytest backend/tests -q`, 0.68 seconds); independent reference calibration also passes. At the original Person 1 handoff, HTTP/frontend checks were not complete. Those later API and dashboard checks are recorded above. Original supplied brief remains byte-for-byte intact.

## Person 2 verification record

At this milestone, 177 tests passed in the workspace and a clean source copy/new environment; `pip check` succeeded. Live Uvicorn health, scenario listing, OpenAPI, all four simulations, and a 422 validation response were verified. Tests also blocked outbound socket connections while exercising all four calculations. Full-application offline/browser checks were completed in the later MVP work documented above.

Versions: Python 3.12.5, FastAPI 0.115.12, Pydantic 2.14.3, Uvicorn 0.34.2, NumPy 2.2.6, SciPy 1.15.3, Pytest 8.3.5. One dependency-level Starlette/AnyIO deprecation warning is present. Backend CI is configured for Python 3.11 and 3.12; actual remote status is available in GitHub Actions. See [API handoff](PERSON_2_HANDOFF.md) and [HTTP evidence](evidence/person-2-http-results.json).

Cross-platform verification caught floating-point residue slightly above 100% in coverage reporting. Coverage now uses stable ratio arithmetic and stays within 0–100 only after raw flow/aggregate shortage validation. Independent accounting assertions also check the percentage range; energy dispatch and solver priorities are unchanged.

## Final MVP additions

Tests now cover unfamiliar equipment, empty/edited equipment lists, custom cloud profiles, NASA unit/time conversion, storage insufficiency, power-limited essential demand, total energy deficit, constrained task windows, and full Capacity Explorer recalculation. Final tests/build commands and observed results are recorded in [frontend verification](FRONTEND_VALIDATION.md) and [benchmark](../BENCHMARK.md). Earlier 62/177-test counts are historical milestones, not the current total.
