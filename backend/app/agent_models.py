"""Contracts for local AI tool selection and model-computed answers."""
from typing import Annotated, Literal
from pydantic import Field, model_validator
from .forecast_models import PlannerContext, PlanForecastArguments, ForecastPlanResponse
from .models import StrictModel


class AgentRequest(PlannerContext):
    question: Annotated[str, Field(min_length=1, max_length=2000)]
    previous_questions: Annotated[list[Annotated[str, Field(min_length=1, max_length=2000)]], Field(max_length=8)] = []
    inputs_confirmed: bool = False
    input_basis: Literal['synthetic_example', 'operator_entered_unverified'] = 'synthetic_example'
    day: Literal['today', 'tomorrow'] = 'tomorrow'


class FixedRequirementArguments(StrictModel):
    day: Literal['today', 'tomorrow'] = 'tomorrow'
    name: Annotated[str, Field(min_length=1, max_length=120)]
    power_kw: Annotated[float, Field(gt=0, le=100)]
    duration_hours: Annotated[int, Field(ge=1, le=24)]
    earliest_start: Annotated[int, Field(ge=0, le=23)]
    deadline: Annotated[int, Field(ge=1, le=24)]

    @model_validator(mode='after')
    def fits_window(self):
        if self.earliest_start + self.duration_hours > self.deadline:
            raise ValueError('Consecutive operating duration does not fit before the deadline')
        return self


class CapacityArguments(StrictModel):
    day: Literal['today', 'tomorrow'] = 'tomorrow'
    sunshine_factor: Annotated[float, Field(ge=0, le=1)] = 1.
    target: Literal['essential', 'all_work'] = 'all_work'


class ClarifyArguments(StrictModel):
    field: Literal['power', 'duration', 'earliest_start', 'deadline', 'equipment', 'midnight_battery', 'intent', 'cycle_constraints', 'day']


class ToolTrace(StrictModel):
    name: str
    status: Literal['completed', 'rejected', 'unavailable']


class CapacitySample(StrictModel):
    battery_capacity_kwh: float
    essential_unmet_kwh: float
    flexible_deferred_kwh: float
    minimum_battery_kwh: float
    reserve_breached: bool
    meets_target: bool


class CapacityResult(StrictModel):
    target: Literal['essential', 'all_work']
    sunshine_factor: float
    current_capacity_kwh: float
    tested_capacity_kwh: float | None
    additional_capacity_kwh: float | None
    resolution_kwh: float
    search_limit_kwh: float
    samples: list[CapacitySample]
    explanation: str
    assumptions: list[str]


class RequirementResult(StrictModel):
    name: str
    start_hour: int
    end_hour: int
    candidates_evaluated: int
    essential_requirements_fully_supplied: bool
    original: ForecastPlanResponse
    proposed: ForecastPlanResponse
    explanation: str


class AgentResponse(StrictModel):
    mode: Literal['local_tool_agent', 'deterministic_guided_fallback']
    model: str | None = None
    message: str
    needs_clarification: bool
    clarification_field: str | None = None
    tool_calls: list[ToolTrace]
    result: ForecastPlanResponse | None = None
    requirement: RequirementResult | None = None
    capacity: CapacityResult | None = None
    fallback_reason: str | None = None
    input_basis: Literal['synthetic_example', 'operator_entered_unverified']
    selected_sunshine_factor: float = 1.
