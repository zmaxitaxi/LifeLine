# Reviewed energy settings and local state

The existing simulator and MILP still perform every energy calculation. Energy
settings can now be reviewed and adopted inside the same planning session;
confirmed activities and the physical equipment inventory are retained.

## Review API

Use the current `expected_revision` for each write:

- `POST /api/planning/sessions/{id}/energy-proposals`
- `PATCH /api/planning/sessions/{id}/energy-proposals/{proposal_id}`
- `GET /api/planning/sessions/{id}/energy-proposals/{proposal_id}`
- `POST /api/planning/sessions/{id}/energy-proposals/{proposal_id}/confirm`
- `POST /api/planning/sessions/{id}/energy-proposals/{proposal_id}/reject`

Create and patch accept `settings` with any explicitly supplied
`battery_capacity_kwh`, `initial_battery_kwh`, `reserve_kwh`, `pv_capacity_kw`,
`charge_efficiency`, `discharge_efficiency`, `max_charge_kw`, or
`max_discharge_kw`. Omitted settings remain unchanged; explicit null is invalid.
The response includes resolved `energy_settings`, `energy_proposals`, and
`active_energy_proposal_id`. Each proposal contains the exact patch and full
`proposed_energy_settings` for before/after review.

Staging or rejecting a change preserves adopted settings and current results.
Confirm takes `{expected_revision, idempotency_key}`, applies the settings once,
invalidates the previous result, and recalculates using the real forecast and
confirmed activities. An existing recovery comparison is recalculated too.
Input changes after a proposal was staged require a new review (`409`);
duplicate confirmation does not apply or calculate twice. A failed forecast or
calculation retains confirmed inputs and reports a failed plan.

`initial_battery_kwh` is the explicit assumption at the selected day's midnight.
Increasing capacity does not rescale this absolute energy. Current readings are
separate `{energy_kwh, measured_at}` records with an explicit timezone-bearing
ISO timestamp. They never silently become starting energy. Omit
`current_battery_reading` to retain the reading, or explicitly use null to review
clearing it. Both starting energy and a retained current reading must fit the
proposed capacity; lower the assumption or clear/update the reading explicitly.

## Restart recovery

The production `app.main:app` saves private atomic JSON snapshots under
`.local/planning-state.json` (git ignored, file mode 0600). Set
`LIFELINE_STATE_PATH` to another file, or `:memory:` to disable persistence.
`create_app(planning_state_path=...)` provides an isolated test seam; ordinary
test applications remain in memory.

Snapshots retain session inputs, drafts, confirmed activities/settings,
idempotency receipts, computed results with their original source timestamps,
recovery selection, recent model context, and the last 80 conversation messages.
Interrupted calculations restore as failed, never current. Corrupt snapshots
stop startup with a recovery message rather than silently discarding confirmed
inputs. Atomic replace and fsync protect the preceding snapshot if a write fails.
A failed save reloads the last durable state and returns `503 STATE_UNAVAILABLE`;
an unsaved confirmation or idempotency receipt cannot be acknowledged as saved.
This remains a local, single-process prototype; do not run multiple workers
against one state file. A saved forecast is still a dated forecast, not newly
retrieved weather, and saved results retain their original modeled date.

`GET /api/planning/sessions/{id}/conversation` returns ordered user and assistant
messages with stable IDs and timestamps. Agent responses include `message_id`
and `user_message_id` so the UI can reconcile optimistic and restored messages
without duplication. Social messages do not alter input or planning revisions.

Agent responses also carry `presentation` identifying the relevant result's
input revision, generation, selected tested option IDs, and whether a schedule
is relevant. Ordinary conversation does not automatically display every plan.
The numerical API contracts remain strict even when a native model's tool
template needs a narrowly scoped argument adapter.

Native `propose_energy_settings` and `update_energy_settings_draft` stage flat
operator-stated settings only; the model cannot confirm them. Explicit
`initial_battery_pct` and `current_battery_pct` are converted by Python using the
proposed capacity, with the current percentage timestamped when received. An
explicit current reading remains separate from midnight energy. Field/source
guards reject invented values, unit errors and swapping capacity with starting
energy. The runtime verifies these guards independently of Llama tool choice.

## Validation

`backend/tests/test_energy_settings.py` exercises reviewed before/after state,
real recomputation, preservation of absolute starting energy and confirmed
equipment, timestamp requirements, invalid values, cancellation, stale inputs,
and receipt conflicts. `backend/tests/test_planning_persistence.py` exercises
restart round trips, interrupted calculations, conversation IDs, corrupt input,
and failed atomic replacement. Mocked weather transport in these tests is
explicitly synthetic test data, not field validation or a live-weather claim.
