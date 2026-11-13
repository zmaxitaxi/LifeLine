# Intended use and practical deployment

Initial user: an NGO energy technician or solar-service technician working with a clinic facility manager. The technician verifies the system/inventory; the manager supplies service hours, staffing windows and deadlines. The prototype should not place an untrained staff member in charge of clinical prioritization or electrical installation.

## Inputs needed before a recommendation

| Input | Practical source | Review needed |
|---|---|---|
| Coordinates and local day | Facility map/GPS and location confirmation | Confirm the timezone/date returned by Open-Meteo |
| PV rating and topology | Installer documentation and panel/inverter labels | Nameplate rating is not measured production; current PV model omits tilt, shading and clipping |
| Usable battery capacity | Installer/BMS specification and service assessment | Nominal capacity can exceed usable/aged capacity |
| Midnight stored energy | Reviewed assumption or suitable measured telemetry | Current charge is not tomorrow's midnight prediction; this prototype does not carry today's state forward |
| Battery power/efficiency limits | Inverter/charge-controller/battery specifications | A larger battery does not automatically improve output power or arrive charged |
| Equipment ratings and operating pattern | Inventory, appliance label/manual and preferably logged consumption | Duty cycles, starting surges and power quality need review |
| Essential hours and reserve | Facility policy and responsible clinical/engineering staff | Never infer medical priority from an appliance name |
| Flexible windows and deadlines | Staff availability and service workflow | Confirm whether work can be interrupted; required stock/process constraints may prohibit shifting |

The live panel explicitly labels **synthetic example clinic** versus **operator-entered, unverified inventory**, and asks the operator to review inputs and midnight charge. Selecting a point on a map does not turn demonstration equipment into a measured clinic inventory. Unknown inputs should trigger clarification or remain an illustrative scenario. No patient information is required.

## Deployment pathway

1. **Prototype now:** one local workstation, manually reviewed inputs, optional local LLM, live forecasts when available, explicit historical/synthetic fallback. Browser state is temporary. No accounts, telemetry, controller, or public multi-tenant service.
2. **Pilot after practitioner agreement:** verify an inventory and task windows; log demand, generation and usable battery state with permission; evaluate predictions across cloudy periods and compare with a strong simple baseline. Predefine accepted error, reserve, task completion and usability criteria. Use shadow recommendations before any operational change. Arrange electrical, biomedical, clinical and data-governance review.
3. **Future if supported by evidence:** calibrated multi-day forecasts, measured telemetry, actual noninterruptible device models, offline assistance with dated data, staff training, maintenance ownership and supported deployment. Automatic control is a separate safety-critical undertaking.

No clinic interview, partnership, pilot, clinical validation, operating deployment or measured benefit is claimed. A public deployment would additionally require authentication, abuse/resource controls, secure persistence and an agreed data policy. The hackathon runs on localhost; source hosting is not application hosting.
