# LifeLine submission description

LifeLine is a decision-support prototype for energy technicians and managers supporting solar-powered rural healthcare clinics. Operators enter equipment requirements and energy-system constraints, compare actionable operating schedules, and identify shortages requiring additional resources.

The application retrieves hourly solar-radiation forecasts from Open-Meteo for a selected location, aligns them to local operating hours, estimates PV generation using documented assumptions, and runs the existing physical simulator, sunshine-first heuristic and MILP. It compares forecast conditions with lower-sunshine cases, discloses deferred work and essential shortfalls, and retains offline historical/synthetic modes.

Every displayed energy result comes from the numerical model. Source, date, coordinates, timezone, retrieval time, assumptions and cache/failure status are visible. Mathematical optimization and a structured tool interface are implemented; the current guided assistant is deterministic and no hosted LLM has been validated. Confirm whether the event requires an LLM before claiming eligibility under that requirement.

LifeLine primarily addresses planning relevant to SDG 7, with a potential supporting role for SDG 3. It does not control equipment, guarantee electricity, establish safe clinical operation or demonstrate patient outcomes. Its next validation step is practitioner review and comparison with permitted facility measurements across adverse conditions.

See [DEMO](DEMO.md), [architecture](ARCHITECTURE.md), [weather integration](LIVE_WEATHER.md) and [validation gaps](VALIDATION_GAPS.md). Hosting/video requirements and submission confirmation remain to be verified with organizers.
