# Data sources, units, and provenance

Live forecasting is an additional, separate source: the [Open-Meteo Forecast API](https://open-meteo.com/en/docs) supplies numerical weather-model forecasts, not observations or measured clinic generation. Source, requested/model-grid coordinates, local dates, IANA timezone, retrieval time and cache status are returned and displayed. Preceding-hour mean radiation in W/m² is interval-aligned and converted using the existing PV assumptions. See [LIVE_WEATHER.md](LIVE_WEATHER.md) for precise conversion, DST limitations, cache/failure behavior, [CC BY 4.0 attribution](https://open-meteo.com/en/licence), and a dated real validation run. Synthetic and historical sources below remain distinct.

The application distinguishes synthetic examples, unverified user inputs, published equipment ratings, and historical satellite-derived irradiance. None is a measured whole-clinic electricity profile.

## NASA POWER historical irradiance — incorporated

- Representative point: Kisumu, Kenya, latitude −0.0917°, longitude 34.768°. This is not an identified clinic.
- Local day: January 14, 2025, Africa/Nairobi (EAT, UTC+3).
- [Original API request](https://power.larc.nasa.gov/api/temporal/hourly/point?parameters=ALLSKY_SFC_SW_DWN&community=RE&longitude=34.768&latitude=-0.0917&start=20250113&end=20250114&format=JSON&time-standard=UTC).
- Parameter: `ALLSKY_SFC_SW_DWN`; source response units **Wh/m²**, hourly. API v2.10.4; response source `SYN1DEG`.
- Original response retained in [data/nasa_power_raw.json](data/nasa_power_raw.json). Processed local day and SHA-256 are in [data/kisumu_weather.json](data/kisumu_weather.json).
- Processing: select 24 UTC values corresponding to local 00:00–23:00, including 21:00–23:00 UTC on the previous date; divide Wh/m² by 1,000. Total local-day irradiation is **6.91772 kWh/m²**. Validate all values as finite/nonnegative and no greater than 2 kWh/m² per hour; reject missing/fill values, including −999.
- Conversion: modeled PV energy = nameplate kW × 0.80 performance ratio × hourly irradiation / reference 1 kW/m² × user scenario factor. This is a horizontal-irradiance approximation, not a calibrated tilted-array yield model.
- Native satellite grid-cell averages are not on-site pyranometer readings. NASA describes solar data as inferred from satellite observations using radiative-transfer models. No site-specific accuracy claim is made. [NASA data FAQ](https://power.larc.nasa.gov/docs/faqs/data/)
- Time convention: NASA offers UTC and local solar time, which differ from civil time. The request explicitly uses UTC; we convert to Kenya civil time. [Hourly documentation](https://power.larc.nasa.gov/docs/services/api/temporal/hourly/)

The sample is bundled and selectable in the UI; runtime execution does not contact NASA. Sunshine multipliers create hypothetical adverse conditions and are not additional measured weather. Selecting a different dataset resets weather multipliers but preserves clinic equipment and infrastructure. The synthetic curve remains available offline as a transparent alternative.

Attribution: data obtained from NASA Langley Research Center's POWER project, funded through NASA Earth Science; POWER Hourly service v2.10.4, accessed November 12, 2026 Pacific. The API response does not contain an explicit SPDX license. Preserve source metadata/attribution; consult NASA's [referencing and redistribution guidance](https://power.larc.nasa.gov/docs/referencing/), which requests publication/redistribution notification. No notification or endorsement is claimed, and no email was sent automatically. Do not describe this as an independently licensed proprietary dataset.

## Equipment demand

The demo equipment powers/schedules in [contracts/scenarios.json](contracts/scenarios.json) remain **synthetic, illustrative values**. User equipment is labeled `user_entered_unverified`; entry into the app does not validate its accuracy or clinical suitability. Power × required duration defines flexible energy; selected critical hours define fixed critical demand.

Published reference ratings were extracted from SEforALL/CLASP's [2025 report, p.13](https://www.seforall.org/system/files/2025-07/SEforALL%20report-medical-appliances-resource-constrained-settings.pdf). The small factual extraction is in [data/published_equipment_ratings.json](data/published_equipment_ratings.json). It records W→kW conversion and source page. It does not supply measured hourly demand or clinical schedules. Copyright remains with the publication's rights holders; the report is linked, not republished or treated as an openly licensed raw monitoring dataset.

No downloadable, machine-readable whole-clinic hourly demand dataset was obtained from the reviewed report. Its published charts and selected appliance monitoring do not justify fabricating a clinic load trace. Therefore demand remains a transparent synthetic/user-configured profile. Clinical equipment duration, priority, and flexibility must be supplied and reviewed by the operator. No published rating is silently installed as a medical scheduling recommendation.

## Battery and solar system assumptions

Capacity, initial stored energy, reserve, power limits, and efficiencies are editable engineering assumptions. Defaults (95% charge/discharge efficiency, 4 kW external charge/discharge limits, 0.80 PV performance ratio) are **not** a tested manufacturer's specification. No battery chemistry, vendor certification, or actual usable capacity is inferred. Rates are kW on the common modeled bus; states and hourly flows are kWh. The horizon has 24 one-hour slots and 25 stored-energy boundaries.

Voltage quality, inrush, refrigeration temperature, state-of-health, degradation, outages beyond the modeled horizon, uncertainty, and thermal/contiguous appliance cycles are omitted. The UI explicitly describes flexible loads as divisible/interruptible approximations. Modeled reserve does not establish clinical safety or real-world availability.

## Validation and reproducibility

Backend tests independently check accounting, unit conversions, the NASA local-day extraction, invalid custom inputs, same-input comparisons, and shortage/capacity cases. Browser tests exercise historical selection with external requests blocked. Use `python scripts/benchmark.py` to recalculate all reported benchmark metrics; there is no hardcoded result path.
