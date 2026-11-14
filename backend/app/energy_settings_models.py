"""Reviewed energy settings; a present battery reading is not a day-start input."""
from datetime import datetime
from typing import Annotated, Literal
from pydantic import Field, field_validator, field_serializer
from pydantic.json_schema import SkipJsonSchema
from .models import (StrictModel, ConfigOverrides, Capacity, Energy, Power,
                     Efficiency, EffectiveConfig, hide_unset_defaults)


class BatteryReading(StrictModel):
    energy_kwh: Energy
    measured_at: datetime

    @field_validator('measured_at', mode='before')
    @classmethod
    def timestamp(cls, value):
        if isinstance(value, str):
            try:
                value = datetime.fromisoformat(value.replace('Z', '+00:00'))
            except ValueError:
                raise ValueError('Use an ISO timestamp with its timezone') from None
        if isinstance(value, datetime) and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError('A current battery reading needs an explicit timestamp timezone')
        return value


class EnergySettingsPatch(StrictModel):
    model_config = {'json_schema_extra': hide_unset_defaults}
    battery_capacity_kwh: Capacity | SkipJsonSchema[None] = None
    initial_battery_kwh: Energy | SkipJsonSchema[None] = None
    reserve_kwh: Energy | SkipJsonSchema[None] = None
    pv_capacity_kw: Power | SkipJsonSchema[None] = None
    charge_efficiency: Efficiency | SkipJsonSchema[None] = None
    discharge_efficiency: Efficiency | SkipJsonSchema[None] = None
    max_charge_kw: Power | SkipJsonSchema[None] = None
    max_discharge_kw: Power | SkipJsonSchema[None] = None

    @field_validator('battery_capacity_kwh', 'initial_battery_kwh', 'reserve_kwh',
        'pv_capacity_kw', 'charge_efficiency', 'discharge_efficiency', 'max_charge_kw',
        'max_discharge_kw', mode='before')
    @classmethod
    def no_explicit_null(cls, value):
        return ConfigOverrides.explicit_null_is_invalid(value)


class EnergySettingsProposal(StrictModel):
    @field_serializer('settings')
    def serialize_patch(self, value):
        return value.model_dump(exclude_unset=True)

    id: Annotated[str, Field(min_length=1, max_length=120)]
    status: Literal['draft', 'confirmed', 'rejected'] = 'draft'
    base_input_revision: Annotated[int, Field(ge=0)]
    settings: EnergySettingsPatch
    proposed_energy_settings: EffectiveConfig
    current_battery_reading: BatteryReading | None = None
    updates_current_battery_reading: bool = False


class CreateEnergySettingsProposal(StrictModel):
    expected_revision: Annotated[int, Field(ge=0)]
    settings: EnergySettingsPatch = Field(default_factory=EnergySettingsPatch)
    # Omission preserves the reading; explicit null clears it after review.
    current_battery_reading: BatteryReading | None = None


class UpdateEnergySettingsProposal(CreateEnergySettingsProposal):
    pass
