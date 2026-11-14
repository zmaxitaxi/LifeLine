"""Strict HTTP/configuration types mirroring contracts/api.ts."""

from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic.json_schema import SkipJsonSchema

ScenarioId = Literal['scheduling', 'normal', 'storm', 'high_demand']
RiskStatus = Literal['OK', 'RESERVE_AT_RISK', 'CRITICAL_SHORTAGE']
PlanName = Literal['baseline', 'heuristic', 'optimized']
Hour = Annotated[int, Field(ge=0, le=23)]
Boundary = Annotated[int, Field(ge=0, le=24)]
Capacity = Annotated[float, Field(gt=0, le=200)]
Energy = Annotated[float, Field(ge=0)]
Power = Annotated[float, Field(ge=0, le=100)]
Efficiency = Annotated[float, Field(gt=0, le=1)]
ExtraPower = Annotated[float, Field(ge=0, le=10)]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True, allow_inf_nan=False)


class EffectiveConfig(StrictModel):
    battery_capacity_kwh: Capacity
    initial_battery_kwh: Energy
    reserve_kwh: Energy
    pv_capacity_kw: Power
    charge_efficiency: Efficiency
    discharge_efficiency: Efficiency
    max_charge_kw: Power
    max_discharge_kw: Power
    additional_critical_kw: ExtraPower

    @model_validator(mode='after')
    def battery_bounds(self):
        if self.initial_battery_kwh > self.battery_capacity_kwh:
            raise ValueError('initial_battery_kwh must not exceed battery_capacity_kwh')
        if self.reserve_kwh > self.battery_capacity_kwh:
            raise ValueError('reserve_kwh must not exceed battery_capacity_kwh')
        return self


def hide_unset_defaults(schema):
    # None is an internal sentinel for omitted overrides, not an accepted JSON
    # value or an advertised default. Defaults depend on the selected preset.
    for field in schema.get('properties', {}).values():
        if field.get('default', 'absent') is None:
            field.pop('default')


class ConfigOverrides(StrictModel):
    model_config = ConfigDict(json_schema_extra=hide_unset_defaults)
    battery_capacity_kwh: Capacity | SkipJsonSchema[None] = None
    initial_battery_kwh: Energy | SkipJsonSchema[None] = None
    reserve_kwh: Energy | SkipJsonSchema[None] = None
    pv_capacity_kw: Power | SkipJsonSchema[None] = None
    charge_efficiency: Efficiency | SkipJsonSchema[None] = None
    discharge_efficiency: Efficiency | SkipJsonSchema[None] = None
    max_charge_kw: Power | SkipJsonSchema[None] = None
    max_discharge_kw: Power | SkipJsonSchema[None] = None
    additional_critical_kw: ExtraPower | SkipJsonSchema[None] = None

    @field_validator('*', mode='before')
    @classmethod
    def explicit_null_is_invalid(cls, value):
        if value is None:
            raise ValueError('Omit a field to use its preset default; null is not accepted')
        return value


class HealthResponse(StrictModel):
    status: Literal['ok'] = 'ok'
    api_version: Literal['1.0'] = '1.0'


class ScenarioSummary(StrictModel):
    id: ScenarioId
    name: str
    description: str
    data_source: Literal['synthetic'] = 'synthetic'
    defaults: EffectiveConfig
    expected_status: RiskStatus
    equipment: list['Equipment']
    cloud_factors: list[float]


class ScenarioListResponse(StrictModel):
    api_version: Literal['1.0'] = '1.0'
    scenarios: list[ScenarioSummary]


class RequestedTaskAllocation(StrictModel):
    hour: Hour
    requested_kwh: Energy


class CriticalEquipment(StrictModel):
    id: Annotated[str, Field(min_length=1)]
    name: Annotated[str, Field(min_length=1)]
    category: Literal['critical']
    power_kw: Power
    required_hours: list[Hour]

    @field_validator('required_hours')
    @classmethod
    def unique_hours(cls, value):
        if len(value) != len(set(value)):
            raise ValueError('Duplicate required hours')
        return value


class FlexibleEquipment(StrictModel):
    id: Annotated[str, Field(min_length=1)]
    name: Annotated[str, Field(min_length=1)]
    category: Literal['flexible']
    max_power_kw: Annotated[float, Field(gt=0, le=100)]
    required_energy_kwh: Energy
    allowed_hours: Annotated[list[Hour], Field(min_length=1)]
    baseline_allocations: list[RequestedTaskAllocation]
    divisible: Literal[True]

    @field_validator('divisible', mode='before')
    @classmethod
    def explicitly_divisible(cls, value):
        if value is not True:
            raise ValueError('Only explicitly divisible flexible tasks are modeled')
        return value

    @model_validator(mode='after')
    def valid_schedule(self):
        if len(self.allowed_hours) != len(set(self.allowed_hours)):
            raise ValueError('Duplicate allowed hours')
        hours = [a.hour for a in self.baseline_allocations]
        if len(hours) != len(set(hours)):
            raise ValueError('Duplicate baseline allocation hours')
        for allocation in self.baseline_allocations:
            if allocation.hour not in self.allowed_hours or allocation.requested_kwh > self.max_power_kw:
                raise ValueError('Baseline allocation outside task window or power limit')
        if sum(a.requested_kwh for a in self.baseline_allocations) > self.required_energy_kwh + 1e-6:
            raise ValueError('Baseline requests more energy than the task requires')
        return self


Equipment = Annotated[CriticalEquipment | FlexibleEquipment, Field(discriminator='category')]


class SimulationRequest(ConfigOverrides):
    scenario: ScenarioId
    equipment: Annotated[list[Equipment], Field(max_length=20)] | SkipJsonSchema[None] = None
    cloud_factors: Annotated[list[Annotated[float, Field(ge=0, le=1)]], Field(min_length=24, max_length=24)] | SkipJsonSchema[None] = None
    weather_dataset: Literal["synthetic", "kisumu-2025-01-14"] = "synthetic"

    @model_validator(mode='after')
    def clinic_overrides(self):
        if 'additional_critical_kw' in self.model_fields_set and self.scenario != 'high_demand':
            raise ValueError('additional_critical_kw can only be overridden for high_demand')
        if self.equipment is not None:
            ids = [item.id for item in self.equipment]
            if len(set(ids)) != len(ids):
                raise ValueError('Equipment IDs must be unique')
            if self.additional_critical_kw not in (None, 0):
                raise ValueError('With custom equipment, define additional loads explicitly in the equipment list')
        return self


class TaskAllocation(StrictModel):
    hour: Hour
    served_kwh: float


class FlexibleTaskResult(StrictModel):
    task_id: str
    requested_kwh: float
    served_kwh: float
    deferred_kwh: float
    allocations: list[TaskAllocation]


class HourlyResult(StrictModel):
    hour: Hour
    pv_kwh: float
    critical_requested_kwh: float
    critical_served_kwh: float
    critical_unserved_kwh: float
    flexible_planned_kwh: float
    flexible_served_kwh: float
    flexible_unserved_kwh: float
    charge_input_kwh: float
    discharge_output_kwh: float
    curtailed_kwh: float
    soc_start_kwh: float
    soc_end_kwh: float


class PlanMetrics(StrictModel):
    total_solar_kwh: float
    critical_requested_kwh: float
    critical_unserved_kwh: float
    critical_coverage_pct: float | None
    min_soc_kwh: float
    final_soc_kwh: float
    flexible_requested_kwh: float
    flexible_served_kwh: float
    flexible_deferred_kwh: float
    curtailed_kwh: float
    conversion_loss_kwh: float
    critical_shortage_hours: list[Hour]
    reserve_breach_boundaries: list[Boundary]


class PlanResult(StrictModel):
    status: RiskStatus
    hourly: Annotated[list[HourlyResult], Field(min_length=24, max_length=24)]
    metrics: PlanMetrics
    flexible_tasks: list[FlexibleTaskResult]

    @field_validator('hourly')
    @classmethod
    def ordered_hours(cls, value):
        if [r.hour for r in value] != list(range(24)):
            raise ValueError('Hourly results must be ordered slots 0 through 23')
        return value


class ComparisonMetrics(StrictModel):
    same_flexible_work_completed: bool
    battery_preserved_at_midnight_kwh: float
    minimum_battery_improvement_kwh: float
    evening_minimum_improvement_kwh: float
    conversion_loss_reduction_kwh: float
    heuristic_matches_optimizer_metrics: bool


class SimulationWarning(StrictModel):
    code: Literal['CRITICAL_UNSERVED', 'RESERVE_BELOW_TARGET', 'FLEXIBLE_DEFERRED']
    plan: PlanName
    message: str


class Recommendation(StrictModel):
    severity: Literal['info', 'warning', 'critical']
    title: str
    explanation: str
    task_id: str | None = None
    hours: list[Hour] | None = None


class Diagnosis(StrictModel):
    assessment: str
    explanation: str
    constraints: list[str]
    discharge_limited_hours: list[Hour]
    optimistic_energy_deficit_kwh: float
    window_limited_tasks: list[str]


class SimulationResponse(StrictModel):
    api_version: Literal['1.0'] = '1.0'
    model_version: Literal['energy-1.0'] = 'energy-1.0'
    scenario: ScenarioId
    scenario_name: str
    data_source: Literal['synthetic', 'user_defined', 'mixed'] = 'synthetic'
    cloud_factors: list[float]
    input_provenance: dict[str, str]
    weather_dataset: str
    diagnosis: Diagnosis
    timezone: str = 'Africa/Nairobi'
    horizon_hours: Literal[24] = 24
    dt_hours: Literal[1] = 1
    pv_performance_ratio: Efficiency
    effective_config: EffectiveConfig
    equipment: list[Equipment]
    assumptions: list[str]
    status: RiskStatus
    baseline: PlanResult
    heuristic: PlanResult
    optimized: PlanResult
    comparison: ComparisonMetrics
    warnings: list[SimulationWarning]
    recommendations: list[Recommendation]

    @model_validator(mode='after')
    def consistent_status(self):
        if self.status != self.optimized.status:
            raise ValueError('Top-level status must match the optimized plan')
        return self


class ErrorDetail(StrictModel):
    loc: list[str | int]
    message: str
    type: str


class ErrorBody(StrictModel):
    code: Literal['INVALID_REQUEST', 'SOLVER_UNAVAILABLE', 'SOLVER_TIME_LIMIT', 'NUMERICAL_ERROR', 'INTERNAL_ERROR',
                  'FORECAST_UNAVAILABLE', 'FORECAST_DATA_INVALID', 'UNSUPPORTED_FORECAST_DAY', 'AGENT_UNAVAILABLE',
                  'RECOVERY_TIME_LIMIT', 'REVISION_CONFLICT', 'PROPOSAL_INCOMPLETE', 'INVALID_ACTIVITY', 'INVALID_ENERGY_SETTINGS',
                  'PROPOSAL_CLOSED', 'IDEMPOTENCY_CONFLICT', 'STALE_RESULT', 'NOT_FOUND']
    message: str
    details: list[ErrorDetail] = Field(default_factory=list)


class ApiErrorResponse(StrictModel):
    error: ErrorBody

ScenarioSummary.model_rebuild()
