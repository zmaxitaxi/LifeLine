"""Restart recovery retains confirmed inputs, receipts and genuine conversation."""
import asyncio
import json
import os
import pytest
from fastapi.testclient import TestClient
from app.main import create_app
from app.planning_state import PlanningStore
from app.planning_persistence import LocalPlanningPersistence
from test_weather_forecast import service_for
from test_local_agent import agent_with
from test_planning_state import BASE, create, propose, confirm, post
from test_planning_agent import ask
from test_energy_settings import energy, accept


def test_restart_preserves_settings_activity_plan_and_idempotency(tmp_path):
    path = tmp_path / 'state' / 'planning.json'
    service, _ = service_for()
    with TestClient(create_app(forecast_service=service, planning_state_path=path)) as client:
        state = confirm(client, propose(client, create(client)))
        state = energy(client, state, {'battery_capacity_kwh': 8.})
        pid = state['active_energy_proposal_id']
        state = accept(client, state)
    with TestClient(create_app(forecast_service=service, planning_state_path=path)) as client:
        assert client.get(f"{BASE}/{state['id']}").json() == state
        duplicate = post(client, f"{BASE}/{state['id']}/energy-proposals/{pid}/confirm",
            {'expected_revision': 0, 'idempotency_key': 'settings-click'})
        assert duplicate == state
    assert os.stat(path).st_mode & 0o777 == 0o600
    assert not list(path.parent.glob('*.tmp'))


def test_restart_restores_partial_draft_current_reading_and_chat_ids(tmp_path):
    path = tmp_path / 'planning.json'
    service, weather = service_for()
    agent, _ = agent_with([{'name': 'conversational_reply', 'arguments': {
        'kind': 'greeting', 'message': 'Hello! How can I help with your clinic planning?'}}])
    with TestClient(create_app(forecast_service=service, agent_service=agent, planning_state_path=path)) as client:
        state = propose(client, create(client), end_hour=16)
        before = state
        response = ask(client, state, 'Hello')
        assert response['state'] == before
        transcript = client.get(f"{BASE}/{state['id']}/conversation").json()
        assert [message['role'] for message in transcript['messages']] == ['user', 'assistant']
        assert transcript['messages'][1]['id'] == response['message_id']
        assert transcript['messages'][0]['id'] == response['user_message_id']
        assert transcript['messages'][1]['content'] == response['message']
        assert not weather
    with TestClient(create_app(forecast_service=service, planning_state_path=path)) as client:
        assert client.get(f"{BASE}/{state['id']}").json() == before
        assert client.get(f"{BASE}/{state['id']}/conversation").json() == transcript


def test_interrupted_compute_restores_inputs_but_cannot_appear_current(tmp_path):
    path = tmp_path / 'planning.json'
    service, _ = service_for()
    with TestClient(create_app(forecast_service=service, planning_state_path=path)) as client:
        state = confirm(client, propose(client, create(client)))
    payload = json.loads(path.read_text())
    payload['states'][state['id']]['plan_status'] = 'pending'
    path.write_text(json.dumps(payload))
    restored = PlanningStore(path).read(state['id'])
    assert restored.confirmed_activities and restored.energy_settings.initial_battery_kwh == 2.
    assert restored.plan_status == 'failed' and restored.plan_error == 'CALCULATION_INTERRUPTED'
    assert restored.computed_plan is None and restored.forecast_reference is None


def test_corrupt_snapshot_is_not_silently_discarded(tmp_path):
    path = tmp_path / 'planning.json'
    path.write_text('{bad snapshot')
    with pytest.raises(RuntimeError, match='Preserve'):
        PlanningStore(path)
    assert path.read_text() == '{bad snapshot'


def test_failed_atomic_write_keeps_previous_snapshot_and_removes_temporary_file(tmp_path, monkeypatch):
    path = tmp_path / 'planning.json'
    persistence = LocalPlanningPersistence(path)
    persistence.save({'schema_version': 1, 'states': {'prior': 'retained'}})
    original = path.read_bytes()
    def fail_replace(*_):
        raise OSError('simulated disk failure')
    monkeypatch.setattr(os, 'replace', fail_replace)
    with pytest.raises(OSError):
        persistence.save({'schema_version': 1, 'states': {}})
    assert path.read_bytes() == original
    assert not list(tmp_path.glob('.planning-*.tmp'))


def test_failed_confirmation_save_rolls_back_memory_and_receipt(tmp_path, monkeypatch):
    path = tmp_path / 'planning.json'
    service, weather = service_for()
    with TestClient(create_app(forecast_service=service, planning_state_path=path)) as client:
        state = energy(client, create(client), {'battery_capacity_kwh': 8.})
        pid = state['active_energy_proposal_id']
        old_file = path.read_bytes()
        def fail_replace(*_):
            raise OSError('simulated disk failure')
        with monkeypatch.context() as patch:
            patch.setattr(os, 'replace', fail_replace)
            response = client.post(f"{BASE}/{state['id']}/energy-proposals/{pid}/confirm", json={
                'expected_revision': state['revision'], 'idempotency_key': 'retry-after-storage'})
            assert response.status_code == 503 and response.json()['error']['code'] == 'STATE_UNAVAILABLE'
        assert path.read_bytes() == old_file and not weather
        assert client.get(f"{BASE}/{state['id']}").json() == state
        retried = post(client, f"{BASE}/{state['id']}/energy-proposals/{pid}/confirm", {
            'expected_revision': state['revision'], 'idempotency_key': 'retry-after-storage'})
        assert retried['energy_settings']['battery_capacity_kwh'] == 8.
        assert retried['plan_status'] == 'current'


def test_sourced_timezone_survives_restart_without_changing_physical_inputs(tmp_path):
    path = tmp_path / 'planning.json'
    service, _ = service_for()
    with TestClient(create_app(forecast_service=service, planning_state_path=path)) as client:
        state = create(client)
        store = client.app.state.planning
        resolved = asyncio.run(store.resolve_timezone(state['id'], state['revision'], 'America/Los_Angeles'))
        assert resolved.revision == state['revision'] + 1
        assert resolved.input_revision == state['input_revision']
        assert resolved.clinic.model_dump(exclude_none=True) == state['clinic']
    restored = PlanningStore(path).read(state['id'])
    assert restored.timezone == 'America/Los_Angeles'
