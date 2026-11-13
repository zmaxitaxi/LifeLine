# LifeLine

Energy scheduling for a fictional solar-powered clinic. LifeLine compares an existing equipment schedule, a sunshine-first heuristic, and a constrained MILP schedule using identical physical inputs.

**Person 1's numerical implementation is complete. The API and dashboard remain Person 2/3 work.** This branch contains a working command-line model, not a web application.

## Run the model

Python 3.11+ is required; verified here with Python 3.12.5, NumPy 2.2.6, SciPy 1.15.3, and Pytest 8.3.5.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r backend/requirements-model.txt
python -m pytest backend/tests -q
PYTHONPATH=backend python -m app.model_demo scheduling
```

The final command returns complete hourly JSON for all three schedules and computed comparisons. Replace `scheduling` with `normal`, `storm`, or `high_demand` to inspect limitations. No API keys, external services, or internet connection are needed after dependency installation.

## Verified primary demonstration

The `scheduling` preset uses a synthetic 1.5 kW solar array, 8 kWh battery, 6 kWh initial battery, and 4.8 kWh reserve target. The existing schedule runs optional device charging and auxiliary laundry in the evening. Both alternatives move that work into sunshine.

| Computed metric | Existing schedule | Sunshine-first | MILP |
|---|---:|---:|---:|
| Flexible work completed | 2.100 kWh | 2.100 kWh | 2.100 kWh |
| Critical energy coverage | 100% | 100% | 100% |
| Minimum battery across all 25 boundaries | 4.618 kWh | 4.986 kWh | 4.986 kWh |
| Minimum evening battery, 18:00–24:00 | 4.618 kWh | 6.828 kWh | 6.828 kWh |
| Battery at midnight | 4.618 kWh | 6.828 kWh | 6.828 kWh |
| Battery conversion losses | 0.378 kWh | 0.268 kWh | 0.268 kWh |
| Status | Reserve at risk | Within modeled limits | Within modeled limits |

The improvement is **2.211 kWh more stored energy at midnight**, **0.368 kWh higher daily minimum**, and **0.111 kWh less conversion loss**, with the same work completed. These are distinct metrics; do not label the midnight difference as the daily minimum improvement.

**Sunshine-first matches the optimizer's key metrics in this primary case.** A separate constrained-window test demonstrates an advantage for the MILP. No general superiority or empirical clinic benefit is claimed.

Storm still cannot maintain reserve when optional work is deferred. High Demand still has 1.320 kWh critical shortfall due to an hourly discharge limit. Their battery improvements come with less flexible work completed; do not present those as the same-work demonstration.

## Implementation and handoff

- [Person 1 handoff, interfaces, results, limitations](docs/PERSON_1_HANDOFF.md)
- [Machine-readable calculated evidence](docs/evidence/person-1-results.json)
- [Updated build brief](docs/BUILD_BRIEF.md)
- [Three-person responsibilities](docs/TEAM_PLAN.md)
- [Review and current readiness](docs/REVIEW.md)
- [Acceptance checklist and remaining API/UI gates](docs/ACCEPTANCE.md)

The original [source brief](docs/source/LifeLine_Codex_Build_Brief.md) is preserved unchanged. Numerical presets are in [contracts/scenarios.json](contracts/scenarios.json); API shapes are in [contracts/api.ts](contracts/api.ts). Person 2 must extend the outer API response for heuristic/comparison data as described in the handoff. Each numerical plan already follows the existing `PlanResult` fields.

Run the independent reference calibration check:

```bash
python3 scripts/check_plan.py
```

This checks reference dispatch and inputs, separately from the optimizer's tests.

## Remaining work

Person 2 owns FastAPI, Pydantic validation, warnings/explanations, integration, CI, and release packaging. Person 3 owns the interactive comparison, dashboard, and browser checks. Future application commands in the build brief are targets until those components exist.

The supplied hackathon deadline is Saturday, November 14, 2026, 11:59 PM America/Los_Angeles; event rules have not been independently verified. The prototype supports investigation of SDG 7 and SDG 3; it does not demonstrate measured health outcomes.

All clinic inputs are synthetic. Illustrative simulation; not for clinical or operational use. No medical equipment control, hardware integration, or real-world certification.
