# Model and data audit

Audit scope: implemented numerical constraints and integration behavior. This is not calibration against a real clinic, clinical validation or a reliability certificate.

| Check | Verified mechanism / evidence | Limit |
|---|---|---|
| Energy conservation | Independent hourly bus and battery-state balance checks, plus daily accounting; regression assertions at tolerance 1e-6 kWh | One idealized energy bus; no reactive power or power-quality model |
| Battery physical bounds | Stored energy constrained between zero and capacity; independent state validation before display cleanup | Capacity is operator/synthetic input; no aging, temperature or BMS model |
| Rates and losses | Charge input/discharge output caps, explicit charge/discharge efficiencies and binary mutually exclusive battery mode | Hourly average rates; starting surges and total inverter clipping are omitted |
| Protected demand | Essential load profile remains fixed. MILP first minimizes unserved essential energy, then protects achievable reserve, then optimizes flexible completion and storage/losses | Essential priorities originate with the operator; no medical prioritization |
| Flexible work | Required energy, per-slot maximum and permitted hours verified | Divisible, interruptible energy aggregates; not certified appliance cycles |
| Additional fixed appliance | User-supplied rated power, whole-hour duration, earliest start and deadline required. All consecutive starts are simulated against one forecast snapshot. Existing protected loads remain unchanged | Fixed consecutive hourly demand is not proof of sterilization/thermal effectiveness. Shortages explicitly invalidate completion; proposed start is not a clinical instruction |
| Fair comparison | Baseline, sunshine-first and MILP receive identical immutable inputs. Completion equality is reported separately | Battery benefits obtained with less work are never an equal-work claim |
| Infeasibility | Missing essential energy, shortage hours, reserve violations, deferred work and power constraints returned; solver failure is distinct from a physical shortage | No grid/generator dispatch or certified backup sizing. Essential unmet kWh is an electrical deficit, not a generator rating or fuel requirement |
| PV conversion | Shared rated kW × hourly irradiation / STC irradiance × performance ratio; forecast factors applied once | Horizontal irradiance, fixed performance ratio; no tilt, shade, temperature or clipping |
| Forecast units/time | Preceding-hour mean W/m² integrated to local slot energy; UTC timestamps and IANA timezone, fractional offsets and night astronomy tested. 23/25-hour days rejected by the fixed 24-slot simulator | No silent compression of DST days; unsupported days cannot be simulated |
| Missing weather/error/cache | Missing/nonfinite/invalid units rejected; timeout and bounded retry; 15-minute cache, clearly labeled stale data up to one hour, date rollover and typed errors tested | A transient Mac TLS failure and subsequent normal-route recovery were recorded separately. A replay is not a live runtime fallback or uptime guarantee |
| Uncertainty | Same-input, reduced-sunshine cases are independently reoptimized. Selected sensitivity case and schedule are labeled | Not calibrated probabilities, forecast-accuracy validation or robust feasibility of one fixed schedule |
| Capacity | Same weather, equipment, starting stored energy, reserve, efficiencies and output limits; bounded capacity search and infeasible resource cases tested | More empty capacity cannot add energy or power. Single-day numerical search is not system design |
| LLM boundary | Native local tool selection, strict schemas, read-only tools, rejected unknown calls, missing-input clarification, no raw numerical model prose displayed | Small real-model prompt sample; broader linguistic/adversarial evaluation remains open |

The simulator, optimizer and baseline/heuristic mathematics were retained. New work wraps them with agent tools, input-only demo cases, consecutive fixed-load what-if checks and verified result presentation.

The original same-work benchmark still ties sunshine-first. The new window/output-limited example has a real work-completion gap against the existing greedy order, but reversing that order removes it. This negative finding is retained in tests and evidence. See [strongest demonstrations](STRONGEST_DEMO.md).

Tests and exact run status are in [FINAL_CHECKLIST.md](FINAL_CHECKLIST.md). Physical-model checks do not establish forecast accuracy, measured clinic impact, user adoption, medical cycle validity, or guaranteed availability.
