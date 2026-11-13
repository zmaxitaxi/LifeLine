# Review of the supplied build brief

Reviewed November 12, 2026, using the supplied Markdown and `zmaxitaxi/LifeLine`. Both the local workspace and the GitHub repository were empty at the start of review; there was no application to inspect or preserve.

## Verdict

The concept and proposed stack are suitable for a focused hackathon prototype. The original scope correctly emphasizes physics, synthetic data, operator-defined critical loads, deterministic optimization, and truthful shortage reporting. The additions below make the handoff sufficiently specific for three people to begin in parallel.

**Person 1’s model, MILP, heuristic, and command-line comparison are implemented and tested.** API and dashboard work remain unimplemented; demo readiness is still conditional on the application checks in [ACCEPTANCE.md](ACCEPTANCE.md). See the [current handoff](PERSON_1_HANDOFF.md). The original review below records the planning decisions and initial repository state.

## Gaps resolved in the detailed specification

| Gap in the original | Why it matters | Decision |
|---|---|---|
| “Implement the MVP” appears inside the attached document | The current request asks for review, detail, division of work, and a push | Preserve the original; deliver a build handoff without treating embedded instructions as a separate request to implement |
| Example loads are small compared with the 14 kWh initial battery | Even a severe solar reduction can leave the storm demo looking healthy | Keep the normal defaults; explicitly use 6 kWh initial energy and 8% cloud multiplier for Storm |
| Unexpected extra demand has no magnitude, category, or hours | Three distinct outcomes are not reproducible | Add a synthetic protected 4.5 kW load during hours 20 and 21 for High Demand |
| Aggregate energy checks omit hourly power bottlenecks | Sufficient daily energy can still leave an hourly shortage | Enforce the discharge limit and show the High Demand rate-limited shortfall |
| Reserve priority and terminal state are underspecified | Flexible jobs could consume reserve or a short horizon could encourage draining the battery | Establish ordered objectives, a feasible reserve floor, and an end-of-day energy objective |
| Shortage slack has no explicit upper bound | A solver could create fictitious shortage energy | Require `0 <= unserved_critical[t] <= critical[t]`; flexible service is zero in a shortage result |
| Charge and discharge could occur together | Artificial energy flows can distort the result | Use one binary battery-mode variable per hour in a small MILP |
| A solver failure could be mistaken for a shortage | Technical failures are not proof of physical infeasibility | Return a structured 503 for timeouts or solver errors; do not report a fabricated energy result |
| An hourly battery field could mean start or end of hour | Charts and metrics can disagree by one hour | Expose both states per hour; construct the chart from 25 battery boundaries, including hour 0 and hour 24 |
| “Hourly deferred” energy has no unique placement | A task deferred beyond the horizon has no meaningful deferred hour | Report deferred energy per task and per day; report actual allocations per hour |
| Baseline and optimized metrics are mixed in one flat response | Baseline shortages and the source of claimed improvement become hard to inspect | Return complete `baseline` and `optimized` results with the same inputs and units |
| Equipment, rate limits, efficiencies, and validation rules are missing from the API example | Three owners would otherwise make incompatible assumptions | Commit a shared TypeScript contract, resolved configuration, error format, and numeric rules |
| Normal versus Storm changes can be misattributed | Storm changes both weather and the initial battery | Show both inputs in the UI; baseline versus optimization is the controlled comparison within each scenario |
| Offline use and integration ownership are implicit | Remote assets or mock responses can break a live demo | Bundle assets and profiles, use a local API proxy, and assign one integration owner |
| No three-person execution plan | Integration tends to occur too late | Assign independent ownership, early handoffs, review partners, and dated integration gates |

## Quantitative calibration

The committed checker uses the exact [scenario configuration](../contracts/scenarios.json), not external weather. It applies a transparent midday sine curve, a 0.80 PV performance ratio, and cloud multipliers.

Normal produces approximately 30.645 kWh of solar against 5.340 kWh of critical and 2.100 kWh of flexible demand. Under the naive baseline it has no unmet energy and a minimum battery level of approximately 12.989 kWh. There is no basis to promise a large outage reduction in this abundant-energy scenario.

With the same 14 kWh initial battery, an 8% solar multiplier still leaves the baseline minimum near 8.748 kWh. Reducing sunshine alone does not create the intended reserve warning with these loads. The Storm preset therefore discloses a 6 kWh initial battery, representing a synthetic depleted start after prior cloudy days. Its critical-only dispatch ends at approximately 2.958 kWh, below the 4 kWh target. Its naive baseline minimum is approximately 0.748 kWh. Because all available surplus is already stored and critical demand must be served, a 4 kWh reserve cannot be maintained even after deferring all 2.100 kWh of flexible tasks.

High Demand retains Normal's weather and starting battery. The additional protected demand makes hours 20 and 21 require 4.660 kWh each, with no solar available. The battery can deliver at most 4.000 kWh per hour. Thus those hours each have at least 0.660 kWh of critical shortfall, independent of sufficient stored energy. The reference critical-only dispatch reaches that 1.320 kWh lower bound.

These are checks on a simplified scenario model, not measured benefits or optimizer performance. The future solver must reproduce these feasibility facts and pass independent conservation tests.

## Verified references

The three original reference links were opened and were available during review. They support the problem context, not the fictional clinic's numerical inputs or the effectiveness of this prototype.

- [WHO: Electricity in health-care facilities](https://www.who.int/news-room/fact-sheets/detail/electricity-in-health-care-facilities) supports the connection between reliable power and health services. Its current page is dated October 15, 2026.
- [WHO: January 14, 2023 announcement](https://www.who.int/news/item/14-01-2023-close-to-one-billion-people-globally-are-served-by-health-care-facilities-with-no-electricity-access-or-with-unreliable-electricity) supports the reported estimate concerning people served by facilities with unreliable or no electricity. Preserve its population and geography qualifiers if used in the pitch.
- [UNDP: Solar for Health](https://www.undp.org/energy/solar-health) is relevant program context. Its page and the WHO page use different statistics and scopes; do not combine them into one unsupported headline.

Technical choices were checked against [SciPy's MILP documentation](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.milp.html), [FastAPI's request-body documentation](https://fastapi.tiangolo.com/tutorial/body/), [Pydantic configuration](https://docs.pydantic.dev/latest/api/config/), and [Vite's setup guide](https://vite.dev/guide/). Pin and validate actual package versions during implementation rather than assuming that reading documentation proves compatibility.

## Open items and assumptions

| Item | Owner | Required action |
|---|---|---|
| Actual teammate names and GitHub handles | Team | Replace role labels when known; no need to delay implementation |
| Event deadline and submission requirements | Person 2 | Verify against the event's actual rules; the supplied brief is the only event source provided |
| Tested dependency versions and target machine | Person 2 | Scaffold, lock dependencies, install on a clean checkout, and record versions |
| Solver behavior, numerical tolerances, and response speed | Person 1 | Implemented and numerically tested; local timing evidence recorded; re-measure on demo laptop |
| Dashboard, API, offline execution, and screenshots | Persons 2 and 3 | Implement and complete the release checklist |
| Hosting | Team | Local demonstration is the MVP target; a public deployment is optional and outside this review delivery |
| Licensing and partner access | Repository owner | Choose a license if desired; no license or external endorsement is assumed |

Do not add trained-model claims, API keys, real clinic data, or hardware integration to close these items. They are unnecessary for the specified demo.

## Scheduling-value adjustment and implementation results

The user prioritized a same-work scheduling demonstration. Added `scheduling` with identical inputs across baseline, heuristic, and MILP. Both alternatives serve 2.1 kWh of flexible work and all critical demand. The daily minimum increases by 0.368421 kWh, midnight battery by 2.210526 kWh, and conversion losses decrease by 0.110526 kWh. Sunshine-first matches MILP in this case; constrained-window tests separately establish when optimization can help. These are computed synthetic outcomes, not measured field benefits.

The earlier three presets are retained for behavior and limitations. Storm and High Demand defer work, so their battery gains must not be presented as the primary same-work improvement. The API/dashboard remain future work under the user’s restriction to Person 1.
