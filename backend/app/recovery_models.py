"""Read-only recovery comparisons, with explicit changes and comparable work."""
from datetime import date
from typing import Annotated, Literal
from pydantic import Field, field_validator
from .forecast_models import PlannerContext, SolarForecast
from .models import EffectiveConfig, PlanResult, SimulationResponse, StrictModel


class RecoveryArguments(StrictModel):
    day: Literal['today', 'tomorrow'] = 'tomorrow'
    focus: Literal['all', 'scheduling', 'solar', 'battery', 'output', 'optional', 'backup'] = 'all'
    sunshine_factor: Annotated[float, Field(ge=0, le=1)] = 1.


class RecoveryRequest(PlannerContext, RecoveryArguments):
    weather_mode: Literal['live_forecast', 'existing_scenario'] = 'live_forecast'
    optional_load_ids: Annotated[list[str], Field(max_length=20)] = []

    @field_validator('optional_load_ids')
    @classmethod
    def unique_ids(cls, values):
        if len(values) != len(set(values)):
            raise ValueError('Optional load IDs must be unique')
        return values


class InfrastructureChange(StrictModel):
    field: Literal['pv_capacity_kw', 'battery_capacity_kwh', 'max_discharge_kw']
    before: float
    after: float
    unit: Literal['kW', 'kWh']


class WorkChange(StrictModel):
    equipment_id: str
    name: str
    original_required_kwh: float
    tested_required_kwh: float
    explicitly_postponed_kwh: float


class BackupDeficit(StrictModel):
    hour: int
    electrical_energy_kwh: float


class RecoveryMetrics(StrictModel):
    essential_requested_kwh: float
    essential_served_kwh: float
    essential_unserved_kwh: float
    original_flexible_required_kwh: float
    tested_flexible_required_kwh: float
    flexible_completed_kwh: float
    flexible_unfinished_kwh: float
    explicitly_postponed_kwh: float
    minimum_battery_kwh: float
    reserve_shortfall_kwh: float
    reserve_breach_boundaries: list[int]
    conversion_losses_kwh: float


class RecoveryOption(StrictModel):
    id: str
    label: str
    kind: Literal['existing', 'scheduling', 'solar', 'battery', 'output', 'optional']
    rank: int | None = None
    config: EffectiveConfig
    plan: PlanResult
    simulation: SimulationResponse
    metrics: RecoveryMetrics
    infrastructure_changes: list[InfrastructureChange]
    work_changes: list[WorkChange]
    essential_shortage_reduction_kwh: float
    minimum_battery_improvement_kwh: float
    flexible_completion_improvement_kwh: float
    normalized_change_magnitude: float
    modeled_essential_and_reserve_met: bool
    modeled_all_requirements_met: bool
    backup_deficits: list[BackupDeficit]
    remaining_constraints: list[str]


class RecoveryResponse(StrictModel):
    weather_mode: Literal['live_forecast', 'existing_scenario']
    forecast: SolarForecast | None = None
    planning_date: date | None = None
    timezone: str
    sunshine_factor: float
    reference: SimulationResponse
    existing: RecoveryOption
    options: list[RecoveryOption]
    problem_detected: bool
    triggers: list[str]
    recommended_option_id: str
    operational_option_id: str = 'reschedule'
    smallest_tested_resolving_option_id: str | None
    summary: str
    next_action: str
    assumptions: list[str]
    limitations: list[str]
