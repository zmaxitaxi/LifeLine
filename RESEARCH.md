# Research and implications

Reviewed November 12, 2026. This is desk research, not interviews or deployment validation. Numerical benchmarks are separate from evidence about real facilities.

## Established evidence

| Source | Evidence and scope | Product implication |
|---|---|---|
| [WHO, World Bank, IRENA and SEforALL: Energizing Health (2023)](https://www.who.int/publications/i/item/9789240066960/) | Addresses energy-demand characterization, electrification options, finance, and institutional responsibilities for low- and middle-income health systems. | Support technicians and electrification planners with explicit equipment requirements and energy accounting; avoid inferring health outcomes from electrical metrics. |
| [SEforALL/CLASP: Medical Appliances for Resource-Constrained Settings (2025)](https://www.seforall.org/publications/medical-appliances-for-resource-constrained-settings) | Surveys 29 Kisumu facilities; the report includes short on-site testing and selected 15-day monitoring. All sampled facilities were grid-connected; levels 1–2 were excluded. Equipment ratings and observed consumption differed. | Treat rated power as an uncertain input. These findings cannot be described as measurements of our fictional off-grid clinic. |
| [World Bank/ESMAP: Sustainable Energy for Schools and Health Centers](https://www.worldbank.org/en/topic/energy/publication/sustainable-energy-schools-health-centers-ppps) | Identifies missing operations/maintenance arrangements as a source of unreliable public-facility solar systems. Describes service-provider responsibility under performance-based energy-service contracts. | A software schedule cannot repair failed equipment, fund maintenance, or replace accountable service delivery. Include technicians/maintainers among intended users. |
| [UNDP: Solar for Health](https://www.undp.org/energy/solar-health) | Describes solar electrification, maintenance, technical training, and financing activities supporting health facilities. | Planning is one component of a wider implementation/maintenance partnership, not a stand-alone electrification intervention. |

The SEforALL/CLASP report describes reliance on diesel backup during grid interruptions, idle equipment, and constrained usage. It identifies autoclaves, oxygen concentrators, infant warmers, and refrigeration among relevant categories. Its p.13 rated-power examples include an 880 W J-10 concentrator, 700 W OKM 730 warmer, and 1,650 W All American X75 autoclave. These are published ratings, not our own tests or typical daily consumption. The report's findings support compatibility/capacity assessment; they do not establish that our scheduling workflow is wanted or routinely feasible. [Report, pp.7, 11–13, 19–24](https://www.seforall.org/system/files/2025-07/SEforALL%20report-medical-appliances-resource-constrained-settings.pdf)

## Existing alternatives

| Product/source | Existing capabilities | LifeLine's proposed focus |
|---|---|---|
| [HOMER Pro](https://homerenergy.com/homer-pro) | Microgrid simulation, system optimization, sensitivity analysis, advanced load/storage models | Small, explainable clinic-equipment workflow; no claim that scheduling or microgrid optimization is novel |
| [REopt](https://reopt.nlr.gov/tool/) | Distributed-resource sizing/dispatch, economic and resilience analysis | A narrower offline local demonstration with per-equipment timelines and transparent comparisons |
| [Victron VRM](https://www.victronenergy.com/media/pg/VRM_Portal_manual/en/dashboard.html) | Connected-system battery/solar monitoring, historical data and forecasts | Explore hypothetical configurations without connected hardware; no attempt to replace monitoring or controls |

These are documentation comparisons, not hands-on competitive evaluations. We have not established unique market positioning or superior performance.

## Assumptions and unresolved hypotheses

- **Engineering assumption:** discretionary work can be represented as divisible hourly energy. Real appliance cycles, clinical requirements, staffing, and workflow may prohibit this. Medical sterilization cycles are not validated by this model.
- **Hypothesis:** technicians/facility managers benefit from an equipment-level comparison before changing infrastructure. Needs direct validation.
- **Hypothesis:** enough optional demand has suitable windows for shifting to matter. The primary demonstration proves a modeled possibility, not its prevalence.
- **Known limitation:** one historical weather day is not a reliability probability, seasonal assessment, or worst-case design basis.
- **Unknown:** whether equipment inventories, measured load curves, or accurate battery condition are available to the intended operator.

## Decisions made from the evidence

Keep editable inputs, shortage diagnosis, and Capacity Explorer alongside scheduling. Distinguish energy quantity, storage timing, and output power. Include historical satellite-derived solar data while leaving demand explicitly illustrative/user-entered. Preserve fixed critical hours and defer assumptions to an operator. Do not add automatic device control or medical prioritization.

Next validation should involve a facility energy technician and a facility manager: observe how they inventory loads, record a real load profile with permission, check task windows and clinical constraints, and compare predictions with measured operation. No such interviews, measurements, partnerships, or endorsements have occurred in this project.
