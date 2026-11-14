# Final two-page frontend integration

The assembled source is on `codex/lifeline-integration` in `/Users/maxli/Documents/ChatGPT/LifeLine/.worktrees/final-product`. The original dirty checkout is untouched. `origin/main` was fetched before this implementation; it remained `ac3a45e`. Main Chat owns the backend, agent, compiler, simulator, optimizer and HTTP/TypeScript contracts. Published backend changes are integrated unchanged.

## Run

```sh
npm --prefix frontend ci
npm --prefix frontend run build
LIFELINE_STATE_PATH=/Users/maxli/Documents/ChatGPT/LifeLine/.local/final-planning-state.json \
  .venv/bin/python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8020
```

Open `http://127.0.0.1:8020/`. Ollama with `llama3.1:8b` supplies conversation. Keep one backend worker for the local atomic JSON store. Use `LIFELINE_STATE_PATH=:memory:` only for disposable sessions. The state file is private and git ignored; it should remain outside temporary worktrees. For development run the backend plus `LIFELINE_API_PORT=8020 npm --prefix frontend run dev`.

For an older in-memory server, preserve its GET session state and actual browser transcript before stopping or refreshing it. Main Chat's `scripts/migrate_planning_snapshot.py` validates an offline export into a new private snapshot without overwriting an existing file. See `docs/ENERGY_SETTINGS_AND_LOCAL_STATE.md`. Keep original exports private. The migration preserves session/result IDs and source times, records imported chat explicitly, and never invents a current battery reading.

## Product behavior

- Exactly two destinations: **AI Assistant** (default) and **Clinic Overview**. Navigation preserves conversation and unsent text. Clinic Overview leads with the current computed outlook, one relevant recommendation and before/after comparison. A shared hourly energy chart and battery follow, with editable activities/equipment and weather below. Other calculated plans remain expandable with computed benefits, limits and exactly postponed work.
- First launch asks for clinic name/location and electrical setup, then a separate review. It starts with tomorrow in the clinic timezone without a date field. It never creates or calculates an example automatically. **Autofill demo setup** is an explicit, editable choice on the electrical step, using actual catalog hardware and equipment. A custom setup sends explicit hardware values with `equipment: []`, then asks the user to add real devices before assessing power. Standard efficiencies and output limits are identified as model assumptions. Unknown ratings remain unsaved rather than being guessed. Custom locations require explicit coordinates/timezone; no geocoding is implied.
- Legacy saved sessions are offered through **Resume clinic**, without displaying their plans on the welcome screen. A second opaque browser session pointer records that the user explicitly chose or reviewed a clinic; server data remains authoritative. **Change clinic** starts a separate setup without deleting the previous server record. Page navigation within a chosen clinic preserves conversation.
- **Add activity** opens an actual manual editor in Overview. Additions and revisions stage canonical server proposals. Equipment references, whole-day device runtime and activity-specific operating windows can be reviewed. Event duration alone never becomes electrical demand. Sharing a physical device does not duplicate it; larger essential/baseline requirements remain protected.
- **Add equipment** also uses the reviewed API directly. Users can complete missing specifications manually or continue in chat. Device watts and explicit whole operating hours are sent separately; Python derives electrical energy. Unknown specifications remain unknown. Unsupported continuous cycles cannot be represented as verified medical operations.
- **Power setup** opens the clinic energy editor. Stored energy assumed at the selected day's midnight is separate from a timestamped current battery reading. Percentages use the displayed battery capacity. Capacity edits preserve absolute stored energy; they do not silently fill the larger battery. Solar capacity, reserve, efficiencies and power limits are editable, with technical fields expanded only when requested.
- All manual edits have separate draft review, Confirm and Cancel actions. Stage/reject preserve the adopted configuration and valid calculation. Confirm uses the explicit idempotent API and its genuine recalculation; it does not trigger another model call or duplicate optimization. HTTP409 refreshes server state and requires fresh review. A failed calculation preserves confirmed inputs and removes obsolete evidence. Settings drafts based on changed inputs require a new review.
- Llama authors conversational text and chooses tools. The frontend does not classify user intent or substitute reply templates. Replies consume the backend's explicit `presentation` contract. Ordinary conversation gets no plan; an exact-plan explanation gets only that result; comparisons show only the actual option IDs intentionally supplied. No automatic all-alternatives panel or Explore plan link is appended.
- Changes to activities or energy settings initiated by chat use the same review boundaries and show the same state in Overview. Review cards appear when the response requests them; other replies do not repeatedly open a draft form. Compact draft shortcuts keep unfinished work reachable.
- The server owns conversation history and stable message IDs. The frontend reconciles optimistic user messages with `user_message_id`/`message_id` and restores history from `/conversation` after reload. Local storage contains one opaque session ID, never a separate planning database. Transient editor buffers and read-only displayed calculation snapshots are not authoritative inputs.
- Tool results are attached only with a matching current input revision and generation. Only the final model response releases new result cards. Read-only questions preserve current calculations and selection. Completed tool activity is optional; raw private model reasoning is never shown. During a request, the overview labels retained evidence as the last verified calculation.
- When the model is unavailable, chat offers an explicit retry. Manual drafting, editing, confirmation and numerical planning remain usable. Legacy deterministic backend assistant routes are preserved but never masquerade as Llama replies.
- Battery playback uses actual integer hourly boundaries from each scenario's `.plan`. Percentages use each scenario's capacity, alongside stored kWh and reserve. Essential unmet demand is distinct from low charge. Playback resets on changed results/selection; reduced motion removes fill transitions. CSS never creates sub-hour numerical readouts.
- Weather uses the independent current/seven-day outlook API. Clicking the modeled date/hour shows actual baseline and selected solar-energy rows. Other dates explicitly have no clinic energy calculation. Weather codes never become fictional energy generation. Missing readings stay unavailable, source/time details remain inspectable, and provider errors have a short retry path.
- Start the server with `LIFELINE_WEATHER_MODE=demo` for an explicitly labeled offline weather demonstration. Llama and the physical simulator remain real. The runtime notice uses `GET /api/weather/mode`; each saved calculation uses its own backend `weather_mode`, so earlier live results are never relabeled. Sample conditions are not presented as observations or a geographic forecast. Live weather remains the default when the environment setting is omitted.

## Verification

```sh
npm --prefix frontend run typecheck
npm --prefix frontend run build
npm --prefix frontend run test:e2e
.venv/bin/python -m pytest backend/tests -q
```

Playwright uses isolated ports 8012/5182, configurable with `LIFELINE_API_PORT`/`LIFELINE_UI_PORT`. It never reuses the production preview. Provider-weather and native model-wire fixtures are confined to `frontend/e2e/support`; authoritative review APIs, persistence models, validators, compiler, simulator, optimizer and recovery evaluation execute unchanged. Actual Ollama/live-weather journeys are separate release checks, not implied by fixture tests. No competing genuine model calls should run during a user's active turn.

Browser plugin was unavailable, so rendered verification uses the existing Playwright runtime. Desktop checks cover 1280×900, the narrow app preview 631×955, and phone 375×812. Tests cover manual activity/equipment editing, missing specs, shared runtime budgets, separate current/start energy, real recalculation, draft rejection, stale evidence, concurrency conflicts, conversation persistence and focused replies, original hourly battery integrity, forecast errors, and keyboard/focus operation. Screenshots and traces are saved outside the repository in the OS temporary directory.

The local store supports restart recovery and atomic rollback, not multi-user or multi-process synchronization. Forecast results retain their original modeled date and provenance after restart. No equipment control, physical infrastructure adoption, medical-cycle validation or clinical availability guarantee is implied.

Verified frontend handoff on Main Chat’s natural-agent dependency `edde294`: **38/38 Playwright journeys**, TypeScript and the production build pass; the combined backend suite passes **460/460**. Main Chat owns additional genuine Ollama/live-weather evidence and final integration checks. Final release references and any subsequent check counts are recorded in the handoff after assembly.

The additive demo-weather presentation on backend contract `9927b1c` passes TypeScript, the production build, and two focused browser regressions covering demo labeling and preservation of older live provenance. These are presentation tests with provider fixtures, not evidence of genuine Llama inference or a reachable live weather provider.

The setup-first version passes all **46 browser journeys** and **503 backend tests**, TypeScript and the production build. Six onboarding regressions cover no automatic creation/tool use, editable demo autofill and stored-energy consistency, vaccination proposals, empty custom equipment, explicit resume, mobile keyboard use and failed-save recovery. Browser model/weather transports remain test fixtures; the backend calculations are real. Earlier genuine local Llama demo evidence remains unchanged by this frontend-only flow.

The final overview/response-feedback iteration is described in `UX_AND_RESPONSE_TIMING.md`. Its full browser regression batch passes53/53 before the additional provider-display test. Browser DOM commit timing is distinct from server phase/inference timing and no genuine speed claim is derived from fixtures. Main Chat owns the final integrated backend/provider benchmark report.
