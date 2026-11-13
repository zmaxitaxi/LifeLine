# Validation gaps

## Verified

- Existing model conservation, battery bounds/rates/efficiencies, no simultaneous charge/discharge, fixed essential hours, flexible windows, fair comparisons, infeasible conditions and strict API validation.
- Forecast adapter tests: Open-Meteo's preceding-hour W/m² convention, overlap conversion, local dates, fractional-hour time zones, explicit rejection of 23/25-hour simulation days, missing values/units, night handling, cache/failure behavior and typed tool arguments.
- Actual live forecast retrieval and browser-to-API-to-model execution, with a recorded dated snapshot in [live weather documentation](LIVE_WEATHER.md). This verifies the integration, not forecast accuracy or clinical suitability.
- Browser workflows, responsive layouts and keyboard controls; test scope is recorded separately. No formal accessibility certification is claimed.

## Assumed or unvalidated

- Clinic equipment/duty cycles are illustrative or unverified operator inputs. Published ratings are not measured hourly clinic consumption.
- Enough discretionary load can actually move within staffing and clinical requirements. Divisible hourly energy can be unrealistic for consecutive/noninterruptible appliance cycles.
- Horizontal irradiance and the fixed PV performance ratio adequately approximate a particular installation. No tilt, shading, inverter clipping, measured battery condition or temperature-dependent behavior is modeled.
- Tomorrow's initial battery energy is an explicitly reviewed assumption, not a predicted outcome from today. A single-day forecast/sensitivity comparison is not multi-day reliability analysis.
- Forecast accuracy at clinic scale, model calibration, operator adoption, time saved, real energy savings, health-service outcomes, costs and deployment partnerships are unvalidated.
- No hosted language model was run or validated. The guided fallback and structured tools are labeled accordingly. Hackathon LLM eligibility remains an organizer question.

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
