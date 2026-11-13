# Two-minute demonstration

Start backend and frontend using [README.md](README.md). Keep local dependencies and datasets installed so internet access is unnecessary. Use the real API; the exported JSON example is not a runtime fallback.

| Time | Action | Explain |
|---|---|---|
| 0–15 s | Show LifeLine and the clinic inputs | A technician needs to assess whether essential equipment can be supported by an existing solar/battery system. All demo demand is illustrative. |
| 15–40 s | Use Scheduling improvement; point to the battery hero and Before → After equipment rows | The same 2.1 kWh of flexible work is completed. Stored energy at midnight changes from 4.618 to 6.828 kWh: approximately 2.211 kWh more. The daytime equipment hours explain the result. This is different from the 0.368 kWh full-day minimum improvement. |
| 40–55 s | Expand Detailed analysis; show the sunshine-first timeline, battery forecast, and comparison table | The simple rule matches the MILP's key outcomes here. The tie is also acknowledged in the primary result. |
| 55–75 s | Add equipment, change watts/duration/window, or select historical Kisumu weather | New valid inputs recalculate; the app is not a three-scenario animation. NASA input is historical satellite-derived irradiance, not a clinic reading or current forecast. |
| 75–90 s | Select High Demand | Essential demand remains unserved at 20:00–22:00 despite stored energy. The 4 kW output limit cannot meet 4.66 kW demand. |
| 90–110 s | In Capacity Explorer raise proposed battery to 40 kWh, then proposed output limit to 6 kW | More storage alone leaves 1.320 kWh unserved; the higher modeled output limit resolves that case. This is a comparison, not installation advice. |
| 110–120 s | Show assumptions and limits | Decision support only. No medical controls, guaranteed power, field-effectiveness claim, or certified system sizing. |

Use the live computed values if inputs differ. Storm demonstrates reserve risk and optional work deferral; do not describe its higher battery as completing the same work. A cloud test changes weather while preserving equipment and starting battery. Reset returns to the selected quick start; it does not reveal a hidden precomputed result.

On a phone, open **Configure clinic** to edit settings. Power limits and efficiencies have a separate collapsed disclosure. Detailed analysis is initially collapsed on all screen sizes; keyboard Enter/Space operates disclosures and hour selections.
