"""Native reviewed settings tools; Python owns unit and percentage conversion."""
import json
import re
from datetime import datetime, timezone
from typing import Annotated
from pydantic import Field
from .energy_settings_models import (EnergySettingsPatch, BatteryReading,
    CreateEnergySettingsProposal, UpdateEnergySettingsProposal)
from .planning_state import PlanningError


class NativeEnergySettings(EnergySettingsPatch):
    initial_battery_pct: Annotated[float, Field(ge=0, le=100)] | None = None
    current_battery_pct: Annotated[float, Field(ge=0, le=100)] | None = None
    current_battery_reading: BatteryReading | None = None


def energy_definitions(state):
    # Flatten $refs for llama3.1's native template, as for activity schemas.
    schema = NativeEnergySettings.model_json_schema()
    definitions = schema.pop('$defs', {})
    def inline(value):
        if isinstance(value, list):
            return [inline(item) for item in value]
        if isinstance(value, dict):
            if '$ref' in value:
                return inline(definitions[value['$ref'].rsplit('/', 1)[-1]])
            return {key: inline(item) for key, item in value.items() if key not in ('title', 'default')}
        return value
    tools = [dict(name='propose_energy_settings', description=(
        'Stage ONLY explicitly supplied clinic energy settings for operator review. '
        'Does not adopt or install hardware. Omitted fields preserve current values. '
        'initial_battery_kwh or initial_battery_pct is the explicit selected-day midnight assumption; '
        'current_battery_reading or current_battery_pct is separate and never becomes starting energy. '
        'For a current percentage Python records the actual receipt time. Never calculate kWh or infer ratings. '
        'Use percentage fields when the operator supplied percentages. Use recompute for hypothetical energy comparisons.'),
        parameters=inline(schema))]
    if state.active_energy_proposal_id:
        tools.append(dict(name='update_energy_settings_draft',
            description='Patch only explicitly changed energy facts in the SAME active settings draft. Confirmation remains an explicit operator action.',
            parameters=inline(schema)))
    return tools


PATTERNS = {
    'battery_capacity_kwh': r'\b(?:battery|storage)\b.*\bcapacity\b|\bcapacity\b.*\b(?:battery|storage)\b',
    'initial_battery_kwh': r'\b(?:initial|starting|start|midnight|day.beginning)\b',
    'initial_battery_pct': r'\b(?:initial|starting|start|midnight|day.beginning)\b',
    'reserve_kwh': r'\breserve\b',
    'pv_capacity_kw': r'\b(?:solar|panels?|pv|photovoltaic)\b',
    'charge_efficiency': r'\b(?:charg(?:e|ing)|charge_efficiency)\b.*\befficiency\b',
    'discharge_efficiency': r'\b(?:discharg(?:e|ing)|discharge_efficiency)\b.*\befficiency\b',
    'max_charge_kw': r'\b(?:charg(?:e|ing)|max_charge_kw)\b',
    'max_discharge_kw': r'\b(?:discharg(?:e|ing)|inverter|output|max_discharge_kw)\b',
    'current_battery_pct': r'\b(?:current(?:ly)?|now|present|reading)\b',
    'current_battery_reading': r'\b(?:current(?:ly)?|now|present|reading)\b',
}


def stated_quantity(question, field, value):
    clauses = re.split(r'\band\b|[;!?]|\.(?!\d)', question, flags=re.I)
    unit = ('pct' if field.endswith('_pct') else 'efficiency' if field.endswith('_efficiency') else
            'energy' if field.endswith('_kwh') or field == 'current_battery_reading' else 'power')
    for clause in clauses:
        if not re.search(PATTERNS[field], clause, re.I):
            continue
        for match in re.finditer(r'(?<![\w.])(\d+(?:\.\d+)?)\s*((?:kwh|wh|kilowatt[ -]?hours?|watt[ -]?hours?|kw|kilowatts?|watts?|w|percent|%)(?!\w))?', clause, re.I):
            raw = float(match[1])
            suffix = (match[2] or '').lower().replace(' ', '').replace('-', '')
            if unit == 'pct' and suffix in ('%', 'percent'):
                actual = raw
            elif unit == 'efficiency' and suffix in ('%', 'percent', ''):
                actual = raw / 100 if suffix else raw
            elif unit == 'energy' and suffix in ('kwh', 'kilowatthour', 'kilowatthours', 'wh', 'watthour', 'watthours'):
                actual = raw / 1000 if suffix in ('wh', 'watthour', 'watthours') else raw
            elif unit == 'power' and suffix in ('kw', 'kilowatt', 'kilowatts', 'w', 'watt', 'watts'):
                actual = raw / 1000 if suffix in ('w', 'watt', 'watts') else raw
            else:
                continue
            if abs(actual - value) < 1e-8:
                return True
    return False


async def apply_energy_tool(name, arguments, question, state, store):
    values = dict(arguments)
    # Narrow native-template compatibility only. HTTP schemas remain strict.
    for key in NativeEnergySettings.model_fields:
        if isinstance(values.get(key), str):
            try:
                values[key] = json.loads(values[key])
            except ValueError:
                pass
    draft = NativeEnergySettings.model_validate(values)
    supplied = draft.model_dump(exclude_unset=True)
    patch = {key: value for key, value in supplied.items() if key in EnergySettingsPatch.model_fields}
    for field, value in patch.items():
        if not stated_quantity(question, field, value):
            raise PlanningError('INVALID_ENERGY_SETTINGS', f'{field} needs an explicitly supplied value and unit in the current request.')
    capacity = patch.get('battery_capacity_kwh', state.energy_settings.battery_capacity_kwh)
    if name == 'update_energy_settings_draft' and state.active_energy_proposal_id:
        prior = store.energy_proposal(state, state.active_energy_proposal_id)
        capacity = patch.get('battery_capacity_kwh', prior.proposed_energy_settings.battery_capacity_kwh)
    if draft.initial_battery_pct is not None:
        if 'initial_battery_kwh' in patch or not stated_quantity(question, 'initial_battery_pct', draft.initial_battery_pct):
            raise PlanningError('INVALID_ENERGY_SETTINGS', 'Supply one explicit starting energy or starting percentage; Python converts the percentage.')
        patch['initial_battery_kwh'] = capacity * draft.initial_battery_pct / 100
    extra = {}
    if draft.current_battery_pct is not None:
        if 'current_battery_reading' in supplied or not stated_quantity(question, 'current_battery_pct', draft.current_battery_pct):
            raise PlanningError('INVALID_ENERGY_SETTINGS', 'Supply one explicit current percentage or a timestamped current reading.')
        extra['current_battery_reading'] = BatteryReading(energy_kwh=capacity * draft.current_battery_pct / 100,
            measured_at=datetime.now(timezone.utc))
    elif 'current_battery_reading' in supplied:
        reading = draft.current_battery_reading
        if reading is None:
            if not re.search(r'\b(?:clear|remove|delete|forget)\b.*\b(?:current|reading|measurement)\b', question, re.I):
                raise PlanningError('INVALID_ENERGY_SETTINGS', 'Clearing a current reading needs an explicit request.')
        elif not stated_quantity(question, 'current_battery_reading', reading.energy_kwh) or not any(
            token in question for token in (reading.measured_at.isoformat(), reading.measured_at.isoformat().replace('+00:00', 'Z'))):
            raise PlanningError('INVALID_ENERGY_SETTINGS', 'A timestamped current reading needs the explicitly supplied energy and timestamp.')
        extra['current_battery_reading'] = reading
    body = CreateEnergySettingsProposal(expected_revision=state.revision,
        settings=EnergySettingsPatch.model_validate(patch), **extra)
    if name == 'update_energy_settings_draft':
        if not state.active_energy_proposal_id:
            raise PlanningError('INVALID_ENERGY_SETTINGS', 'There is no active settings draft to update.')
        return await store.update_energy(state.id, state.active_energy_proposal_id,
            UpdateEnergySettingsProposal.model_validate(body.model_dump(exclude_unset=True)))
    return await store.propose_energy(state.id, body)
