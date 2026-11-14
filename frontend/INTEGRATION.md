# Two-page frontend integration

Work is isolated on `codex/frontend-two-page` in `/private/tmp/lifeline-frontend-two-page`; the original dirty checkout is untouched. The branch began from fetched `origin/main` (`ac3a45e`) and integrates Main Chat's published backend dependencies through `da52d5f` (including `cf8f693` and `aa3fb39`). Frontend changes are exclusively under `frontend/`; agent, simulation, optimization and API contracts remain owned by Main Chat.

## Run and integrate

Apply the supplied frontend commit after its backend dependencies, including native conversation/synthesis commit `d37efc6` supplied by Main Chat. Required contracts are `contracts/planning.ts`, `contracts/recovery.ts`, `contracts/weather.ts`, and `docs/ACTIVITY_PLANNING.md`.

```sh
npm --prefix frontend ci
npm --prefix frontend run build
.venv/bin/python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8020
```

Open `http://127.0.0.1:8020/`. For development use the backend plus `LIFELINE_API_PORT=8020 npm --prefix frontend run dev`. Ollama with `llama3.1:8b` is required for conversation. The existing deterministic numerical tools remain available to Llama; this UI never substitutes a deterministic reply when Llama is unavailable. It shows an explicit retry instead. Older standalone deterministic backend endpoints are preserved but not used by production frontend planning actions.

## Experience and state

- Exactly two destinations: **AI Assistant** (default) and **Clinic Overview**. Navigation preserves the mounted conversation and unsent message. Plans and multiple computed alternatives appear inside the chat; there is no Explore plan link. Earlier calculations remain labeled, read-only transcript evidence.
- Overview fills the available workspace with four equal regions at widths of 600 px and above, including Codex's narrow desktop preview. Smaller phones stack the same four panels. Each panel scrolls independently. Equipment is visible immediately, opens details on selection, and can be added from Overview or chat. Battery playback and calculated plan choices are expanded by default.
- Overview equipment entry collects only operator-provided information and sends it to Llama through the session agent. Flexible equipment accepts printed watts and whole device-hours; Python derives its energy requirement. Event duration alone never becomes electrical demand. Unknown priority, ratings, operating hours and interruptibility remain questions, not defaults.
- Every planning action uses the session `/agent` API. Replies render the model's returned validated message unchanged. While a request is running, results and reported tool activity wait for the final response; the UI shows only a generic preparing status, never private model reasoning. Read-only explanations use the exact selected comparison without changing its generation or selection.
- `usePlanningSession` caches server responses only. Local storage contains one opaque session ID, never a competing configuration. Confirm and Cancel use the explicit canonical review endpoints; equipment is not adopted before Confirm. HTTP 409 refreshes and requires review instead of silently replaying changes.
- Results require `plan_status=current` and a matching input revision. Pending, failed or ambiguous recalculations suppress stale evidence. Recovery selection uses server revision/input revision/generation checks and changes only the inspected comparison, not physical equipment.
- Every battery value is an actual hourly boundary from the selected scenario's `.plan`, including the existing baseline. Percentages use that scenario's capacity; stored kWh, capacity, reserve and essential shortages stay distinct. Playback steps whole hours only and resets on new results or selection. CSS fill easing does not create intermediate simulated values; reduced motion removes it.
- Weather uses `/api/weather/outlook` for actual current model conditions and seven daily forecasts, separately from the energy model's solar forecast. Selecting the calculated planning date/hour displays actual baseline and selected `pv_kwh` and energy flows. Other dates explicitly have no clinic energy calculation; weather codes never generate fictional seven-day energy values. Retrieval errors have a short retry path; missing readings show unavailable rather than zero. Source/timestamp/uncertainty stay in details.

## Limits

Sessions are in process memory. A server restart invalidates the stored ID; the UI explains this and requires an explicit new-session action. Earlier activities are never silently copied. Bootstrap uses labeled Kisumu example inputs and an assumed midnight battery state, not a measured current charge. Base clinic/date/configuration inputs are immutable within a session in the current contract. There is no physical equipment control, infrastructure adoption, clinical-cycle validation or clinical availability guarantee.

## Validation

```sh
npm --prefix frontend run typecheck
npm --prefix frontend run build
npm --prefix frontend run test:e2e
.venv/bin/python -m pytest backend/tests -q
```

Playwright uses isolated ports 8012/5182, configurable with `LIFELINE_API_PORT`/`LIFELINE_UI_PORT`. Browser artifacts live in the OS temporary directory. The Browser plugin was not available, so tests use the existing Playwright setup. The test harness injects model-wire and provider-weather fixtures; the authoritative session API, validation, compiler, simulator, optimizer and recovery evaluation execute unchanged. Fixtures never enter the production app. Real installed-model/live-weather validation remains a separate integration check.

Coverage includes chat/navigation persistence, model replies and follow-ups, actual tool calls, explicit proposal confirmation/rejection, equipment entry and backend-derived energy, final-answer gating, reply retry without deterministic substitution, read-only selected-plan explanations, stale-result clearing, full-width/narrow/mobile layouts, keyboard operation, scrollable equipment details, current/week weather and errors, weather-hour energy grounding, canonical plan selection, all 25 battery boundaries, capacity preservation, reserve and essential-shortage notices, playback reset and reduced motion.

Verified against `d37efc6`: **25 Playwright journeys**, **424 backend tests**, TypeScript and the production build pass. Browser checks cover 1280×900 desktop, 631×955 in-app preview and 375×812 phone layouts. The full-width desktop and preview screenshots are saved to the OS temporary directory as `lifeline-four-square-overview.png` and `lifeline-preview-four-panels.png`.
