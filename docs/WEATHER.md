# Weather and data sources

LifeLine associates every calculation with its weather source, location, planning date and timezone. Forecast outputs also include requested and model-grid coordinates, retrieval time and cache status. A saved forecast retains its original timestamp.

## Available inputs

| Source | What it represents |
|---|---|
| Live Open-Meteo | Numerical weather-model forecasts for today and tomorrow in the clinic's timezone. Select a location or supply coordinates. This estimates incident radiation and PV production. |
| NASA POWER historical day | Bundled satellite-derived irradiance for a representative point in Kisumu, Kenya, on January 14, 2025. No network request is needed at runtime. |
| Synthetic presets | Declared example inputs, including normal, storm, high demand and scheduling cases. |
| Explicit demo weather | `LIFELINE_WEATHER_MODE=demo` serves a synthetic sample with 800 W/m² peak irradiance, a 06:00–18:00 daylight curve, and illustrative temperatures. Its assumed timezone is Africa/Nairobi and its dates advance with the demo calendar. |

Open-Meteo weather can be unavailable. The application surfaces that failure. Historical and synthetic modes are explicit alternatives. The separate **current and seven-day outlook** reports weather-model conditions, temperatures and precipitation probabilities. Only a supported 24-hour planning day receives an electrical simulation.

Equipment and operating requirements are illustrative or entered and reviewed by the operator. The published ratings extracted in [equipment reference data](../data/published_equipment_ratings.json) come from the SEforALL/CLASP report, page 13. They give equipment examples, without a measured whole-clinic load profile. [Medical Appliances for Resource-Constrained Settings](https://www.seforall.org/system/files/2025-07/SEforALL%20report-medical-appliances-resource-constrained-settings.pdf)

## Forecast conversion and uncertainty

- Open-Meteo shortwave radiation is a **preceding-hour mean in W/m²**. The sample ending at 01:00 covers the preceding hour. The adapter integrates overlaps for local intervals in the provider's IANA timezone, including fractional offsets. Days with 23 or 25 hours return `UNSUPPORTED_FORECAST_DAY` for the 24-hour engine.
- A one-hour mean converts to kWh/m² by multiplying by one hour and dividing by 1,000. Modeled PV energy is rated kW times irradiation divided by the 1 kW/m² reference, multiplied by the performance ratio, normally 0.80. The model approximates array-plane irradiance using the horizontal profile. Tilt, shading, temperature and inverter clipping are outside this approximation.
- Zero astronomical terrestrial radiation identifies forecast nighttime intervals. The sample daylight curve applies only in demo mode. Missing or invalid provider radiation and unexpected units fail validation.
- Live radiation already includes modeled clouds. The forecast replaces preset cloud factors. Lower-sunshine factors, such as 0.75 and 0.50, are each applied once to create separate sensitivity runs. Each case can reoptimize, so these are modeled alternatives without a probability estimate or a fixed-schedule performance guarantee.
- The selected day starts at an explicitly reviewed local-midnight stored-energy assumption. A timestamped current reading does not predict tomorrow's battery charge.
- The hourly forecast cache is process-local and bounded to 64 locations, with a 15-minute freshness period and a bounded retry for transient failures. A refresh failure can use validated data up to one hour old if it still covers both dates, with a stale label and original retrieval time. The independent outlook cache has a ten-minute freshness period and its own bounded stale handling.

### Attribution

Weather data by [Open-Meteo](https://open-meteo.com/) under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). LifeLine aligns forecast intervals and converts irradiance to estimated PV energy. [Forecast API documentation](https://open-meteo.com/en/docs)

Historical data were obtained from NASA Langley Research Center's POWER Project, funded through NASA Earth Science. The [original hourly UTC API response](../data/nasa_power_raw.json) records `ALLSKY_SFC_SW_DWN` in Wh/m². The [processed sample](../data/kisumu_weather.json) converts the 24 values for the Africa/Nairobi civil day into kWh/m². The daily total is 6.91772 kWh/m². Reproduce the extraction with `python scripts/prepare_weather.py`. [NASA POWER attribution guidance](https://power.larc.nasa.gov/docs/referencing/)

## Verify and troubleshoot

With the server running in `live` mode, run these commands from the repository root. Change `--api-url` to match your server's port. Both commands use the network.

```bash
.venv/bin/python scripts/check_live_forecast.py \
  --api-url http://127.0.0.1:8000 --midnight-battery-kwh 6
.venv/bin/python scripts/diagnose_weather.py --output /tmp/lifeline-weather-diagnostic.json
```

On Windows, run the same scripts with `.\.venv\Scripts\python.exe` and a writable output path.

On November 13, the Mac resolved DNS and opened TCP, but the TLS handshake stalled. The ordinary hostname later recovered without DNS, operating-system or application changes, and the full live forecast-to-model check succeeded. The earlier Windows success was observed under different conditions, and the root cause remains undetermined. Compare DNS, TCP, TLS, HTTP and validated weather from both machines at the same time if the issue recurs. The app uses normal certificate verification. The [initial failure notes](evidence/mac-weather-initial-failures.json), [network diagnostic](evidence/mac-weather-network.json), [live recovery run](evidence/mac-weather-live-recovery.json) and [later unavailable run](evidence/final-weather-network-unavailable.json) preserve each result separately.

A [dated live browser run](evidence/live-forecast-run.json) exercised real weather retrieval and the simulator. A separate [live outlook probe](evidence/current-week-weather-live.json) returned seven daily rows. These checks verify the integration. Establishing forecast accuracy or sustained availability requires further measurement.
