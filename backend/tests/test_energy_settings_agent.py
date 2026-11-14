"""Native explicit-source guards preserve numerical authority in Python."""
import asyncio
import pytest
from app.energy_settings_agent import apply_energy_tool, stated_quantity
from app.planning_state import PlanningStore, PlanningError
from app.planning_models import CreatePlanningSession
from app.scenarios import load_catalog
from test_planning_state import initial


def test_native_percentages_converted_in_python_and_staged_without_adoption():
    async def run():
        store = PlanningStore()
        state = await store.create(CreatePlanningSession.model_validate_json(__import__('json').dumps(initial())), load_catalog())
        staged = await apply_energy_tool('propose_energy_settings', {
            'battery_capacity_kwh': '8', 'initial_battery_pct': 75., 'current_battery_pct': 50.},
            'Set battery capacity to 8 kWh and the starting charge to 75% and the current reading is 50%.',
            state, store)
        proposal = staged.energy_proposals[-1]
        assert proposal.proposed_energy_settings.initial_battery_kwh == 6.
        assert proposal.current_battery_reading.energy_kwh == 4.
        assert proposal.current_battery_reading.measured_at.tzinfo is not None
        assert staged.energy_settings.initial_battery_kwh == 2.
        assert staged.current_battery_reading is None
    asyncio.run(run())


@pytest.mark.parametrize('field,value,question', [
    ('initial_battery_kwh', 8., 'Set battery capacity to 8 kWh and starting charge to 2 kWh.'),
    ('battery_capacity_kwh', 2., 'Set battery capacity to 8 kWh and starting charge to 2 kWh.'),
    ('max_discharge_kw', 5., 'The solar capacity is 5 kW.'),
    ('pv_capacity_kw', 10., 'What happens tomorrow?'),
])
def test_model_cannot_swap_or_invent_settings_values(field, value, question):
    assert not stated_quantity(question, field, value)


def test_known_units_and_explicit_percent_efficiency_are_converted():
    assert stated_quantity('Set reserve to 500 Wh.', 'reserve_kwh', .5)
    assert stated_quantity('Solar capacity is 1500 W.', 'pv_capacity_kw', 1.5)
    assert stated_quantity('Charging efficiency is 95%.', 'charge_efficiency', .95)
    assert stated_quantity('Discharging efficiency is 0.9.', 'discharge_efficiency', .9)


def test_patch_same_draft_uses_its_reviewed_capacity_for_percent_and_reading_clear():
    async def run():
        store = PlanningStore()
        state = await store.create(CreatePlanningSession.model_validate_json(__import__('json').dumps(initial())), load_catalog())
        state = await apply_energy_tool('propose_energy_settings', {'battery_capacity_kwh': 8.},
            'Set battery capacity to 8 kWh.', state, store)
        pid = state.active_energy_proposal_id
        state = await apply_energy_tool('update_energy_settings_draft', {'initial_battery_pct': 50.},
            'Set the starting charge to 50%.', state, store)
        assert len(state.energy_proposals) == 1 and state.active_energy_proposal_id == pid
        assert state.energy_proposals[-1].proposed_energy_settings.initial_battery_kwh == 4.
        with pytest.raises(PlanningError):
            await apply_energy_tool('update_energy_settings_draft', {'current_battery_reading': None},
                'Hello.', state, store)
        state = await apply_energy_tool('update_energy_settings_draft', {'current_battery_reading': None},
            'Clear the current battery reading.', state, store)
        assert state.energy_proposals[-1].updates_current_battery_reading
    asyncio.run(run())
