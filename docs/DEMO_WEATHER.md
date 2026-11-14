# Explicit demo weather

The user authorized sample weather to make the local Llama demonstration usable
while the Mac's Open-Meteo route is unavailable. Start with
`LIFELINE_WEATHER_MODE=demo`; omit it or use `live` for real Open-Meteo access.
This is an explicit launch mode, never an automatic hidden fallback.

`DemoWeatherService` supplies a declared synthetic day: hourly mean irradiance
follows an 800 W/m² peak sine profile from 06:00 to 18:00 in the assumed
Africa/Nairobi demo timezone, with exactly zero nighttime generation. It is not
a location-specific prediction. Sample temperature rows are 20–28°C with a
24°C current illustration and clear conditions. All are filler inputs, not
observations or an external weather forecast. Dates follow the current demo
calendar so today/tomorrow workflows remain usable.

The existing PV conversion, simulator, baseline, sunshine-first heuristic, MILP
and recovery comparisons calculate every result from that profile. Reduced
sunshine still creates separately computed sensitivity cases. Llama authors
replies and chooses tools; it does not invent weather or energy calculations.

`SolarForecast`, `WeatherOutlook` and each `ComputedPlan` carry
`weather_mode:demo`; source and data_kind identify synthetic demo weather.
Simulation provenance also identifies the sample inputs. Old live results keep
their original live provenance. `GET /api/weather/mode` reports the configured
server mode for the banner. Switch modes by restarting the same single-process
backend with the desired environment setting; saved sessions remain intact.
