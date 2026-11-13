# Product validation status

**Status: functioning planning prototype with desk-research support and computational verification; no field/user validation.**

| Question | Current answer |
|---|---|
| Intended user | Energy technicians, facility managers, and organizations planning/supporting solar-powered healthcare facilities |
| User problem | Determine whether configured essential requirements can be supplied, whether optional work can move, and which resource constraints remain |
| Supporting evidence | [RESEARCH.md](RESEARCH.md) documents authoritative evidence of unreliable electricity, equipment/infrastructure mismatch, and maintenance/service-delivery gaps |
| Proposed value | Editable equipment → reliability assessment → actual operating timelines → fair baseline/heuristic/MILP comparison → infrastructure what-if exploration |
| Proposed differentiation | A narrow, explainable, locally runnable clinic-equipment workflow with explicit provenance and an honest simple-rule comparator |
| Established novelty? | None claimed. HOMER, REopt, and hardware monitoring platforms already address substantial portions of energy planning/monitoring |
| Verified outcome | Model/HTTP/browser tests and [computed benchmarks](BENCHMARK.md); these do not establish health outcomes, operator adoption, or real electricity savings |
| Unvalidated assumptions | Useful optional-load flexibility; operator access to accurate inputs; schedule adherence; acceptable language/device/workflow; demand for this tool rather than existing products |
| Deployment barriers | Accurate facility data, staffing/clinical constraints, electrical/biomedical review, actual battery condition, power quality, uncertainty, maintained hardware, training, and accountable service provision |

LifeLine addresses SDG 7.1 and supports investigation relevant to SDG 3.8. It does not measure progress toward either target. Reliable energy provision requires more than a software intervention; no schedule repairs broken equipment or replaces maintenance arrangements.

Next validation: recruit appropriate practitioners with permission; observe present assessment/maintenance workflow; test equipment-entry accuracy; check whether optional tasks are actually movable; compare forecasts with logged operation across cloudy periods; measure task completion and reserve without changing critical requirements; evaluate usability against existing alternatives. Set success criteria before a pilot and record negative findings. No interviews, pilots, deployment partnerships, patient benefits, or endorsements are claimed.

If practitioners show insufficient flexible demand, preserve reliability/capacity assessment and simplify the scheduling emphasis. If inputs are unavailable or uncertainty dominates, prioritize better measurement and engineering review before more elaborate optimization. Do not add LLMs or hardware controls to compensate for missing evidence.
