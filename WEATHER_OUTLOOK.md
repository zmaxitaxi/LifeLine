# Current weather and seven-day outlook

`GET /api/weather/outlook?latitude=-0.0917&longitude=34.768` returns the strict `WeatherOutlook` contract in [contracts/weather.ts](contracts/weather.ts) and [OpenAPI](contracts/openapi.json). The frontend owns the compact current/day cards and uses these returned values. It must not derive a week of weather from the solar curve, or substitute zeros for missing fields.

The adapter requests actual Open-Meteo current temperature, WMO condition code and day/night flag, plus seven daily condition codes, minimum/maximum Celsius temperatures and maximum precipitation probability. Open-Meteo describes current conditions as weather-model output, rather than station observations. Its daily boundaries use the UTC offset resolved at retrieval, including across DST; the adapter preserves those provider calendar labels and records that period basis. [Official parameter and time conventions](https://open-meteo.com/en/docs).

The current sample has its actual UTC `valid_at`. `retrieved_at` records the separate retrieval instant; source, requested/grid coordinates, IANA timezone, fixed provider offset and attribution are retained. Nullable provider values remain null with a concise warning. Invalid units, codes, nonfinite values, duplicate/missing dates, impossible temperature ranges and wrong day boundaries are rejected.

`WeatherOutlookService` has a bounded 64-location cache, a ten-minute freshness period, one bounded retry for transient network/server errors, and a labeled stale cache of at most one hour. A local-day rollover forces refresh. It never silently manufactures weather or shifts yesterday's seven-day outlook forward. Failure uses the existing structured error envelope; the UI should show a short unavailable/retry state, not provider exceptions. Source/time metadata can remain in an expandable detail.

This service is independent of `ForecastService`: the original preceding-hour solar-radiation adapter, today/tomorrow conversion, simulator, optimizer and sensitivity inputs remain unchanged. Temperature, daily weather codes and rainfall probabilities do not drive photovoltaic calculations. The seven-day outlook is not a seven-day battery-reliability simulation.

Tests inject the HTTP transport and clock. Production uses the fixed Open-Meteo host with certificate verification; no key, proxy override or DNS/IP workaround is introduced. `create_app(..., outlook_service=...)` supports an independently injected service for frontend integration tests. Fixture weather must remain clearly labeled test data.

A live probe on November 13 retrieved current conditions and all seven daily rows successfully; [dated output](docs/evidence/current-week-weather-live.json) records the actual values. This verifies the integration, not weather accuracy at a clinic.
