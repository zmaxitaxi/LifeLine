# Validation gaps

## Verified

- Recovery backend comparisons run the existing simulator/MILP with identical weather and absolute initial stored energy. Tests distinguish scheduling, generation, storage and output limits; original work remains in the completion denominator after optional postponement. [Contract and test scope](RECOVERY_PLANNER.md).
- Fresh forecast-backed local Llama recovery tool execution passed six targeted questions on November 13. [Actual native calls, source timestamps and numerical results](docs/evidence/recovery-agent-live-smoke.json). The team's earlier [87.5/100 report](LLM_EVALUATION.md) is a separate evaluation of the previous tool set, with multi-turn and coverage limitations stated.

- Existing model conservation, battery bounds/rates/efficiencies, no simultaneous charge/discharge, fixed essential hours, flexible windows, fair comparisons, infeasible conditions and strict API validation.
- Forecast adapter tests: Open-Meteo's preceding-hour W/m² convention, overlap conversion, local dates, fractional-hour time zones, explicit rejection of 23/25-hour simulation days, missing values/units, night handling, cache/failure behavior and typed tool arguments.
- Actual live forecast retrieval and browser-to-API-to-model execution, with a recorded dated snapshot in [live weather documentation](LIVE_WEATHER.md). This verifies the integration, not forecast accuracy or clinical suitability.
- Browser workflows, responsive layouts and keyboard controls; test scope is recorded separately. No formal accessibility certification is claimed.
- Real local Llama 3.1 8B tool selections, missing-input clarification, additional fixed consecutive-load checks, and computed capacity/weather questions. The five-question final integration run used an explicitly recorded actual forecast because a fresh API connection failed; see [replay evidence](docs/evidence/local-agent-recorded-weather-run.json). It is not a successful fresh live retrieval or a broad language-model benchmark.
- Wajo authentication, schemas and isolated no-action greeting succeeded. Wajo is not a production dependency; no custom planning connector was validated.

## Assumed or unvalidated

- Recovery ranking compares a bounded set of individual sensitivities. It does not establish the globally smallest system, lowest cost, availability of hardware, clinical acceptability or installation feasibility. A recommended tested alternative can still leave deficits; its explicit unresolved requirements must be shown.

- Clinic equipment/duty cycles are illustrative or unverified operator inputs. Published ratings are not measured hourly clinic consumption.
- Enough discretionary load can actually move within staffing and clinical requirements. Divisible hourly energy can be unrealistic for consecutive/noninterruptible appliance cycles.
- Horizontal irradiance and the fixed PV performance ratio adequately approximate a particular installation. No tilt, shading, inverter clipping, measured battery condition or temperature-dependent behavior is modeled.
- Tomorrow's initial battery energy is an explicitly reviewed assumption, not a predicted outcome from today. A single-day forecast/sensitivity comparison is not multi-day reliability analysis.
- Forecast accuracy at clinic scale, model calibration, operator adoption, time saved, real energy savings, health-service outcomes, costs and deployment partnerships are unvalidated.
- Local-model robustness across arbitrary wording, languages, hardware and adversarial input is not established. Native tool allowlists, strict numerical inputs, source/quantity checks and explicit confirmation reduce the effect of model mistakes; natural prose validation does not prove every semantic claim. Missing/invalid responses can require clarification or retry. Primary session chat has no hidden deterministic narrative substitute. The limited Wajo greeting does not validate hosted energy planning. No Claude model was run.
- Local persistence is a private JSON snapshot for one backend process, not authenticated shared storage, a clinical record system or a multi-worker service. Restart recovery and write-failure behavior are tested; hardware storage failure, backups and operational governance remain unvalidated. Saved results retain their original forecast date and retrieval time.
- Live weather is intermittent: the earlier Mac failure was traced to TLS handshaking before HTTP; the same normal route recovered without settings/code changes, and fresh forecast-to-model execution passed at 12:35 PM Pacific on November 13. [Diagnosis](WEATHER_NETWORK.md). The exact server/network component responsible remains unknown; Caden's destination address was not captured. Repeat checks on the presentation network. No forecast-accuracy, availability or uptime guarantee is made.

## Practitioner review and pilot inputs

Interview a clinic facility manager, an energy/maintenance technician and a biomedical equipment practitioner. Observe how they obtain equipment inventories, decide operating windows, review uncertainty and communicate a daily plan. Record disagreements and unavailable inputs rather than assuming usability from a polished interface.

A permitted pilot would need actual array/inverter specifications, orientation/shading, logged generation and load, battery state/usable capacity/rate limits, critical-service requirements, validated appliance cycles, staffing/operating windows and forecast archives across cloudy periods. Compare predictions to logs and measure requirements completion/reserve without changing protected services. Establish success criteria and engineering/clinical oversight before operational use.

## What could invalidate the idea

- Discretionary work is too small or insufficiently movable to produce useful benefits.
- Input collection is more burdensome than the existing planning workflow, or operators cannot obtain reliable inputs.
- Forecast/model errors dominate the reserve margins or apparent scheduling improvement.
- Hardware failure, insufficient supply, power quality or maintenance dominates the problem; scheduling cannot repair these.
- Operators find simpler scheduling rules or established tools adequate. A heuristic tie is an acceptable finding, not a reason to fabricate optimizer superiority.

If these assumptions fail, preserve the transparent reliability/capacity assessment and simplify or reconsider the scheduling product. No claims of clinical validation or guaranteed power are justified by the current tests.
