# LifeLine — AI-Driven Clinic Activity Planning and Shared State

You own the backend, AI agent, planning state, and API contracts for LifeLine.

Repository: https://github.com/zmaxitaxi/LifeLine

Coordinate with a separate UI implementation chat.

**Do not redesign the frontend or independently modify its primary navigation/components.**

Sync with the latest `main` before starting.

Preserve the existing local Llama 3.1 8B integration, LLM evaluation fixes, Open-Meteo weather integration, optimizer, simulator, and Recovery Planner functionality.

## Objective

Enable users to configure clinic activities and equipment requirements through natural-language conversation.

The user should be able to say:

"We have a vaccination campaign tomorrow from 9 AM to 3 PM. Will we have enough electricity?"

LifeLine should translate that into a structured proposed activity, request missing information when necessary, and update the confirmed clinic plan only after approval.

## 1. Structured planning state

Define a shared planning model containing:

- Selected clinic.
- Clinic location.
- Planning date.
- Confirmed activities.
- Proposed activities.
- Equipment inventory.
- Equipment-to-activity associations.
- Energy-system configuration.
- Weather forecast reference.
- Current computed plan.
- Selected recovery intervention.

Avoid duplicating equipment energy demand when multiple activities reference the same physical device.

Preserve the distinction between proposed and confirmed requirements.

Do not create accounts or a database unless genuinely necessary.

## 2. Activity model

Each activity should support:

- Unique identifier.
- Name.
- Planning date.
- Start/end window.
- Completion deadline, where applicable.
- Referenced equipment.
- Additional proposed equipment.
- Confirmation status.

Do not assume that every activity adds electrical demand.

An activity such as a vaccination campaign may simply constrain equipment already present in the clinic inventory.

## 3. AI activity extraction

Extend the local LLM's validated tools to support activity proposals.

The agent should:

1. Recognize activity names and timing.
2. Match known equipment where possible.
3. Identify missing information.
4. Ask concise clarification questions.
5. Produce structured proposals.
6. Preserve confirmed equipment requirements.
7. Never invent power ratings or clinical priorities.

Use strict schemas and backend validation.

Do not allow the LLM to mutate confirmed state directly.

## 4. Proposal and confirmation API

Implement explicit operations to:

- Create a draft activity.
- Update a draft.
- Inspect proposed changes.
- Confirm or reject a proposal.
- Read the current planning state.
- Update an existing confirmed activity through a reviewed change.

The confirmation operation must be idempotent and prevent duplicate equipment demand.

Only confirmed changes should affect the active energy plan.

## 5. Simulation integration

Convert confirmed activities into energy constraints.

Reuse the existing simulator and optimizer.

Respect:
- Essential loads.
- Allowed operating hours.
- Required durations.
- Deadlines.
- Existing equipment specifications.

Reject unsupported or physically inconsistent constraints.

After confirmation, invalidate outdated results and recalculate using the current planning inputs.

## 6. Conversational continuity

Ensure the assistant understands the latest confirmed planning state on every turn.

For example:

User: "We have a vaccination campaign tomorrow."

Assistant: Requests missing details.

User: "It starts at 9 AM."

Assistant: Updates the draft.

User: "Actually, make that 10 AM."

Assistant: Updates the same draft, not a duplicate.

User: "Confirm."

Assistant: Confirms exactly one activity.

User: "What if tomorrow is cloudier?"

Assistant: Recalculates using that confirmed activity.

Address the previously documented T4 multi-turn limitation.

## 7. API contract for UI team

Publish the exact request/response schemas before the UI team integrates.

Document:
- Planning state.
- Activity proposal.
- Confirmation.
- Rejection.
- Simulation results.
- Error responses.

Keep existing API routes compatible wherever possible.

## 8. Testing

Test:
- Multi-turn proposal creation.
- Draft updates.
- Confirmation and rejection.
- Duplicate prevention.
- Shared equipment references.
- Missing power specifications.
- Essential equipment protection.
- Weather changes after confirmation.
- Stale-result invalidation.
- Local model tool calling.
- Recovery Planner compatibility.

Use the real simulator for numerical integration tests.

Do not hardcode answers to evaluation prompts.

## Deliverables

1. Backend implementation.
2. Shared API contracts.
3. Updated tests.
4. Brief integration documentation for the UI team.
5. Clear examples of API requests and responses.

## Coordination

Own backend and contract files.

Avoid independently changing the frontend while the UI chat is working.

Commit changes on a dedicated branch and provide the commit reference and integration instructions.

Do not merge over another chat's uncommitted changes.

**Success criterion: A clinic worker can describe an activity naturally, review the extracted requirements, confirm them, and have the real energy model incorporate the changes across subsequent conversations.**