# Live weather planning

LifeLine retrieves actual Open-Meteo weather-model forecasts for operator-selected coordinates. The weather profile feeds the existing physical simulator, sunshine-first heuristic and MILP. It is not measured clinic production, and an energy-feasibility result does not establish clinical safety.

## Run and demonstrate

Use the normal [application commands](README.md). Asking the primary forecast question in the main question box opens the live-weather workflow and requests the reviewed midnight assumption; computed answers return to the conversation. You can also open **Live weather forecast and tomorrow’s plan**, select a representative location or enter coordinates, and fetch today/tomorrow. Enter and confirm the assumed battery energy **at local midnight for the selected day**, then calculate a forecast-backed plan. Example locations are representative points, not partner clinics.

The primary question is: “Can our clinic safely operate tomorrow given the weather forecast?” The answer is computed from configured equipment, retrieved weather and the reviewed midnight assumption. Local **Llama 3.1 8B through Ollama** can now select validated tools through `/api/agent/ask`; it never supplies weather or energy calculations. The original `/api/planner/ask` remains a limited, explicitly non-LLM guided fallback. Unknown guided requests ask for clarification and do not alter equipment.

Forecast-backed results include the actual forecast, a 25%-lower and a 50%-lower sunlight case, Before → After allocations, all three schedule comparisons, battery charts, shortage diagnostics and assumptions. Each sunlight case is independently reoptimized; this is not a fixed-schedule robustness guarantee or a calibrated probability interval.

```bash
# Server must already be running. This command intentionally uses the network.
.venv/bin/python scripts/check_live_forecast.py \
  --midnight-battery-kwh 6 \
  --latitude -0.0917 --longitude 34.768
```

To save a new explicitly dated validation snapshot, add `--output /tmp/live-forecast-run.json`. Results and weather will change. No live snapshot is used as an application fallback.

## Weather and physics conventions

- Provider: [Open-Meteo Forecast API](https://open-meteo.com/en/docs), using `shortwave_radiation` and `terrestrial_radiation`, `timezone=auto`, `timeformat=unixtime`, `forecast_days=3`. Three days supply the endpoint needed for the last hour of tomorrow; the UI exposes today/tomorrow.
- Shortwave radiation is a **preceding-hour mean in W/m²**, not instantaneous radiation or kWh/m². The sample ending at 01:00 supplies the 00:00–01:00 simulation slot. Intervals are overlap-integrated, including fractional-hour time zones. Local dates and DST rules use the returned IANA zone, not browser time or a fixed UTC offset.
- For a one-hour slot, irradiation is mean W/m² × 1 h ÷ 1000 = kWh/m². Estimated PV energy is rated kW × irradiation (kWh/m²) ÷ the 1 kW/m² reference irradiance × the existing performance ratio (normally 0.8). Historical and live irradiance share this conversion helper.
- Horizontal irradiance approximates array-plane irradiance. Tilt, shading, temperature, snow/soiling variation and inverter clipping are omitted; no new PV physics are implied.
- Nighttime values are zeroed only where the provider's astronomical, preceding-hour terrestrial radiation is zero. The synthetic 06:00–18:00 curve is not imposed on real locations or seasons. Adjustments are disclosed.
- Provider radiation already includes weather/cloud effects. Preset cloud curves and `clinic.cloud_factors` are explicitly replaced in live mode; the named uncertainty multiplier is applied exactly once.
- The existing 24-slot simulator is retained. Local days with 23 or 25 hours are identified in forecast metadata and rejected for simulation with `UNSUPPORTED_FORECAST_DAY`; they are never silently squeezed into 24 slots.
- Today's profile includes elapsed hours. It is a whole-calendar-day counterfactual, not a remaining-day controller. Tomorrow starts at the operator's explicit midnight battery assumption; today's current battery is not silently carried forward or treated as a prediction.

## Caching, failures and provenance

The backend uses a bounded, 64-location process-local cache with a 15-minute freshness TTL and request coalescing. A failed refresh may use previously validated data up to one hour old **only with a stale warning and the original retrieval timestamp**. Entries that no longer cover both local dates cannot be used. Cache state is not persistent across restarts or shared between workers.

Transport failures and provider 5xx responses have one bounded retry after 0.2 seconds. Rate limits and invalid data are not retried automatically. Timeouts, rate limits, invalid/missing/nonfinite radiation, unexpected units and broken time sequences produce explicit errors. Missing radiation is never filled with invented weather. There is no silent switch to NASA or synthetic weather: those remain available as clearly chosen, labeled modes, without network access after installation.

The response/UI disclose requested coordinates, provider grid coordinates, local planning date, IANA timezone, UTC retrieval time, cache status, exact provider request, source and licence. Retrieval time is not a weather-model initialization timestamp; Open-Meteo's stitched forecast response does not supply a single model-run time here.

Data attribution: [Weather data by Open-Meteo.com](https://open-meteo.com/) under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). LifeLine aligns hourly intervals and transforms irradiance into estimated PV energy. The public endpoint is used for this noncommercial hackathon prototype; [provider service terms](https://open-meteo.com/en/terms) and quotas must be reviewed for subsequent deployment. No paid infrastructure or services were provisioned.

## HTTP and structured tools

Existing `/api/simulate`, scenarios, historical data and health behavior remain intact. New endpoints:

| Endpoint | Purpose |
|---|---|
| `GET /api/forecast/locations` | Representative coordinate presets |
| `GET /api/forecast?latitude=…&longitude=…` | Today/tomorrow radiation, timezone and provenance |
| `POST /api/forecast/plan` | Forecast + baseline/heuristic/MILP + sunlight sensitivity cases |
| `GET /api/planner/tools` | JSON Schemas for read-only configuration, forecast retrieval and planning tools; honest provider availability |
| `POST /api/planner/tool` | Execute a validated structured call using operator-bound clinic/location/midnight context |
| `POST /api/planner/ask` | Explicitly limited deterministic guided fallback, not an LLM |

```json
{
  "latitude": -0.0917,
  "longitude": 34.768,
  "clinic": {"scenario": "scheduling"},
  "midnight_battery_kwh": 6,
  "tool_call": {
    "name": "plan_forecast",
    "arguments": {"day": "tomorrow", "reduced_sunshine_factors": [0.75, 0.5]}
  }
}
```

Tools bind the clinic equipment, physical limits, location and starting-energy assumption outside model-generated arguments. The model-facing planning arguments can select the day and sensitivity factors; attempts to add or change equipment through tool arguments are rejected. Calls cannot access arbitrary URLs or operate devices.

Local-agent setup requires Ollama and the selected installed model, without an API key. The app uses a fixed localhost model endpoint and rejects cloud model records. All weather and numerical calculations remain backend-owned. Wajo was tested separately with a privately configured key; it is not used by the app. See [agent architecture](ARCHITECTURE.md) and [Wajo findings](WAJO_INVESTIGATION.md).

Current verification note: the earlier successful live retrieval is retained in `docs/evidence/live-forecast-run.json`. During the final November 13 checks, the API hostname could not be connected to from this machine, while the documentation site remained reachable. This does not establish a global outage. The app returned `FORECAST_UNAVAILABLE` and did not invent weather. See `docs/evidence/current-live-weather-check.json`; repeat the live check before presenting. Recorded-forecast replays are explicitly labeled verification artifacts, never automatic runtime fallbacks.

## Verification

Thirty-seven forecast-specific backend tests exercise mocked transports and clocks, independent energy accounting for every method and sensitivity case, preceding-hour alignment, date boundaries, fractional-hour zones, 23/25-hour days, missing data, units, astronomical night, cache coalescing/expiry/staleness, failure fallback, strict arguments and protected requirements. Tests require no provider network.

Four browser tests calculate fixture-backed plans through the actual Python API/model, cover uncertainty and impossible starting conditions, exercise explicit failure/validation messages and keyboard/mobile controls. `backend/tests/forecast_browser_fixture.py` exists solely for tests and is never imported by the production application.

An additional **real live browser/HTTP run** retrieved Kisumu weather on `2026-11-13T08:34:16.390183Z` for local November 14. With 1.5 kW PV and the explicitly assumed 6 kWh midnight charge, estimated solar was 7.1316 kWh, minimum optimized battery 4.8311579 kWh and flexible deferral zero. At 50% lower sunlight, estimated solar was 3.5658 kWh, minimum battery 4.03761 kWh and flexible deferral 2.1 kWh. Essential unmet demand was zero in these cases. This is one forecast snapshot with illustrative demand, not a general reliability finding. [Recorded inputs/source/metrics](docs/evidence/live-forecast-run.json).
