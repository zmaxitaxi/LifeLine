"""Local canonical state and activity-to-existing-model compilation.

No second dispatch engine: constraints produce SimulationRequest equipment.
"""
import asyncio
from datetime import datetime, timezone
from uuid import uuid4
from pydantic import ValidationError
from starlette.concurrency import run_in_threadpool
from .planning_models import (PlanningState, ActivityProposal, Activity, ActivityDraft,
                              ComputedPlan)
from .models import SimulationRequest, CriticalEquipment, FlexibleEquipment, RequestedTaskAllocation
from .forecast_planner import forecast_case
from .forecast_models import ForecastLocation
from .agent_tools import SnapshotService
from .recovery_models import RecoveryRequest
from .recovery_planner import generate_recovery_plan


class PlanningError(Exception):
    def __init__(self, code, message, status=422, fields=()):
        self.code, self.message, self.status, self.fields = code, message, status, fields


def merge_draft(previous, patch):
    try:
        return ActivityDraft.model_validate(previous.model_dump() | patch.model_dump(exclude_unset=True))
    except ValidationError:
        raise PlanningError('INVALID_ACTIVITY', 'Activity window, duration or deadline is inconsistent.') from None


def equipment_from_draft(item):
    values = item.model_dump(exclude_none=True)
    if item.category == 'flexible':
        values['baseline_allocations'] = []
        return FlexibleEquipment.model_validate(values)
    return CriticalEquipment.model_validate(values)


def missing_fields(details):
    missing = [field for field in ('name', 'planning_date', 'start_hour', 'end_hour', 'equipment_ids')
               if getattr(details, field) is None]
    for n, item in enumerate(details.additional_equipment):
        required = ('category',) if item.category is None else (
            ('power_kw', 'required_hours') if item.category == 'critical' else
            ('max_power_kw', 'required_energy_kwh', 'allowed_hours', 'divisible'))
        missing.extend(f'additional_equipment.{n}.{field}' for field in required if getattr(item, field) is None)
    return missing


def validate_activity(details, state, *, complete=True, target=None):
    missing = missing_fields(details)
    if complete and missing:
        raise PlanningError('PROPOSAL_INCOMPLETE', 'Review the missing activity requirements before confirming.', fields=missing)
    if details.planning_date is not None and details.planning_date != state.planning_date:
        raise PlanningError('INVALID_ACTIVITY', 'Activity date must match the selected session date.')
    inventory = {e.id: e for e in state.equipment_inventory}
    additional_ids = [e.id for e in details.additional_equipment]
    if len(additional_ids) != len(set(additional_ids)):
        raise PlanningError('INVALID_ACTIVITY', 'Additional equipment IDs must identify unique physical devices.')
    for item in details.additional_equipment:
        if item.id in inventory:
            old = next((e for e in target.details.additional_equipment if e.id == item.id), None) if target else None
            if old != item:
                raise PlanningError('INVALID_ACTIVITY', 'Use an existing equipment reference; confirmed equipment specifications cannot be replaced.')
        try:
            parsed = equipment_from_draft(item)
            if isinstance(parsed, CriticalEquipment) and not parsed.required_hours:
                raise PlanningError('INVALID_ACTIVITY', 'New equipment needs nonempty operating hours.')
            if isinstance(parsed, FlexibleEquipment) and parsed.required_energy_kwh > len(parsed.allowed_hours) * parsed.max_power_kw + 1e-7:
                raise PlanningError('INVALID_ACTIVITY', 'New equipment energy cannot fit its hourly power and allowed hours.')
            inventory[item.id] = parsed
        except ValidationError:
            item_missing = any(f'additional_equipment.{details.additional_equipment.index(item)}.' in f for f in missing)
            if complete or not item_missing:
                raise PlanningError('INVALID_ACTIVITY', 'Equipment specifications are inconsistent or unsupported.') from None
    known = set(inventory) | set(additional_ids)
    if details.equipment_ids is not None and not set(details.equipment_ids) <= known:
        raise PlanningError('INVALID_ACTIVITY', 'Referenced equipment ID is not in the inventory or proposed additions.')
    for constraint in details.equipment_constraints:
        if constraint.equipment_id not in known or constraint.equipment_id not in (details.equipment_ids or []):
            raise PlanningError('INVALID_ACTIVITY', 'Every constrained device must be an explicit equipment reference.')
        if constraint.equipment_id not in inventory:
            if not complete:
                continue
            raise PlanningError('PROPOSAL_INCOMPLETE', 'Equipment specifications must be completed first.')
        equipment = inventory[constraint.equipment_id]
        if constraint.required_hours is not None and equipment.category != 'critical':
            raise PlanningError('INVALID_ACTIVITY', 'Fixed operating constraints require critical equipment; continuous cycles are unsupported for divisible flexible tasks.')
        if constraint.allowed_hours is not None and equipment.category != 'flexible':
            raise PlanningError('INVALID_ACTIVITY', 'Essential equipment cannot be shortened, moved or made flexible.')
        hours = constraint.required_hours if constraint.required_hours is not None else constraint.allowed_hours
        if hours is not None:
            validate_hours(hours, details)
            if constraint.allowed_hours is not None and not set(hours) <= set(equipment.allowed_hours):
                raise PlanningError('INVALID_ACTIVITY', 'Flexible hours cannot extend the confirmed equipment window.')
    for item in details.additional_equipment:
        hours = item.required_hours if item.category == 'critical' else item.allowed_hours
        if hours:
            validate_hours(hours, details)
    return inventory


def validate_hours(hours, details):
    if details.start_hour is not None and any(h < details.start_hour for h in hours):
        raise PlanningError('INVALID_ACTIVITY', 'Equipment hours precede the activity start.')
    end = min(x for x in (details.end_hour, details.deadline_hour, 24) if x is not None)
    if any(h >= end for h in hours):
        raise PlanningError('INVALID_ACTIVITY', 'Equipment hours exceed the activity window or deadline.')


def compile_clinic(state, activities=None, inventory=None):
    equipment = {e.id: e.model_copy(deep=True) for e in (inventory or state.equipment_inventory)}
    for activity in activities if activities is not None else state.confirmed_activities:
        for constraint in activity.details.equipment_constraints:
            item = equipment[constraint.equipment_id]
            if constraint.required_hours is not None:
                item.required_hours = sorted(set(item.required_hours) | set(constraint.required_hours))
            if constraint.allowed_hours is not None:
                allowed = sorted(set(item.allowed_hours) & set(constraint.allowed_hours))
                if not allowed or len(allowed) * item.max_power_kw + 1e-7 < item.required_energy_kwh:
                    raise PlanningError('INVALID_ACTIVITY', 'Combined activity windows cannot meet the confirmed equipment energy requirement.')
                item.allowed_hours = allowed
                # Baseline requests outside the new reviewed window cannot run.
                # Redistribute only the baseline request, keeping required work fixed.
                remaining = sum(a.requested_kwh for a in item.baseline_allocations)
                allocations = []
                for hour in allowed:
                    energy = min(remaining, item.max_power_kw)
                    if energy > 0:
                        allocations.append(RequestedTaskAllocation(hour=hour, requested_kwh=energy))
                    remaining -= energy
                item.baseline_allocations = allocations
    try:
        return SimulationRequest.model_validate(state.clinic.model_dump(exclude_unset=True) |
            {'equipment': [e.model_dump() for e in equipment.values()]})
    except ValidationError:
        raise PlanningError('INVALID_ACTIVITY', 'Combined equipment exceeds the supported inventory or scheduling constraints.') from None


class PlanningStore:
    def __init__(self):
        self.states = {}
        self.lock = asyncio.Lock()
        self.receipts = {}
        self.generations = {}
        self.history = {}
        self.last_edited_fields = {}
        self.agent_diagnostics = {}

    def read(self, session_id):
        if session_id not in self.states:
            raise PlanningError('NOT_FOUND', 'Planning session was not found.', 404)
        return self.states[session_id].model_copy(deep=True)

    def check(self, session_id, expected):
        state = self.read(session_id)
        if state.revision != expected:
            raise PlanningError('REVISION_CONFLICT', 'Planning state changed. Refresh and review the latest state.', 409)
        return state

    def proposal(self, state, proposal_id):
        proposal = next((p for p in state.proposals if p.id == proposal_id), None)
        if proposal is None:
            raise PlanningError('NOT_FOUND', 'Activity proposal was not found.', 404)
        return proposal

    async def create(self, body, catalog):
        clinic = SimulationRequest.model_validate(body.clinic.model_dump(exclude_unset=True) |
            {'initial_battery_kwh': body.midnight_battery_kwh})
        config = catalog.resolve(clinic)
        inventory = catalog.equipment_for(clinic, config)
        clinic = SimulationRequest.model_validate(clinic.model_dump(exclude_unset=True) |
            {'equipment': [e.model_dump() for e in inventory]})
        state = PlanningState(id=str(uuid4()), revision=0, input_revision=0,
            selected_clinic_id=body.selected_clinic_id, clinic_name=body.clinic_name,
            location=body.location, planning_date=body.planning_date,
            clinic=clinic, equipment_inventory=inventory, timezone=body.timezone)
        async with self.lock:
            self.states[state.id] = state
        return state.model_copy(deep=True)

    async def propose(self, session_id, body):
        async with self.lock:
            state = self.check(session_id, body.expected_revision)
            target = next((a for a in state.confirmed_activities if a.id == body.target_activity_id), None)
            if body.target_activity_id and target is None:
                raise PlanningError('NOT_FOUND', 'Confirmed activity was not found.', 404)
            details = body.details
            if target:
                details = merge_draft(target.details, body.details)
            validate_activity(details, state, complete=False, target=target)
            proposal = ActivityProposal(id=str(uuid4()), details=details, missing_fields=missing_fields(details),
                target_activity_id=target.id if target else None, base_activity_version=target.version if target else None)
            state.proposals.append(proposal)
            self.last_edited_fields[state.id] = list(body.details.model_fields_set - {'planning_date'})
            state.active_proposal_id = proposal.id
            state.revision += 1
            self.states[state.id] = state
            return state.model_copy(deep=True)

    async def update(self, session_id, proposal_id, body):
        async with self.lock:
            state = self.check(session_id, body.expected_revision)
            proposal = self.proposal(state, proposal_id)
            if proposal.status != 'draft':
                raise PlanningError('PROPOSAL_CLOSED', 'Create a reviewed revision proposal for a confirmed activity.', 409)
            target = next((a for a in state.confirmed_activities if a.id == proposal.target_activity_id), None)
            details = merge_draft(proposal.details, body.details)
            validate_activity(details, state, complete=False, target=target)
            proposal.details, proposal.missing_fields = details, missing_fields(details)
            self.last_edited_fields[state.id] = list(body.details.model_fields_set - {'planning_date'})
            state.active_proposal_id = proposal.id
            state.revision += 1
            self.states[state.id] = state
            return state.model_copy(deep=True)

    async def reject(self, session_id, proposal_id, body):
        async with self.lock:
            state = self.check(session_id, body.expected_revision)
            proposal = self.proposal(state, proposal_id)
            if proposal.status == 'confirmed':
                raise PlanningError('PROPOSAL_CLOSED', 'Confirmed activities need a reviewed revision.', 409)
            if proposal.status != 'rejected':
                proposal.status = 'rejected'
                state.revision += 1
                if state.active_proposal_id == proposal.id:
                    state.active_proposal_id = None
                self.states[state.id] = state
            return state.model_copy(deep=True)

    async def confirm(self, session_id, proposal_id, body):
        async with self.lock:
            state = self.read(session_id)
            receipt = self.receipts.get((session_id, body.idempotency_key))
            if receipt:
                if receipt != proposal_id:
                    raise PlanningError('IDEMPOTENCY_CONFLICT', 'Confirmation key was already used for another proposal.', 409)
                return state, False
            proposal = self.proposal(state, proposal_id)
            if proposal.status == 'confirmed':
                self.receipts[(session_id, body.idempotency_key)] = proposal_id
                return state, False
            state = self.check(session_id, body.expected_revision)
            proposal = self.proposal(state, proposal_id)
            if proposal.status != 'draft':
                raise PlanningError('PROPOSAL_CLOSED', 'Rejected proposals cannot be confirmed.', 409)
            target = next((a for a in state.confirmed_activities if a.id == proposal.target_activity_id), None)
            if target and target.version != proposal.base_activity_version:
                raise PlanningError('REVISION_CONFLICT', 'Confirmed activity changed after this proposal was created.', 409)
            inventory = validate_activity(proposal.details, state, target=target)
            activity = Activity(id=target.id if target else str(uuid4()), version=target.version + 1 if target else 1,
                details=proposal.details.model_copy(deep=True))
            activities = [a for a in state.confirmed_activities if a.id != activity.id] + [activity]
            compile_clinic(state, activities, list(inventory.values()))  # validates combined constraints before committing
            state.confirmed_activities = activities
            state.equipment_inventory = list(inventory.values())
            state.clinic = SimulationRequest.model_validate(state.clinic.model_dump(exclude_unset=True) |
                {'equipment': [e.model_dump() for e in inventory.values()]})
            proposal.status, proposal.confirmed_activity_id = 'confirmed', activity.id
            if state.active_proposal_id == proposal.id:
                state.active_proposal_id = None
            state.input_revision += 1
            state.revision += 1
            self.invalidate(state)
            self.states[state.id] = state
            self.receipts[(session_id, body.idempotency_key)] = proposal_id
            return state.model_copy(deep=True), True

    def invalidate(self, state):
        state.computed_plan = None
        state.forecast_reference = None
        state.selected_recovery_intervention_id = None
        state.plan_status = 'not_computed'
        state.plan_error = None

    async def recompute(self, session_id, body, catalog, service, solve_lock, *, confirmed_input_revision=None):
        async with self.lock:
            if confirmed_input_revision is None:
                state = self.check(session_id, body.expected_revision)
            else:
                state = self.read(session_id)
                if state.input_revision != confirmed_input_revision:
                    return state
            if body.sunshine_factor is not None and body.sunshine_factor != state.sunshine_factor:
                state.input_revision += 1
                state.sunshine_factor = body.sunshine_factor
            self.invalidate(state)
            state.plan_status = 'pending'
            state.revision += 1
            generation = self.generations.get(session_id, 0) + 1
            self.generations[session_id] = generation
            self.states[session_id] = state
            snapshot = state.model_copy(deep=True)
        try:
            clinic = compile_clinic(snapshot)
            forecast = await service.get(ForecastLocation(**snapshot.location.model_dump()))
            index = next((n for n, day in enumerate(forecast.days) if day.date == snapshot.planning_date), None)
            if index is None or index > 1:
                raise PlanningError('UNSUPPORTED_FORECAST_DAY', 'Selected date is outside the supported today/tomorrow forecast.')
            day = forecast.days[index]
            if not day.simulation_supported:
                raise PlanningError('UNSUPPORTED_FORECAST_DAY', 'Selected date does not have exactly 24 supported hourly slots.')
            context = RecoveryRequest(clinic=clinic, **snapshot.location.model_dump(),
                midnight_battery_kwh=clinic.initial_battery_kwh, day='today' if index == 0 else 'tomorrow',
                sunshine_factor=snapshot.sunshine_factor)
            async with solve_lock:
                simulation = await run_in_threadpool(forecast_case, catalog, context, day, forecast, snapshot.sunshine_factor)
            recovery = None
            if body.include_recovery:
                recovery = await generate_recovery_plan(context, catalog, SnapshotService(forecast), solve_lock)
            computed = ComputedPlan(input_revision=snapshot.input_revision, generation=generation,
                computed_at=datetime.now(timezone.utc), sunshine_factor=snapshot.sunshine_factor,
                simulation=simulation, recovery=recovery)
        except Exception as exc:
            async with self.lock:
                current = self.read(session_id)
                if current.input_revision == snapshot.input_revision and self.generations[session_id] == generation:
                    current.plan_status = 'failed'
                    current.plan_error = getattr(exc, 'code', 'CALCULATION_UNAVAILABLE')
                    current.revision += 1
                    self.states[session_id] = current
                return self.read(session_id)
        async with self.lock:
            current = self.read(session_id)
            if current.input_revision != snapshot.input_revision or self.generations[session_id] != generation:
                return current  # old work can never become the current plan
            current.computed_plan, current.forecast_reference = computed, forecast
            current.timezone = forecast.timezone
            current.plan_status = 'current'
            current.revision += 1
            self.states[session_id] = current
            return current.model_copy(deep=True)

    async def select_recovery(self, session_id, body):
        async with self.lock:
            state = self.check(session_id, body.expected_revision)
            plan = state.computed_plan
            if not plan or plan.input_revision != body.input_revision or plan.generation != body.generation:
                raise PlanningError('STALE_RESULT', 'Recovery comparison is no longer current.', 409)
            if not plan.recovery or body.option_id not in {o.id for o in plan.recovery.options + [plan.recovery.existing]}:
                raise PlanningError('INVALID_REQUEST', 'Choose an option in the current recovery comparison.')
            state.selected_recovery_intervention_id = body.option_id
            state.revision += 1
            self.states[session_id] = state
            return state.model_copy(deep=True)
