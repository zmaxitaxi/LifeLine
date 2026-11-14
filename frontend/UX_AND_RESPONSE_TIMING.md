# Clinic Overview and response feedback

This frontend change consumes Main Chat's authoritative planning, recovery, stream, failure and timing contracts. It changes no agent decisions, pricing data, simulator or optimizer.

## What users see

- The current clinic's computed energy outlook comes first: planning day, weather provenance, essential equipment needs and battery reserve risk. Empty essential requirements are explicitly incomplete, never a safe zero-demand clinic.
- A relevant proposed comparison follows, with no more than three specific next actions. A current plan that already meets every modeled requirement is identified as needing no change under those assumptions. Other calculated plans remain accessible, with benefits, unresolved constraints and exactly postponed device work.
- Hourly solar availability and equipment energy actually supplied appear in a wide chart. Missing supply is separately hatched. The adjacent battery uses its own scenario capacity and actual backend stored-energy boundaries. The chart picker, battery slider and playback stay synchronized at integer hours.
- Numbered markers refer only to confirmed activity start times. They do not assign invented energy to an activity or count shared equipment twice. Required essential equipment is labeled as requested, not proof it received power.
- Editable equipment, activities, weather and technical settings remain below the decision and evidence. Proposed input changes still require explicit confirmation. Choosing an already computed comparison does not physically adopt it or recalculate.
- Clinic setup no longer asks for a date. It starts with tomorrow in the selected clinic timezone and shows that assumption for review. The backend must clarify requests for a different date, rather than silently changing the planning day.
- Unknown prices remain explicitly unestimated. The backend supplies the cost status and explanation; the UI does not fabricate currencies, supplier rates or purchases.

## Response transport and measurements

The Assistant makes one POST to `/api/planning/sessions/{id}/agent/stream`. It displays only published public phase events: request accepted, model response preparation, weather, simulation, serialization and persistence. It renders the final reply and associated results only from the backend's validated `result` event. It never exposes private reasoning or unverified raw model tokens.

An interrupted stream is never silently replayed: a tool may already have saved changes. The existing session hook reloads authoritative state. Stale requests preserve conflict handling. Structured date failures preserve their dates and nonretryable action across reloads; timeout, provider availability and weather failures have separate public explanations. The provider/model label comes from status, not an assumed local model name.

Backend `response.timings` reports server stages and inference timing. These are distinct from browser visibility. The frontend also keeps bounded, last-request-only Performance entries:

- `lifeline.first_progress_commit`: milliseconds from dispatch to the first public-progress DOM commit.
- `lifeline.answer_commit`: dispatch to a successful verified reply's DOM commit.
- `lifeline.error_commit`: dispatch to a failed response notice's DOM commit.

These are DOM commit proxies, not GPU timings, first model token timings or measured pixel-paint times. Progress is not a completed answer. Entries contain no question text. Read them with `performance.getEntriesByType('measure')` in an actual browser benchmark. Browser fixture delays are test data and must never be reported as genuine model performance.

## Verification

The browser suite covers navigation and chat persistence, explicit activity/equipment/energy confirmation, critical-load protection, hourly chart and battery values, distinct missing demand, scenario capacity differences, no stale result after failure, persisted date guidance, interrupted-stream non-replay, public progress before a final reply, and keyboard/mobile behavior.

Run `npm --prefix frontend run build` and `npm --prefix frontend run test:e2e`. Tests use isolated model/weather transports with the actual review APIs, compiler, simulator, optimizer and result validators. Main Chat owns the separate real Llama before/after benchmark and final backend regression report; no real-model speed improvement is inferred from frontend fixtures.

The current demonstration uses Claude Haiku only. Its actual API/browser timing
evidence is in [Haiku validation](../docs/HAIKU_VALIDATION.md); the older Llama
benchmark remains historical. The first release CI passed both Python jobs and
55 browser tests, but failed saving one screenshot to a Mac-only `/private/tmp`
path. Evidence now uses Playwright's per-test `outputPath`, verified in all ten
affected Overview journeys. This changes test artifact storage, not the app.
