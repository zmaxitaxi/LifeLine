# Person 2 implementation plan

Person 2 owns the FastAPI integration, shared API contracts, dependency and CI coordination, and the release record. Start from the integrated `main` baseline reviewed at `f881eea`. The original B1–B7 deliverables are present in the repository. The work below verifies them on the release candidate and addresses defects found during verification. See the [team plan](TEAM_PLAN.md), [backend handoff](PERSON_2_HANDOFF.md), and [acceptance checklist](ACCEPTANCE.md).

## 1. Establish the release candidate

- Record the candidate SHA, OS, Python and Node versions, and demo machine. Use a clean checkout and a fresh virtual environment. If a fix is needed, use the team plan's `codex/api-integration` branch based on current `main`.
- **B1 — Setup and CI.** Use the pinned backend requirements and frontend lockfile. Verify the candidate's backend matrix on Python 3.11 and 3.12 and the frontend job on Node 22 from the [workflow](../.github/workflows/ci.yml). Record the actual CI run for the candidate SHA and the clean setup result on the demo machine.
- Run the existing checks from the repo root with the virtual environment active:

  ```text
  python -m pip install -r backend/requirements-dev.txt
  python -m pip check
  python -m pytest backend/tests -q
  python scripts/check_plan.py
  npm --prefix frontend ci
  npm --prefix frontend run build
  ```

- Install Playwright Chromium with `npx playwright install chromium` from `frontend`, then run `npm --prefix frontend run test:e2e` from the root. Playwright finds the root `.venv` on both Windows and Unix. Run the built-app smoke check below separately on the demo machine.

## 2. Verify API behavior and contract

Start Uvicorn after the frontend build with `python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000`. Use real HTTP against that process for the smoke checks.

| Assignment | Work and acceptance |
|---|---|
| **B2 — Input validation** | Check request and response models against `contracts/api.ts`, `contracts/forecast.ts`, and the generated OpenAPI snapshot. Exercise an omitted override, an explicit zero, and a capacity below inherited starting charge or reserve. Omission uses the preset, zero is preserved where valid, and incompatible merged values return the structured 422 response. |
| **B3 — Routes and orchestration** | Call `GET /api/health`, `GET /api/scenarios`, and `POST /api/simulate` for all four presets. Check that effective inputs match the request and scenario defaults. Verify 24 hourly rows per plan, finite numeric results, and all three plans returned from the same effective configuration. |
| **B4 — Examples and fixtures** | Check `contracts/examples/scheduling.response.json` against the live response shape. Confirm the built dashboard makes real API calls and that provider test fixtures stay confined to tests. A failed API call should display the corresponding failure state. |
| **B5 — Model integration** | Run the reference calibration and check HTTP results against it. Confirm the three plans preserve the same essential demand, equipment requirements, and hardware/weather inputs. Use Person 1 to review any discrepancy in physical accounting or optimizer behavior. |
| **B6 — Metrics and explanations** | Check that warnings are attributable to the correct plan and that served, deferred, and unmet energy agree with the plan data. Verify that a heuristic tie is disclosed, and that deferring work is reflected in any battery comparison. |
| **B7 — Failure handling** | Confirm the existing T13–T16 and shared T18 tests pass. Verify a modeled shortage returns HTTP 200 with `CRITICAL_SHORTAGE`, invalid input returns 422, and solver failures tested by the suite return structured 503 responses with no computed plan. |

For a contract defect, agree on the change with Persons 1 and 3, update affected backend and frontend consumers together, and regenerate schema/examples with `python scripts/export_api_contract.py`. Include a regression check for the defect.

## 3. Verify the full demo path

- **Built dashboard.** Open `http://127.0.0.1:8000/` on the demo machine. With Person 3, switch presets, edit a requirement, reset, and verify that the dashboard shows effective inputs and the latest response. Check the error and retry path and verify that an unavailable API does not leave an old plan displayed as current.
- **Offline fallback.** After installing dependencies and Chromium, verify that the synthetic and bundled historical modes can run with external requests blocked while localhost remains available. Record whether this was verified by browser request blocking or by disconnecting the machine.
- **Live forecast.** Run `python scripts/check_live_forecast.py --midnight-battery-kwh 6` against the running candidate using the demo inputs. Check the local planning date, forecast provenance, confirmed starting energy, and the lower-sunshine comparisons. Verify that a provider error or stale forecast is shown explicitly. Keep the deterministic fixture-backed forecast checks in CI and record the live smoke check separately with the retrieval timestamp.

## 4. Freeze and hand off the release

- Check the official event rules for eligibility and any LLM requirement, the deadline and timezone, team registration, required links, video or hosting requirements, and disclosure rules. Record the official source and any unresolved questions in the [submission checklist](../HACKATHON_CHECKLIST.md). Use the team plan's schedule as planning input until confirmed. Raise any required work outside the existing scope with the team before implementing it.
- Follow the [team plan's integration gates](TEAM_PLAN.md#schedule-and-integration-gates). At the 4 PM Saturday gate, complete clean setup, CI review, and offline checks. At the 8 PM gate, record the release SHA and rehearse that build with Person 3. By the 10:30 PM submission target, verify the required fields and links with the submission owner.
- Update the [release record](ACCEPTANCE.md#release-record) with the candidate SHA, environment, exact commands, actual results, CI run, demo evidence, and open items. Align the README and handoff instructions where the verified commands or current workflow differ. Record submission confirmation when available.

Person 2 is done when the candidate passes the API and built-app checks, the team can reproduce both the online demo and the offline fallback, and the release record identifies the tested SHA and any unresolved submission requirements.
