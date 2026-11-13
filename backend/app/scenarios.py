"""Validate bundled inputs at startup; resolve HTTP overrides into the existing model."""

from dataclasses import fields
import json
from pathlib import Path
from typing import Annotated, Literal
from pydantic import Field, field_validator, model_validator
from .energy_types import BatteryConfig, FlexibleTask, ModelInput
from .models import (ConfigOverrides, CriticalEquipment, EffectiveConfig, FlexibleEquipment,
                     Hour, RiskStatus, ScenarioId, SimulationRequest, StrictModel)
from .solar_forecast import forecast_solar

CONFIG_PATH = Path(__file__).resolve().parents[2] / 'contracts/scenarios.json'


class PVModel(StrictModel):
    sunrise_hour: Literal[6]
    sunset_hour: Literal[18]
    performance_ratio: Annotated[float, Field(gt=0, le=1)]

    @field_validator('sunrise_hour', 'sunset_hour', mode='before')
    @classmethod
    def integer_hours(cls, value):
        if type(value) is not int:
            raise ValueError('Daylight hours must be integer clock values')
        return value


class ScenarioPreset(StrictModel):
    id: ScenarioId
    name: str
    description: str
    overrides: ConfigOverrides
    cloud_factors: Annotated[list[Annotated[float, Field(ge=0, le=1)]], Field(min_length=24, max_length=24)]
    additional_critical_hours: list[Hour]
    expected_status: RiskStatus
    reference_checks: dict[str, float] | None = None

    @model_validator(mode='after')
    def additional_load(self):
        if len(set(self.additional_critical_hours)) != len(self.additional_critical_hours):
            raise ValueError('Duplicate additional load hours')
        if self.id != 'high_demand' and (self.additional_critical_hours or 'additional_critical_kw' in self.overrides.model_fields_set):
            raise ValueError('Additional load is reserved for high_demand')
        if self.id == 'high_demand' and not self.additional_critical_hours:
            raise ValueError('High Demand must specify additional load hours')
        return self


class ScenarioCatalog(StrictModel):
    schema_version: Literal['1.0']
    provenance: str
    timezone: Literal['Africa/Nairobi']
    horizon_hours: Literal[24]
    dt_hours: Literal[1]
    pv_model: PVModel
    defaults: EffectiveConfig
    critical_equipment: list[CriticalEquipment]
    flexible_equipment: list[FlexibleEquipment]
    scenarios: list[ScenarioPreset]

    @field_validator('horizon_hours', 'dt_hours', mode='before')
    @classmethod
    def integer_time_settings(cls, value):
        if type(value) is not int:
            raise ValueError('Horizon and time step must be integer hours')
        return value

    @model_validator(mode='after')
    def validate_catalog(self):
        ids = [s.id for s in self.scenarios]
        if len(ids) != 4 or set(ids) != {'scheduling', 'normal', 'storm', 'high_demand'}:
            raise ValueError('Exactly four unique scenario IDs are required')
        equipment_ids = [e.id for e in self.critical_equipment + self.flexible_equipment]
        if len(set(equipment_ids)) != len(equipment_ids) or 'additional_protected_load' in equipment_ids:
            raise ValueError('Equipment IDs must be unique; additional_protected_load is reserved')
        if self.defaults.additional_critical_kw != 0:
            raise ValueError('Common additional demand must be zero')
        for preset in self.scenarios:
            # Fail startup on invalid merged defaults, rather than discovering
            # configuration defects during a request or silently clamping them.
            self.resolve(SimulationRequest(scenario=preset.id))
        return self

    def preset(self, scenario_id):
        return next(s for s in self.scenarios if s.id == scenario_id)

    def resolve(self, request: SimulationRequest) -> EffectiveConfig:
        preset = self.preset(request.scenario)
        overrides = request.model_dump(exclude_unset=True, exclude={'scenario'})
        return EffectiveConfig.model_validate(self.defaults.model_dump()
            | preset.overrides.model_dump(exclude_unset=True) | overrides)

    def equipment_for(self, request, config):
        equipment = list(self.critical_equipment) + list(self.flexible_equipment)
        if request.scenario == 'high_demand':
            equipment.append(CriticalEquipment(id='additional_protected_load',
                name='Additional operator-protected load (synthetic)', category='critical',
                power_kw=config.additional_critical_kw,
                required_hours=self.preset(request.scenario).additional_critical_hours))
        return equipment

    def build_inputs(self, request, config):
        preset = self.preset(request.scenario)
        battery = BatteryConfig(**{f.name: getattr(config, f.name) for f in fields(BatteryConfig)})
        pv = forecast_solar(config.pv_capacity_kw, preset.cloud_factors, self.pv_model.performance_ratio)
        critical = [0.] * 24
        tasks = []
        for equipment in self.equipment_for(request, config):
            if equipment.category == 'critical':
                for h in equipment.required_hours:
                    critical[h] += equipment.power_kw
            else:
                baseline = [0.] * 24
                for allocation in equipment.baseline_allocations:
                    baseline[allocation.hour] = allocation.requested_kwh
                tasks.append(FlexibleTask(equipment.id, equipment.required_energy_kwh,
                    equipment.max_power_kw, tuple(equipment.allowed_hours), tuple(baseline)))
        return ModelInput(battery, pv, tuple(critical), tuple(tasks))


def load_catalog(path: Path = CONFIG_PATH) -> ScenarioCatalog:
    # Python-mode validation deliberately rejects numeric strings and booleans.
    return ScenarioCatalog.model_validate(json.loads(path.read_text(encoding='utf-8')))
