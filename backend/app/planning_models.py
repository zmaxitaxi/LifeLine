"""Revisioned local planning contracts. Drafts are partial; confirmed facts are strict."""
from datetime import date, datetime
from typing import Annotated, Literal
from pydantic import Field, model_validator, field_validator, field_serializer
import re
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from .models import StrictModel, SimulationRequest, Equipment, Hour, Boundary, EffectiveConfig
from .energy_settings_models import BatteryReading, EnergySettingsProposal
from .forecast_models import ForecastLocation, SolarForecast
from .models import SimulationResponse
from .recovery_models import RecoveryResponse

ID = Annotated[str, Field(min_length=1, max_length=120)]
Revision = Annotated[int, Field(ge=0)]


class EquipmentConstraint(StrictModel):
    equipment_id: ID
    # Reference-only associations add no electrical demand. Explicit constraints
    # extend critical hours or narrow divisible flexible windows, never ratings.
    required_hours: list[Hour] | None = None
    allowed_hours: list[Hour] | None = None
    @model_validator(mode='after')
    def one_kind(self):
        if self.required_hours is not None and self.allowed_hours is not None:
            raise ValueError('Use required_hours or allowed_hours, not both')
        for values in (self.required_hours, self.allowed_hours):
            if values is not None and (not values or len(values) != len(set(values))):
                raise ValueError('Constraint hours must be nonempty and unique')
        return self


class ProposedEquipment(StrictModel):
    id: ID
    name: Annotated[str, Field(min_length=1, max_length=120)]
    category: Literal['critical', 'flexible'] | None = None
    power_kw: Annotated[float, Field(gt=0, le=100)] | None = None
    required_hours: list[Hour] | None = None
    max_power_kw: Annotated[float, Field(gt=0, le=100)] | None = None
    required_energy_kwh: Annotated[float, Field(gt=0)] | None = None
    required_duration_hours: Annotated[int, Field(ge=1, le=24)] | None = None
    allowed_hours: list[Hour] | None = None
    divisible: Literal[True] | None = None

    @model_validator(mode='after')
    def consistent_rated_duration(self):
        if self.category=='flexible' and self.max_power_kw is not None and self.required_duration_hours is not None and self.required_energy_kwh is not None:
            if abs(self.required_energy_kwh-self.max_power_kw*self.required_duration_hours)>1e-6:
                raise ValueError('Energy must agree with the explicitly supplied rated power and operating duration')
        if self.category=='critical' and self.required_duration_hours is not None and self.required_hours is not None:
            if len(self.required_hours)!=self.required_duration_hours:
                raise ValueError('Fixed required hours must agree with the explicitly supplied duration')
        return self


class ActivityDraft(StrictModel):
    @field_validator('planning_date', mode='before')
    @classmethod
    def iso_date(cls, value):
        if isinstance(value, str) and re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
            return date.fromisoformat(value)
        return value

    name: Annotated[str, Field(min_length=1, max_length=120)] | None = None
    planning_date: date | None = None
    start_hour: Hour | None = None
    end_hour: Boundary | None = None
    deadline_hour: Boundary | None = None
    duration_hours: Annotated[int, Field(ge=1, le=24)] | None = None
    # None means not reviewed; [] explicitly means no equipment requirement.
    equipment_ids: list[ID] | None = None
    equipment_constraints: list[EquipmentConstraint] = []
    additional_equipment: list[ProposedEquipment] = []
    @model_validator(mode='after')
    def valid_window(self):
        if self.start_hour is not None and self.end_hour is not None and self.start_hour >= self.end_hour:
            raise ValueError('Activity start must be earlier than end')
        end = self.deadline_hour if self.deadline_hour is not None else self.end_hour
        if end is not None and self.start_hour is not None and self.duration_hours is not None and self.start_hour + self.duration_hours > end:
            raise ValueError('Required duration cannot fit before the deadline')
        if self.end_hour is not None and self.deadline_hour is not None and self.end_hour > self.deadline_hour:
            raise ValueError('Activity end exceeds completion deadline')
        if self.equipment_ids is not None and len(self.equipment_ids) != len(set(self.equipment_ids)):
            raise ValueError('Equipment references must be unique')
        return self


class Activity(StrictModel):
    id: ID
    version: Annotated[int, Field(ge=1)]
    status: Literal['confirmed'] = 'confirmed'
    details: ActivityDraft


class ActivityProposal(StrictModel):
    id: ID
    status: Literal['draft', 'confirmed', 'rejected'] = 'draft'
    target_activity_id: ID | None = None
    base_activity_version: int | None = None
    details: ActivityDraft
    missing_fields: list[str] = []
    confirmed_activity_id: ID | None = None


class ComputedPlan(StrictModel):
    input_revision: Revision
    generation: Annotated[int, Field(ge=1)]
    computed_at: datetime
    sunshine_factor: float
    simulation: SimulationResponse
    recovery: RecoveryResponse | None = None


class PlanningState(StrictModel):
    @field_serializer('clinic')
    def serialize_clinic(self, clinic):
        # SimulationRequest uses None internally for omitted preset overrides;
        # explicit null is intentionally invalid in its public request schema.
        return clinic.model_dump(exclude_none=True)

    id: ID
    revision: Revision
    input_revision: Revision
    selected_clinic_id: ID
    clinic_name: str
    location: ForecastLocation
    planning_date: date
    timezone: str | None = None
    clinic: SimulationRequest
    equipment_inventory: list[Equipment]
    energy_settings: EffectiveConfig
    current_battery_reading: BatteryReading | None = None
    energy_proposals: list[EnergySettingsProposal] = []
    active_energy_proposal_id: ID | None = None
    confirmed_activities: list[Activity] = []
    proposals: list[ActivityProposal] = []
    active_proposal_id: ID | None = None
    forecast_reference: SolarForecast | None = None
    computed_plan: ComputedPlan | None = None
    plan_status: Literal['not_computed', 'pending', 'current', 'failed'] = 'not_computed'
    plan_error: str | None = None
    selected_recovery_intervention_id: str | None = None
    sunshine_factor: Annotated[float, Field(ge=0, le=1)] = 1.


class CreatePlanningSession(StrictModel):
    @field_validator('planning_date', mode='before')
    @classmethod
    def iso_date(cls, value):
        return ActivityDraft.iso_date(value)

    selected_clinic_id: ID
    clinic_name: Annotated[str, Field(min_length=1, max_length=120)]
    location: ForecastLocation
    planning_date: date
    clinic: SimulationRequest
    # Never derive a midnight assumption from a current reading.
    midnight_battery_kwh: Annotated[float, Field(ge=0)]
    current_battery_reading: BatteryReading | None = None
    timezone: str | None = None

    @field_validator('timezone')
    @classmethod
    def known_timezone(cls, value):
        if value is not None:
            try:
                ZoneInfo(value)
            except (ZoneInfoNotFoundError, ValueError):
                raise ValueError('Use a valid IANA clinic timezone') from None
        return value


class RevisionRequest(StrictModel):
    expected_revision: Revision


class CreateActivityProposal(RevisionRequest):
    details: ActivityDraft
    target_activity_id: ID | None = None


class UpdateActivityProposal(RevisionRequest):
    # Partial patch: omitted keys preserve the previous draft; null clears one.
    details: ActivityDraft


class ConfirmActivityProposal(RevisionRequest):
    idempotency_key: ID


class RejectActivityProposal(RevisionRequest):
    pass


class RecomputePlanningState(RevisionRequest):
    sunshine_factor: Annotated[float, Field(ge=0, le=1)] | None = None
    include_recovery: bool = False


class SelectRecoveryIntervention(RevisionRequest):
    input_revision: Revision
    generation: Annotated[int, Field(ge=1)]
    option_id: ID


class SessionAgentRequest(RevisionRequest):
    question: Annotated[str, Field(min_length=1, max_length=2000)]


class AgentPresentation(StrictModel):
    kind: Literal['conversation', 'activity_review', 'energy_review', 'calculation', 'explanation'] = 'conversation'
    input_revision: Revision | None = None
    generation: Annotated[int, Field(ge=1)] | None = None
    option_ids: list[ID] = []
    show_schedule: bool = False


class PlanningMessage(StrictModel):
    id: ID
    role: Literal['user', 'assistant']
    content: Annotated[str, Field(min_length=1, max_length=12000)]
    created_at: datetime
    presentation: AgentPresentation | None = None
    mode: Literal['local_tool_agent', 'local_agent_unavailable'] | None = None


class PlanningConversation(StrictModel):
    session_id: ID
    messages: list[PlanningMessage] = []


class SessionAgentResponse(StrictModel):
    mode: Literal['local_tool_agent', 'local_agent_unavailable']
    model: str | None = None
    message: str
    needs_clarification: bool
    clarification_fields: list[str] = []
    tool_calls: list[str] = []
    presentation: AgentPresentation = Field(default_factory=AgentPresentation)
    message_id: ID | None = None
    user_message_id: ID | None = None
    state: PlanningState
