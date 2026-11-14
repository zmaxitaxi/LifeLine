# Final objective checklist

This is a decision-support prototype, not clinical deployment or a power guarantee.
The final architecture retains the existing physical simulator, MILP, baseline and
sunshine-first comparator. The current model is **Claude Haiku (`claude-haiku-5-5`)** through the Anthropic API. A server-side Anthropic key and internet are required for the assistant. No Llama fallback is used; numerical planning and manual review remain independent.

## Product behavior

| Objective | Implemented behavior and practical boundary |
|---|---|
| Configure a clinic | Location/date and illustrative quick-start inputs; reviewed solar, storage, midnight starting energy, reserve, efficiencies and charge/output limits. A timestamped current reading is separate. Capacity changes preserve absolute stored energy unless explicitly edited. |
| Plan clinic work | Add/edit partial activity proposals in chat or manually. Existing activities remain active until reviewed changes are confirmed. Existing devices are referenced once. Explicit flexible daily runtime is converted to energy in Python; event duration alone adds no demand. |
| Claude assistant | Haiku authors conversation and chooses state-valid native tools. Plain conversation and unevaluated ideas do not require calculations. Computed claims use actual model facts; explicit confirmation remains an operator action. The primary chat never silently replaces a failed model with a canned energy answer. |
| Actual weather | Open-Meteo hourly irradiation for supported today/tomorrow calculations, provenance/timezone/retrieval metadata, cache and explicit failures. Independent current/seven-day weather is not a seven-day energy prediction. Historical NASA and synthetic numerical modes remain explicit offline alternatives. |
| Actionable scheduling | Before/after operating schedules, original work completion, battery timeline, losses, essential deficits and reduced-sunshine tests. Fixed, sunshine-first and MILP comparisons use identical inputs. |
| Recovery options | Bounded individual scheduling/solar/storage/output sensitivities, absolute initial energy held fixed, explicit remaining hourly deficits and unchanged protected demand. Smallest tested candidate is not global sizing, a cost optimum, a purchase instruction or installed hardware. |
| Clear interface | AI Assistant and decision-first Clinic Overview, an hourly energy chart beside the battery, and expandable details, reviewed activity/settings forms, exact-selected-plan explanations, and relevant calculated evidence rather than every option on every message. |
| Durable local work | Private atomic snapshots preserve sessions, drafts, confirmed inputs, receipts and recent chat. Interrupted calculations cannot restore as current. Failed saves roll back and return an explicit error. One process only; no accounts or distributed storage. |
| Safe rollout | An explicit offline migration preserves a legacy preview's actual state and transcript, marks imported messages, and does not invent past timestamps/current readings. Original exports remain intact. |

Clinic identity/location/date and base inventory still require a deliberate new
session; energy settings and activity requirements can be edited in-session.
There is no implicit migration of activities between clinics or dates.

## Verification record

- Final assembled backend: **525 tests passed**, including settings, restart
  recovery, source/unit validation, shared-device runtime, migration and all
  existing numerical/API checks.
- Final assembled frontend: **56/56 browser journeys**, TypeScript and production
  build pass against the real Python compiler, simulator and MILP, with injected
  test-only weather/model transport. Desktop, narrow preview and phone layouts
  are covered, including blank setup, explicit demo autofill and saved-clinic resume.
  This is separate from genuine model/weather evidence.
- Actual Claude Haiku passed the greeting, clinic assessment, date clarification,
  valid vaccination proposal, recovery comparison, selected explanation and
  history journeys in targeted runs. The last seven-case batch was **6/7**;
  recovery passed after a documented source-validation correction. A genuine
  browser check passed Hello (2.272s) and assessment (6.685s), with no adopted
  changes or page errors. [Measured evidence and limitations](docs/HAIKU_VALIDATION.md).
- The teammates' [comprehensive evaluation](LLM_EVALUATION.md) records
  **87.5/100** on the previous tool set. New targeted checks do not inherit that
  score and do not establish arbitrary-language or clinical reliability.
- Real native tool/weather runs have original timestamps in
  [recovery evidence](docs/evidence/recovery-agent-live-smoke.json),
  [activity evidence](docs/evidence/activity-agent-real-model.json), and
  [conversation evidence](docs/evidence/conversation-agent-real-model.json).
  Each is a targeted integration smoke, not a broad new evaluation.
- Earlier remote CI passed on `c98d6a7`:
  [Python 3.11/3.12 and frontend checks](https://github.com/zmaxitaxi/LifeLine/actions/runs/43522478094).
  That result is retained as dated history.

The [two-minute guide](DEMO_2_MINUTES.md) includes exact genuine-Haiku prompts and a fresh-clinic preflight. Extended rehearsal verifies vaccination confirmation/revision/rejection, actual equipment slots, recovery comparisons, reviewed solar changes, reload and backend restart without changing the presentation clinic.

## Demonstrated value

The [historical recovery example](docs/evidence/recovery-historical-demo.json)
reduces essential deficit from **1.320 to 0 kWh** with a hypothetical output
limit change from **4 to 5 kW**, completing all **2.100 kWh** flexible work with
the same weather, equipment and initial stored energy. Extra storage alone does
not solve the output bottleneck. It is an illustrative modeled sensitivity.

The original equal-work scheduling scenario preserves **2.211 kWh** more battery
energy at midnight and improves the daily minimum by **0.368 kWh**. The
sunshine-first heuristic ties MILP. The competing-window benchmark shows
**3.8 / 3.470 / 2.770 kWh** completed by MILP / sunshine-first / fixed scheduling;
a different greedy ordering closes that gap. See [inputs and caveats](STRONGEST_DEMO.md).
Runtime endpoints calculate fresh results rather than reading evidence fixtures.

The current labeled sample-weather demo completes all **2.1 kWh** flexible work
and all **5.34 kWh** essential demand. Final stored energy is **4.585 kWh fixed**,
**5.682 kWh sunshine-first**, and **5.700 kWh MILP**. MILP gains **1.115 kWh** over
fixed scheduling and improves the minimum by **0.368 kWh**; the heuristic is
nearly as good. [Computed proof](docs/evidence/demo-weather-scheduling-proof.json).

## Remaining external work

1. Check Anthropic API access and the selected weather mode on the presentation machine/network;
   rehearse the [current demo](DEMO.md) on the final build. Clearly identify any
   historical, recorded or synthetic fallback.
2. Confirm official registration, eligibility, deadline/timezone, submission URL,
   video/hosting requirements, team credits and AI/data attribution. The
   user-supplied deadline is November 14, 2026, 11:59 PM Pacific; event-specific
   rules were not independently established by the provided slide.
3. Record/submit the required presentation and retain the official confirmation.
   These engineering changes do not submit the project. Select a repository
   license if the event requires it; no license is inferred for the user.
4. Obtain practitioner review and permitted measured equipment/solar/battery
   data before any operational pilot or real savings/health-impact claim.
   [Validation gaps](VALIDATION_GAPS.md) and [operations](OPERATIONS.md) remain explicit.
