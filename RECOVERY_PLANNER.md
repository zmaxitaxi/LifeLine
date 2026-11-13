# Energy Recovery Planner

Backend integration contract on `codex/energy-recovery`, based on `main` commit `ac3a45e`. The primary model remains local `llama3.1:8b`. This branch preserves the existing frontend; the UI chat owns its presentation and navigation.

## API and agent tools

- `POST /api/recovery/plan`: strict `RecoveryRequest` → `RecoveryResponse`; see [contracts/recovery.ts](contracts/recovery.ts), [OpenAPI](contracts/openapi.json) and [Python schemas](backend/app/recovery_models.py).
- `GET /api/demos/recovery`: input-only historical demonstration; submit its `request` to the recovery endpoint to calculate results.
- Native agent tool `generate_recovery_plan({day, focus, sunshine_factor})`: `focus` is `all`, `scheduling`, `solar`, `battery`, `output`, `optional` or `backup`. Existing forecast, equipment and capacity tools remain available.
- `POST /api/agent/ask` and `/api/agent/stream` return additive `recovery` data. An essential deficit, reserve breach or unfinished flexible work in a forecast plan also activates recovery investigation against the same captured weather snapshot.

Example request:

```json
{
  "latitude": -0.0917,
  "longitude": 34.768,
  "clinic": {"scenario": "high_demand"},
  "midnight_battery_kwh": 14.0,
  "day": "tomorrow",
  "focus": "all",
  "sunshine_factor": 1.0,
  "weather_mode": "live_forecast",
  "optional_load_ids": []
}
```

`live_forecast` is the default. It retrieves actual Open-Meteo radiation through the existing validated/cache-aware service; failure never silently switches to a scenario. `existing_scenario` is an explicitly selected historical/synthetic demonstration. Its returned provenance and date distinguish it from current weather.

## Known clinic context

Agent requests can set `use_configured_context: true`. The configured equipment, location, energy system and starting-energy assumption are then available without another inventory review prompt. A supplied `midnight_battery_kwh` or confirmed `starting_battery_pct` takes precedence. An explicitly configured `clinic.initial_battery_kwh` may be used as the starting assumption. The labeled synthetic example can use its preset starting assumption. Unverified real-clinic inputs with no configured starting charge still require that missing fact; a current battery reading is never a prediction of tomorrow's charge.

The UI should disclose example inputs and the starting assumption next to the clinic context. Legacy clients that omit this opt-in retain their existing review flow. `context_sunshine_factor` preserves the prior selected sensitivity across follow-ups. `active_requirement` holds the last explicitly specified additional fixed requirement: it stays hypothetical and is retained during weather/recovery follow-ups, without adopting it into the inventory. `RequirementResult.arguments` supplies the strict argument object for that continuation.

## Calculation and comparison

The planner reuses `forecast_case` or the extracted shared `simulate_case`, which both use the existing `compare_schedules`, battery simulator and lexicographic MILP. No second dispatch engine or LLM arithmetic is used.

All options preserve essential equipment, absolute initial stored kWh, absolute reserve, efficiencies, charge limit, equipment windows and weather. Each option explicitly lists any changed solar capacity, battery capacity, discharge output limit, or authorized optional requirement. Default candidate sizes test three bounded increases per infrastructure type; they are sensitivities, not products or installation recommendations. No intervention is physically applied.

The response contains the existing fixed plan, the original three-way schedule comparison, every tested intervention, their verified hourly trajectories, numerical metrics/deltas, infrastructure/work changes, and remaining hourly essential deficits. Explicitly postponed work remains unfinished relative to the original workload. Only caller-supplied `optional_load_ids` that refer to flexible equipment can be postponed; an essential ID is rejected before weather access.

Ranking minimizes essential unserved energy, reserve shortfall and breached boundaries, original flexible work unfinished, then normalized modeled change magnitude. `smallest_tested_resolving_option_id` means the smallest score among the tested candidates meeting all original electrical requirements. It is neither a continuous sizing optimum nor a cost optimum. A best-ranked option can still have unresolved deficits; check `modeled_all_requirements_met`, `remaining_constraints` and `backup_deficits`.

Backup deficits are delivered electrical kWh for each local hourly slot. No generator ratings, fuel estimates, purchases, clinical decisions or equipment controls are inferred.

## UI integration

Use `recovery.reference.baseline` for the current schedule and `option.plan`/`option.simulation.optimized` for the selected intervention. Battery percentages must divide each plan's stored energy by its own capacity. Do not replace capacity changes with a fully charged initial battery. Show a concise diagnosis, the operational `reschedule` option, the best tested hypothetical option, remaining limits and a human review action; put numerical details in a disclosure. Preserve existing chat and battery playback.

`recovery.forecast` is nullable only for explicit scenario mode. `planning_date` is the historical date for bundled NASA weather and null for an undated synthetic example. Do not require `AgentResponse.result` when a scenario recovery is present; render from `recovery.reference` instead.

## Validation and limits

Automated tests cover resolved scheduling/generation/storage/output cases, empty-storage/no-solution cases, protected equipment, original-work denominators, actual weather conversion and independent hourly balances, context continuation, invalid forecasts and historical provenance. Transport fixtures are synthetic test inputs, not live/model-quality evidence.

`scripts/check_recovery_agent.py` calls the real installed model, records its native arguments and executes the actual numerical tools. Default mode retrieves a real forecast once; `--recorded-forecast FILE` explicitly labels a replay. It is a small integration smoke, not the previous team's comprehensive evaluation or a validation of a real clinic.

Only modeled electrical feasibility is checked. Staffing, clinical suitability, real nameplate ratings, installation, inverter topology/surge capacity, costs, degradation and multi-day reliability require external human review. Individual interventions are tested; combinations are not searched. A technical failure returns an error, never a partial successful recovery comparison.

Recorded verification on November 13: 326 backend tests passed; production TypeScript/build passed; all 23 existing Chromium journeys passed (22 on the initial isolated run, plus the static-server check after setting its API-port environment variable). Six real native Llama questions passed with an actual Open-Meteo retrieval at 22:42:17 UTC; warm follow-ups took 2.38–2.68 seconds and the first question 10.16 seconds on this Mac. This is integration evidence on one machine, not a replacement for the team's earlier comprehensive evaluation. Both documented historical and live demo CLI commands also completed through the real API. These checks cover the backend branch and existing main frontend; the separate two-page UI integration still needs its own final browser verification.
