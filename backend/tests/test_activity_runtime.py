"""Shared device runtime edits are explicit daily work budgets, not new devices."""
from fastapi.testclient import TestClient
import pytest
from app.main import create_app
from test_weather_forecast import service_for
from test_planning_state import BASE, create, post, propose, confirm


def pump_constraint(hours):
    return [{'equipment_id': 'pump', 'required_duration_hours': hours}]


def test_runtime_revision_of_configured_device_recomputes_once_without_event_inference():
    service, _ = service_for()
    with TestClient(create_app(forecast_service=service)) as client:
        state = confirm(client, propose(client, create(client), equipment_ids=['pump']))
        original = state['confirmed_activities'][0]
        state = post(client, f"{BASE}/{state['id']}/proposals", {
            'expected_revision': state['revision'], 'target_activity_id': original['id'],
            'details': {'duration_hours': 3, 'equipment_constraints': pump_constraint(3)}})
        assert state['computed_plan']['simulation']['optimized']['metrics']['flexible_requested_kwh'] == 1.
        state = confirm(client, state, key='pump-three-daily-hours')
        assert len(state['equipment_inventory']) == 2 and len(state['confirmed_activities']) == 1
        assert state['confirmed_activities'][0]['version'] == 2
        metrics = state['computed_plan']['simulation']['optimized']['metrics']
        assert metrics['flexible_requested_kwh'] == pytest.approx(1.5)
        assert metrics['critical_requested_kwh'] == pytest.approx(2.4)


def test_shared_daily_runtime_max_preserves_other_work_and_baseline():
    service, _ = service_for()
    with TestClient(create_app(forecast_service=service)) as client:
        state = create(client)
        for name, hours in [('Campaign A', 3), ('Campaign B', 4)]:
            state = confirm(client, propose(client, state, name=name, equipment_ids=['pump'],
                equipment_constraints=pump_constraint(hours)), key=name)
        assert len(state['equipment_inventory']) == 2
        assert state['computed_plan']['simulation']['optimized']['metrics']['flexible_requested_kwh'] == 2.
        activity = next(a for a in state['confirmed_activities'] if a['details']['name'] == 'Campaign B')
        state = post(client, f"{BASE}/{state['id']}/proposals", {
            'expected_revision': state['revision'], 'target_activity_id': activity['id'],
            'details': {'equipment_constraints': pump_constraint(1)}})
        state = confirm(client, state, key='reduce-one-reviewed-runtime')
        assert state['computed_plan']['simulation']['optimized']['metrics']['flexible_requested_kwh'] == 1.5
        # Association/event duration alone never alters device work.
        state = confirm(client, propose(client, state, name='Campaign C', duration_hours=5,
            equipment_ids=['pump']), key='event-alone')
        assert state['computed_plan']['simulation']['optimized']['metrics']['flexible_requested_kwh'] == 1.5


def test_impossible_combined_window_and_essential_runtime_are_rejected_atomically():
    service, _ = service_for()
    with TestClient(create_app(forecast_service=service)) as client:
        state = create(client)
        bad = client.post(f"{BASE}/{state['id']}/proposals", json={
            'expected_revision': state['revision'], 'details': {
                'equipment_ids': ['fridge'], 'equipment_constraints': [
                    {'equipment_id': 'fridge', 'required_duration_hours': 1}]}})
        assert bad.status_code == 422
        state = propose(client, state, equipment_ids=['pump'], equipment_constraints=[
            {'equipment_id': 'pump', 'required_duration_hours': 3, 'allowed_hours': [10, 11]}])
        bad = client.post(f"{BASE}/{state['id']}/proposals/{state['active_proposal_id']}/confirm", json={
            'expected_revision': state['revision'], 'idempotency_key': 'impossible'})
        assert bad.status_code == 422
        assert client.get(f"{BASE}/{state['id']}").json() == state
