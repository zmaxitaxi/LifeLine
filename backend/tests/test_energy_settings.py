"""Reviewed settings change the real model once, never invent stored energy."""
from copy import deepcopy
import json
import pytest
from fastapi.testclient import TestClient
from app.main import create_app
from app.planning_models import PlanningState
from test_weather_forecast import service_for
from test_planning_state import BASE, create, post, propose, confirm


def energy(client, state, settings=None, **extra):
    return post(client, f"{BASE}/{state['id']}/energy-proposals",
        {'expected_revision': state['revision'], 'settings': settings or {}} | extra)


def accept(client, state, key='settings-click'):
    return post(client, f"{BASE}/{state['id']}/energy-proposals/{state['active_energy_proposal_id']}/confirm",
        {'expected_revision': state['revision'], 'idempotency_key': key})


def test_review_confirm_preserves_absolute_start_energy_and_recalculates_once():
    service, weather = service_for()
    with TestClient(create_app(forecast_service=service)) as client:
        state = create(client)
        state = propose(client, state)
        state = confirm(client, state)
        old = deepcopy(state)
        staged = energy(client, state, {'battery_capacity_kwh': 8., 'pv_capacity_kw': 2.})
        pid = staged['active_energy_proposal_id']
        assert staged['clinic'] == old['clinic']
        assert staged['computed_plan'] == old['computed_plan']
        assert staged['energy_settings']['initial_battery_kwh'] == 2.
        proposed = staged['energy_proposals'][-1]['proposed_energy_settings']
        assert proposed['battery_capacity_kwh'] == 8. and proposed['initial_battery_kwh'] == 2.
        current = accept(client, staged)
        assert current['confirmed_activities'] == old['confirmed_activities']
        assert current['equipment_inventory'] == old['equipment_inventory']
        assert current['energy_settings']['battery_capacity_kwh'] == 8.
        assert current['computed_plan']['simulation']['effective_config']['initial_battery_kwh'] == 2.
        assert current['input_revision'] == old['input_revision'] + 1
        assert current['computed_plan']['generation'] == old['computed_plan']['generation'] + 1
        duplicate = post(client, f"{BASE}/{state['id']}/energy-proposals/{pid}/confirm",
            {'expected_revision': 0, 'idempotency_key': 'settings-click'})
        assert duplicate == current
        PlanningState.model_validate_json(json.dumps(current))


def test_timestamped_reading_never_becomes_midnight_energy_and_clear_is_reviewed():
    service, _ = service_for()
    reading = {'energy_kwh': 3.5, 'measured_at': '2026-11-14T14:25:00+03:00'}
    with TestClient(create_app(forecast_service=service)) as client:
        state = create(client)
        staged = energy(client, state, current_battery_reading=reading)
        assert staged['current_battery_reading'] is None
        state = accept(client, staged)
        assert state['current_battery_reading'] == reading
        assert state['clinic']['initial_battery_kwh'] == 2.
        assert state['computed_plan']['simulation']['effective_config']['initial_battery_kwh'] == 2.
        state = energy(client, state, current_battery_reading=None)
        assert state['current_battery_reading'] == reading
        state = accept(client, state, key='clear-reading')
        assert state['current_battery_reading'] is None


@pytest.mark.parametrize('settings', [
    {'battery_capacity_kwh': 1.}, {'initial_battery_kwh': 5.}, {'reserve_kwh': 5.},
    {'charge_efficiency': 0.}, {'discharge_efficiency': 1.1},
    {'pv_capacity_kw': -1.}, {'max_discharge_kw': '4'}, {'pv_capacity_kw': None},
])
def test_invalid_settings_rejected_without_mutation(settings):
    service, weather = service_for()
    with TestClient(create_app(forecast_service=service)) as client:
        state = create(client)
        response = client.post(f"{BASE}/{state['id']}/energy-proposals",
            json={'expected_revision': state['revision'], 'settings': settings})
        assert response.status_code == 422
        assert client.get(f"{BASE}/{state['id']}").json() == state
        assert not weather


def test_partial_patch_cancel_stale_input_and_receipt_collision():
    service, _ = service_for()
    with TestClient(create_app(forecast_service=service)) as client:
        state = energy(client, create(client), {'pv_capacity_kw': 2.})
        pid = state['active_energy_proposal_id']
        state = client.patch(f"{BASE}/{state['id']}/energy-proposals/{pid}",
            json={'expected_revision': state['revision'], 'settings': {'max_discharge_kw': 3.}}).json()
        proposal = state['energy_proposals'][-1]
        assert proposal['settings'] == {'pv_capacity_kw': 2., 'max_discharge_kw': 3.}
        old = deepcopy(state['energy_settings'])
        state = post(client, f"{BASE}/{state['id']}/energy-proposals/{pid}/reject",
            {'expected_revision': state['revision']})
        assert state['energy_settings'] == old and state['active_energy_proposal_id'] is None
        state = energy(client, state, {'pv_capacity_kw': 2.})
        stale = state['active_energy_proposal_id']
        state = propose(client, state)
        state = confirm(client, state, key='activity-receipt')
        response = client.post(f"{BASE}/{state['id']}/energy-proposals/{stale}/confirm",
            json={'expected_revision': state['revision'], 'idempotency_key': 'new-receipt'})
        assert response.status_code == 409
        response = client.post(f"{BASE}/{state['id']}/energy-proposals/{stale}/confirm",
            json={'expected_revision': state['revision'], 'idempotency_key': 'activity-receipt'})
        assert response.status_code == 409 and response.json()['error']['code'] == 'IDEMPOTENCY_CONFLICT'


@pytest.mark.parametrize('reading', [
    {'energy_kwh': 2., 'measured_at': '2026-11-14T14:00:00'},
    {'energy_kwh': 5., 'measured_at': '2026-11-14T14:00:00Z'},
])
def test_reading_requires_timezone_and_physical_capacity(reading):
    service, _ = service_for()
    with TestClient(create_app(forecast_service=service)) as client:
        state = create(client)
        response = client.post(f"{BASE}/{state['id']}/energy-proposals",
            json={'expected_revision': 0, 'current_battery_reading': reading})
        assert response.status_code == 422
        assert client.get(f"{BASE}/{state['id']}").json() == state


def test_capacity_decrease_never_rescales_current_reading():
    service, _ = service_for()
    reading = {'energy_kwh': 3.5, 'measured_at': '2026-11-14T14:00:00Z'}
    with TestClient(create_app(forecast_service=service)) as client:
        state = accept(client, energy(client, create(client), current_battery_reading=reading))
        bad = client.post(f"{BASE}/{state['id']}/energy-proposals",
            json={'expected_revision': state['revision'], 'settings': {'battery_capacity_kwh': 3.}})
        assert bad.status_code == 422
        staged = energy(client, state, {'battery_capacity_kwh': 3.}, current_battery_reading=None)
        assert staged['current_battery_reading'] == reading
        state = accept(client, staged, key='capacity-and-clear')
        assert state['current_battery_reading'] is None and state['clinic']['initial_battery_kwh'] == 2.
