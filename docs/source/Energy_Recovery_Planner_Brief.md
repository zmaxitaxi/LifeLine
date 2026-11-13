# LifeLine — Build an AI Energy Recovery Planner

## Objective

Transform LifeLine from an energy forecasting and battery monitoring assistant into an AI-powered energy reliability problem-solving system for resource-constrained healthcare clinics.

Repository: https://github.com/zmaxitaxi/LifeLine

The primary agent currently uses `llama3.1:8b` through Ollama.

**Keep the local LLM as the primary agent. Do not replace it with Wajo or Claude.**

Preserve the existing application, simulator, MILP optimizer, weather integration, tests, and simplified chat-first interface.

The goal is not to add another dashboard.

The goal is to help clinic operators answer:

> "We're going to run out of electricity. What can we actually do about it?"

## Phase 1 — Inspect the current architecture

Review:

- `backend/app/local_agent.py`
- `backend/app/agent_tools.py`
- `backend/app/forecast_planner.py`
- `backend/app/optimizer.py`
- `backend/app/energy_simulator.py`
- `backend/app/diagnosis.py`
- `backend/app/comparison.py`
- `backend/app/agent_routes.py`

Identify existing functionality that can be reused.

Do not duplicate the simulator or optimizer.

Document the current capabilities and remaining gaps.

## Phase 2 — Implement an Energy Recovery Planner

Create a backend recovery-planning system that investigates potential responses whenever the model detects insufficient power, incomplete flexible work, or battery reserve violations.

The planner must evaluate several types of intervention.

### A. Equipment rescheduling

Determine whether changing permissible flexible equipment schedules can resolve the shortage.

Respect all existing protected equipment requirements.

Report how much work is completed, postponed, or left unfinished.

### B. Solar capacity

Evaluate whether increasing photovoltaic generation capacity improves the situation.

Test multiple candidate solar capacities using the same weather conditions and equipment requirements.

Report:

- Solar capacity tested.
- Essential energy served.
- Remaining shortages.
- Battery reserve violations.
- Flexible work completed.

Do not assume extra panels can be installed immediately.

### C. Battery capacity

Evaluate whether increasing battery capacity would help.

Preserve physically meaningful assumptions about the initial stored energy.

Do not assume a larger battery begins fully charged.

Distinguish storage-capacity limitations from insufficient generation or output-power constraints.

### D. Battery/inverter output limits

Determine whether the shortage is caused by insufficient output power rather than insufficient energy.

Evaluate higher output limits as hypothetical alternatives.

Explain when increasing battery capacity alone would not resolve the problem.

### E. Flexible demand reduction

Determine whether postponing or reducing operator-designated optional loads can preserve energy for essential services.

Never reduce essential demand automatically.

### F. Backup energy requirements

Calculate the remaining unmet essential energy after feasible scheduling changes.

Identify the hours when additional energy is required.

Report electrical energy deficits without converting them into unsupported generator ratings, fuel needs, or purchasing recommendations.

## Phase 3 — Compare interventions

Implement a structured comparison system.

For each intervention, calculate:

- Essential energy served.
- Essential energy unserved.
- Flexible work completed.
- Flexible work deferred.
- Minimum battery energy.
- Reserve violations.
- Required infrastructure changes.
- Remaining unsolved constraints.

All calculations must use the existing simulator and optimizer.

Compare alternatives under identical weather, demand, and initial conditions unless the intervention explicitly changes one of those inputs.

Do not compare unrelated scenarios as if they were equivalent.

### Ranking

Rank interventions based on:

1. Satisfying essential electrical demand.
2. Avoiding reserve violations where physically feasible.
3. Completing required flexible work.
4. Minimizing the modeled magnitude of operational or infrastructure changes.

Do not claim to identify the cheapest option without cost data.

Do not call an intervention operationally feasible solely because the electrical model supports it.

Distinguish:
- Modeled electrical feasibility.
- Operational feasibility.
- Clinical acceptability.
- Cost and implementation feasibility.

Only the first is currently within LifeLine's validated scope.

## Phase 4 — Integrate with the local LLM

Expose the Recovery Planner through validated agent-callable tools.

Suggested tools:

- `diagnose_energy_shortage`
- `evaluate_recovery_options`
- `compare_infrastructure_changes`
- `generate_recovery_plan`

Reuse existing tools where they already provide equivalent functionality.

The local LLM should decide which investigation is appropriate.

Python should execute the calculations.

The LLM must not invent numerical outputs or make engineering decisions independently of the validated model.

### Example conversation

User:

"We're expecting very little sunshine tomorrow. How can we keep our clinic running?"

LifeLine:

1. Retrieves the actual weather forecast.
2. Evaluates the clinic's current electrical requirements.
3. Identifies any energy shortages.
4. Runs alternative operating schedules.
5. Tests relevant hypothetical infrastructure changes.
6. Compares the computed results.
7. Produces an actionable recovery plan.

The user should be able to ask:

"Would another battery help?"

"What about more solar panels?"

"Can we move equipment to the afternoon?"

"What's the smallest modeled change that eliminates the shortage?"

The agent should answer through actual calculations.

## Phase 5 — Generate actionable recovery plans

The final response should clearly communicate:

### 1. Problem

What is preventing the clinic's electrical requirements from being met?

### 2. Best available operational action

What can staff consider changing with their current infrastructure?

### 3. Additional resources

What hypothetical infrastructure or backup support could address remaining shortages?

### 4. Expected modeled improvement

How do the calculated results differ from the current plan?

### 5. Remaining limitations

Which requirements remain unmet, and what assumptions prevent definitive recommendations?

### 6. Next action

What should the operator review or confirm?

All proposed changes must require human review.

The application must not automatically control equipment or authorize purchases.

## Phase 6 — Update the frontend

Keep the existing chat-first UI.

Do not add a separate complicated Recovery Planner dashboard.

When a shortage is detected, allow the agent to present a concise recovery summary within the conversation.

For example:

**Problem detected**
The modeled electricity supply is insufficient to meet current requirements.

**Options evaluated**
- Reschedule flexible equipment.
- Increase solar capacity.
- Increase battery capacity.
- Review output-power limitations.

**Recommended next step**
Present the most promising modeled intervention and explain its limitations.

Provide expandable details for users who want to inspect the calculations.

Preserve the existing animated battery visualization if it has been implemented.

If it is not yet implemented, do not delay core recovery functionality to build it.

## Phase 7 — Test real problem-solving ability

Add tests covering:

1. Shortages resolved through rescheduling.
2. Shortages resolved through additional solar capacity.
3. Storage-limited scenarios.
4. Output-power-limited scenarios.
5. Cases where additional battery capacity does not help.
6. Cases where no tested intervention resolves the shortage.
7. Protection of essential equipment.
8. Correct numerical comparisons.
9. Multi-turn follow-up questions.
10. Invalid or unavailable weather inputs.

Test the local LLM's ability to select and execute the appropriate recovery tools.

Do not use scripted responses as evidence of agent functionality.

## Phase 8 — Create a hackathon demonstration

Build one compelling, calculated demonstration where:

1. A clinic faces an electricity shortage.
2. LifeLine identifies the underlying constraint.
3. The agent investigates multiple possible solutions.
4. At least one intervention produces a meaningful modeled improvement.
5. LifeLine explains what the operator can do next.
6. The result updates when the user changes a requirement.

Use live weather when available, but keep a clearly labeled historical demonstration as a reliable fallback.

Do not fabricate shortages or improvements.

## Constraints

- Keep `llama3.1:8b` as the primary model.
- Preserve the current deterministic fallback.
- Do not integrate Wajo at this stage.
- Preserve the existing simulator and optimization logic.
- Do not add unnecessary frontend complexity.
- Never fabricate numerical results.
- Never silently change essential medical equipment requirements.
- Never claim clinical safety or guaranteed electricity availability.
- Do not recommend specific hardware purchases without verified specifications and engineering review.
- Do not control physical equipment.

## Final verification

Run all existing backend and frontend tests.

Add regression tests for the new recovery-planning functionality.

Verify that calculated results remain consistent across the frontend, agent responses, and backend.

Update the README and demo documentation.

## Final report

Provide:

1. Recovery Planner architecture.
2. Tools added or reused.
3. Interventions supported.
4. Computed results from the strongest example.
5. Test results.
6. Remaining limitations.
7. Instructions for demonstrating the complete workflow.

**Success criterion: LifeLine should identify an energy reliability problem, investigate its causes, compare possible interventions, and recommend an actionable, evidence-backed recovery plan—not merely display battery levels or predict shortages.**