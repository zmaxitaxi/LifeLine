# Two-page frontend integration

This frontend branch was started from fetched `origin/main` at `ac3a45e` and then fast-forwarded onto Main Chat’s published backend dependency `d47b2b9`. The frontend commit changes only `frontend/`; it does not implement or modify the agent, simulator, optimizer, backend routes, or shared API definitions. The original checkout and its uncommitted work remain untouched.

## Integrating

Apply the frontend commit supplied in the handoff after Main Chat’s backend dependency `d47b2b9` (or a descendant containing it). The required authoritative interfaces are `contracts/planning.ts`, `contracts/recovery.ts`, and `docs/ACTIVITY_PLANNING.md`. Do not replace these with the earlier uncommitted recovery prototype’s contract.

Run from the combined repository:

```sh
npm --prefix frontend ci
npm --prefix frontend run build
.venv/bin/python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8020
```

Open `http://127.0.0.1:8020/`. For development, run the backend and `LIFELINE_API_PORT=8020 npm --prefix frontend run dev` separately. An installed Ollama `llama3.1:8b` model supplies local conversation. The UI can create/review activities manually and request deterministic numerical calculations when the local model is unavailable; it does not invent an activity extraction.

## State and review boundary

- Exactly two primary destinations: **AI Assistant** (default) and **Clinic Overview**. The overview’s four sections are local destinations, not additional primary pages. Calculate plan is a chat suggestion, with no extra empty-plan status/action row. Forecast source/update details live in the overview’s Weather section; the shared header keeps only the concise outlook. Hash navigation preserves the mounted conversation and unsent composer text; Explore plan opens the Solutions section.
- `usePlanningSession` caches only server responses. Local storage keeps one opaque session ID, never a competing activity, equipment, configuration, or plan record. The server owns conversational context and receives only `expected_revision` and the current question.
- Activity edits are transient form buffers. **Save draft for review** PATCHes an unconfirmed server proposal. **Confirm** uses the explicit endpoint and a stable idempotency key; only that response can establish a confirmed activity and a new plan. Cancel calls the rejection endpoint.
- Editing a confirmed activity first creates a proposal with `target_activity_id`; it preserves the original until confirmation. Associations alone do not add energy demand. Extra electrical-hour requirements and new device specifications must be explicitly supplied; existing device ratings and protected requirements are not silently replaced.
- Both pages use the same `PlanningState`. HTTP 409 reloads the server snapshot and asks for another review instead of replaying a mutation. Failed/ambiguous recalculations hide the previous result until verification. A result renders only when `plan_status=current` and `computed_plan.input_revision` matches `input_revision`.
- Selecting a recovery comparison uses the server’s revision/input revision/generation check. It does not apply hardware. All task recommendations, battery states and capacities come from the actual selected/recommended scenario; the original workload remains the comparison denominator.
- Battery playback is only in Clinic Overview. Values are actual integer hourly boundaries, with separate per-scenario capacity, stored kWh, reserve, and unmet-demand notices. CSS eases fill transitions only; no sub-hour values are manufactured. Reduced-motion users receive no fill transitions.
- Session APIs report successful tool names after completion. The UI shows generic request activity while waiting and the actual reported names afterwards. It does not manufacture incremental backend stages or private model reasoning.

## Limits to retain

Sessions are process-memory state. A server restart invalidates the stored ID; the UI requires an explicit new-session action and explains that previous activities were not copied. Base clinic/location/date/energy inputs are immutable within a session in this backend scope. Initial bootstrap clearly uses the configured Kisumu example and its starting-energy assumption, not a measured battery reading. Inventory ratings are read-only; new-device proposal specifications can be edited manually. Clinic base edits or another planning date require a deliberately created new session through the existing API. No persistent accounts, hardware deployment, medical-cycle validation, or clinical availability guarantee is implied.

## Verification

```sh
npm --prefix frontend run typecheck
npm --prefix frontend run build
npm --prefix frontend run test:e2e
.venv/bin/python -m pytest backend/tests -q
```

Playwright starts isolated ports **8012** (backend test harness) and **5182** (Vite); override with `LIFELINE_API_PORT` and `LIFELINE_UI_PORT`. It does not reuse a production server. Browser artifacts and weather-outage flag files are written to the OS temporary directory. The harness is under `frontend/e2e/support`; it injects test weather, a matching clock, and Ollama transport only. Every planning-state mutation, confirmation boundary, compiler, simulator, optimizer and recovery comparison runs through the unmodified real backend. Fixture values never enter the production app.

The suite covers navigation/chat persistence; structured proposals, follow-ups, missing specifications and explicit confirmation/rejection; manual creation/revision; conflict refresh; deterministic calculation without a local-model answer; pending/failed/stale-result suppression; actual hourly battery values/percentages/capacity preservation/reserve/essential shortages; playback reset; forecast failure/retry; expired sessions; mobile layout and keyboard operation. Main Chat separately owns real installed-model/live-weather evaluation evidence.

Latest verified frontend handoff: **17 Chromium journeys**, **362 backend checks**, TypeScript, and production build pass against the Main Chat dependency. Desktop checks cover page identity, meaningful content, no framework overlay, console health, and the real confirm/edit/recalculate interaction. Mobile checks use 375×812, keyboard navigation, no horizontal overflow, and exact hourly battery readouts. Browser plugin was unavailable, so validation used the existing Playwright runtime. Visual evidence is saved outside the repository in the OS temporary directory (`lifeline-two-page-assistant.png`, `lifeline-two-page-proposal.png`, `lifeline-two-page-overview-mobile.png`).
