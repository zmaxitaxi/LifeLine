# LifeLine

AI-assisted energy planning for a fictional off-grid clinic. LifeLine will forecast solar generation, simulate a battery, and recommend when to run flexible electrical loads while reporting critical shortages honestly.

**Current status: reviewed build specification and three-person implementation plan. The application has not been implemented.** This repository does not yet contain a running dashboard, backend, solver, or application test results.

## Start here

1. Read the [review and decisions](docs/REVIEW.md) for what changed and what remains unverified.
2. Use the [detailed build brief](docs/BUILD_BRIEF.md) as the implementation specification.
3. Pick one of the three roles in the [team plan](docs/TEAM_PLAN.md).
4. Implement against the shared [API types](contracts/api.ts) and [scenario configuration](contracts/scenarios.json).
5. Complete the [acceptance checklist](docs/ACCEPTANCE.md) before calling the MVP demo-ready.

The [original supplied brief](docs/source/LifeLine_Codex_Build_Brief.md) is preserved verbatim for comparison. Its embedded instructions are source material; this delivery reviews and expands that material into a build handoff.

## The three owners

| Owner | Responsibility | First handoff |
|---|---|---|
| Person 1 — Energy and optimization | Forecast, physical simulator, baseline, constrained solver, model tests | Pure Python functions returning the agreed plan data |
| Person 2 — API and integration | FastAPI, validation, fixtures, dependency setup, CI, integration, release checklist | Validated endpoints and a response the dashboard can consume |
| Person 3 — Dashboard and demo | React dashboard, accessible responsive charts, scenario controls, recommendations, demo | A complete screen connected to the API |

Use these role labels until actual teammate names are supplied. The roles are assignments in the plan; no GitHub users have been assigned or contacted.

## Verify the planning inputs now

Requires Python 3.11+ and no third-party packages or network access:

```bash
python3 scripts/check_plan.py
```

This checks the committed synthetic profiles and a reference physical dispatch. It verifies why the three presets produce useful demo conditions. It does **not** implement or validate the future optimizer, API, or dashboard.

Expected calibration, rounded for display:

| Preset | Initial battery | Solar / 24 h | Critical demand / 24 h | Reference result |
|---|---:|---:|---:|---|
| Normal | 14 kWh | 30.645 kWh | 5.340 kWh | Critical demand and all baseline flexible demand served; reserve maintained |
| Storm | 6 kWh | 2.452 kWh | 5.340 kWh | Critical-only minimum 2.958 kWh; baseline minimum 0.748 kWh; reserve unavoidably at risk |
| High Demand | 14 kWh | 30.645 kWh | 14.340 kWh | At least 1.320 kWh critical shortfall from the 4 kW discharge limit at hours 20 and 21 |

Storm explicitly starts with a depleted battery to illustrate earlier cloudy days. High Demand adds a fictional operator-protected 4.5 kW load at 20:00–22:00. These are synthetic demonstration choices, not measurements or medical recommendations. Overrides can change the expected statuses.

## Run the application after implementation

The following are the **required future development commands**, not commands that work in this planning-only repository. Person 2 must create the referenced dependency files and verify the commands before release.

Backend, from the repository root:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r backend/requirements-dev.txt
python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

Frontend, in a second terminal:

```bash
cd frontend
npm ci
npm run dev -- --host 127.0.0.1 --port 5173
```

Required release checks, from the repository root:

```bash
python -m pytest backend/tests
npm --prefix frontend run typecheck
npm --prefix frontend run build
```

Target Python 3.11 and Node 22.12+ within the Node 22 line. Commit exact tested dependency versions and `frontend/package-lock.json` during implementation. Vite's current setup requirements are documented in its [official guide](https://vite.dev/guide/). Serve all demo data, icons, and fonts locally; after dependency installation, the demo must run with internet access disabled.

## Delivery target

The supplied brief lists **Saturday, November 14, 2026 at 11:59 PM America/Los_Angeles** as the hackathon deadline. Treat this as a team planning assumption until checked against the actual event rules. The team plan targets an earlier release to leave time for submission.

Illustrative simulation; not for clinical or operational use. No hardware integration, medical equipment control, clinical advice, or deployment certification is included.
