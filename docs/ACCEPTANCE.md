# Validation and release checklist

Person 1’s numerical implementation is complete; API and dashboard checks remain uncompleted. Checked model gates do not imply a working web application. See [PERSON_1_HANDOFF.md](PERSON_1_HANDOFF.md) and the [calculated evidence](evidence/person-1-results.json).

## Planning verification

- [x] Original brief reviewed and preserved verbatim.
- [x] Three human implementation roles and integration owner defined.
- [x] Exact synthetic presets and a shared API shape committed.
- [x] Physical dispatch checker verifies preset accounting and calibration without external dependencies.
- [x] Original contextual reference links checked.
- [ ] Event-specific rules and deadline independently verified.

## Current numerical verification

Model tests cover T01–T12 and T17, plus the numerical portion of T18. T14/T15 have numerical input checks only; complete API validation remains Person 2’s responsibility. T13–T16 are not complete as API gates. Tests additionally verify the primary same-work scheduling gain, an honest heuristic tie, a constrained-window advantage for MILP, corrupt output rejection, and a shared solve budget. See test count below.

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

- [ ] Install from a clean checkout using committed dependency files and lockfile.
- [ ] README backend/frontend commands work as written on the demo laptop.
- [x] Numerical tests: `.venv/bin/python -m pytest backend/tests -q` passes (see latest count below). API tests are still pending.
- [ ] `npm --prefix frontend run typecheck` passes.
- [ ] `npm --prefix frontend run build` passes.
- [ ] Built frontend can reach the API using the documented local preview configuration.
- [ ] Scheduling improvement, Normal, Storm, and High Demand each issue fresh API calculations; results match numerical expectations.
- [ ] Editable controls change the effective inputs and results; Reset restores the preset.
- [ ] Rapid scenario switching cannot display a late result under the wrong scenario label.
- [ ] Loading, validation errors, offline backend, timeout, and retry are understandable.
- [ ] At 375 px and 1440 px widths, cards, charts, labels, and equipment remain legible without page overflow.
- [ ] Scenario buttons and controls work with keyboard navigation; focus is visible; status is not conveyed by color alone.
- [ ] Battery chart includes boundary 0 and boundary 24, units in kWh, and reserve reference line.
- [ ] Requested energy, served energy, deferred tasks, and unmet critical energy are distinguishable.
- [ ] Baseline warnings remain visible independently of optimized status.
- [ ] Storm visibly discloses its lower starting battery; no misleading cloud-only comparison.
- [ ] Disconnect external internet after installing dependencies and run all four presets, charts, and local assets successfully.
- [ ] Measure preset response times on the demo laptop; target under 2 seconds; fail visibly if the total solve budget exceeds 5 seconds.
- [ ] Rehearse against the release commit; confirm no development fixtures are used in the live path.
- [ ] Keep the illustrative-use disclaimer and synthetic-input labeling visible.
- [ ] Verify event requirements and submit the repository/demo materials before the stated deadline.

## Ninety-second demonstration

| Time | Action | Evidence and wording |
|---|---|---|
| 0–20 s | Explain the problem | Rural clinics need dependable electricity for essential services. LifeLine explores whether a simple planning tool can help reveal energy constraints. |
| 20–55 s | Show Scheduling improvement | Show existing evening task allocations, then the computed daytime schedule. Both complete 2.1 kWh. Identify 2.211 kWh more at midnight, 0.368 kWh higher daily minimum, and the heuristic tie. |
| 55–70 s | Select Storm | State that this preset changes cloud cover and starts with a depleted battery. Show full critical coverage, deferred optional work, and the remaining reserve warning. |
| 70–80 s | Select High Demand | Show hours 20 and 21 and the computed unmet critical energy. Explain that the 4 kW discharge limit cannot supply the 4.66 kW critical demand, even with stored energy available. |
| 80–90 s | State the scope | This is a deterministic decision-support prototype, with synthetic data and explicit limits; it does not control medical equipment. |

Use the actual release output in narration. If the computation differs after a model change, investigate and update the evidence; do not preserve a scripted number by changing the display alone. A short local screen recording of the working release is an optional presentation fallback, labeled as a recording.

## Release record to fill in

```text
Release commit:
Python / Node / SciPy versions:
Demo laptop / OS:
Backend test command, count, result:
Frontend typecheck result:
Frontend production build result:
Clean install and built-preview check:
Observed preset statuses and unmet energy:
Slowest preset response time:
Offline run result:
Desktop/mobile screenshots:
Known limitations:
Event deadline/rules source:
Submission confirmation:
```

Only call the MVP demo-ready after the required gates have evidence. Operational deployment would require separate validated facility data, engineering and healthcare review, and safety/cybersecurity work beyond this hackathon.

## Person 1 verification record

Python 3.12.5; NumPy 2.2.6; SciPy 1.15.3; Pytest 8.3.5. **62 numerical tests passed** (`.venv/bin/python -m pytest backend/tests -q`, 0.68 seconds); independent reference calibration also passes. No HTTP, frontend build, browser, full-application offline, or deployment checks have been completed. Original supplied brief remains byte-for-byte intact.
