# LifeLine submission description

LifeLine is a decision-support prototype for energy technicians and managers supporting solar-powered rural healthcare clinics. Operators enter equipment requirements and energy-system constraints, compare actionable operating schedules, and identify shortages requiring additional resources.

The application retrieves hourly solar-radiation forecasts from Open-Meteo for a selected location, aligns them to local operating hours, estimates PV generation using documented assumptions, and runs the existing physical simulator, sunshine-first heuristic and MILP. It compares forecast conditions with lower-sunshine cases, discloses deferred work and essential shortfalls, and retains offline historical/synthetic modes.

The primary assistant uses local **Llama 3.1 8B through Ollama** to understand requests and choose validated tools. It retrieves current configuration, asks for missing appliance ratings, checks additional fixed consecutive demand before deadlines, and explores whether more battery capacity alone could help. Existing essential equipment is protected; a proposal requires explicit adoption. The numerical model supplies every displayed energy result and assessment. Deterministic guided/offline modes remain as fallbacks. Wajo was tested separately and is not a dependency.

The equal-work demonstration preserves 2.211 kWh more battery energy at midnight; sunshine-first ties the optimizer. A constructed window/power-limit example completes 3.8 kWh, leaving 1.030 kWh less unfinished work than the existing schedule and 0.330 kWh less than sunshine-first. Reversing greedy task order closes that gap. These are numerical examples, not clinic outcomes or universal optimizer superiority.

Source, date, coordinates, timezone, retrieval time, assumptions and cache/failure status are visible. The final fresh-weather check could not connect to the provider API; the real local-agent workflow was verified against an explicitly recorded earlier actual forecast. Disclose this until fresh retrieval is reverified. No canned model response or invented weather is substituted.

LifeLine primarily addresses planning relevant to SDG 7, with a potential supporting role for SDG 3. It does not control equipment, guarantee electricity, establish safe clinical operation or demonstrate patient outcomes. Its next validation step is practitioner review and comparison with permitted facility measurements across adverse conditions.

See [DEMO](DEMO.md), [architecture](ARCHITECTURE.md), [weather integration](LIVE_WEATHER.md) and [validation gaps](VALIDATION_GAPS.md). Hosting/video requirements and submission confirmation remain to be verified with organizers.
