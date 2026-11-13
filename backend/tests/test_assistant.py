"""Conversational requests must use real physics and ask for missing inputs."""
import socket
import pytest
from fastapi.testclient import TestClient
from app.main import create_app


@pytest.fixture(scope='module')
def client():
    with TestClient(create_app(), raise_server_exceptions=False) as value:
        yield value


def ask(client, message, plan=None, pending=None):
    response = client.post('/api/assistant', json={'message': message,
        'plan': plan or {'scenario': 'scheduling'}, 'pending': pending})
    assert response.status_code == 200, response.text
    return response.json()


def test_tomorrow_uses_same_model_as_simulate_and_discloses_no_forecast(client):
    response = ask(client, 'Will we have enough electricity tomorrow?')
    direct = client.post('/api/simulate', json={'scenario': 'scheduling'}).json()
    assert response['result'] == direct
    assert response['mode'] == 'offline'
    assert response['tools_used'] == ['energy_simulator', 'schedule_optimizer', 'schedule_comparison']
    assert 'not tomorrow’s actual conditions' in response['message']


def test_cloud_test_preserves_clinic_requirements_and_recomputes(client):
    plan = {'scenario': 'scheduling', 'initial_battery_kwh': 5.5}
    before = client.post('/api/simulate', json=plan).json()
    response = ask(client, 'What if the weather is worse than expected?', plan)
    after = response['result']
    assert after['effective_config'] == before['effective_config']
    assert after['equipment'] == before['equipment']
    assert after['optimized']['metrics']['total_solar_kwh'] == pytest.approx(before['optimized']['metrics']['total_solar_kwh'] / 4)
    assert after['cloud_factors'] == [0.25] * 24


def test_simple_followup_changes_actual_required_energy(client):
    first = ask(client, 'Change laundry')
    assert first['result'] is None
    assert first['question']['kind'] == 'duration'
    response = ask(client, '4 hours', pending=first['question'])
    task = next(t for t in response['result']['optimized']['flexible_tasks'] if t['task_id'] == 'auxiliary_laundry')
    assert task['requested_kwh'] == pytest.approx(2.4)
    assert response['result'] == client.post('/api/simulate', json=response['request']).json()


def test_deadline_changes_allowed_hours_and_reports_unfinished_work(client):
    response = ask(client, 'Run laundry for 4 hours before noon')
    task = next(e for e in response['result']['equipment'] if e['id'] == 'auxiliary_laundry')
    assert task['allowed_hours'] == [10, 11]
    assert task['required_energy_kwh'] == pytest.approx(2.4)
    result = next(t for t in response['result']['optimized']['flexible_tasks'] if t['task_id'] == task['id'])
    assert result['deferred_kwh'] >= 1.2 - 1e-6
    assert all(a['hour'] < 12 for a in result['allocations'])


def test_sterilizer_missing_information_is_asked_one_question_at_a_time(client):
    first = ask(client, 'We need to sterilize equipment before noon. When should we do it?')
    assert first['result'] is None and first['question']['kind'] == 'power'
    second = ask(client, '1200 watts', pending=first['question'])
    assert second['result'] is None and second['question']['kind'] == 'duration'
    assert 'cannot validate sterilization cycles' in second['message']
    third = ask(client, '2 hours', pending=second['question'])
    assert third['result'] is None and third['question']['kind'] == 'start'
    response = ask(client, '8am', pending=third['question'])
    equipment = response['result']['equipment'][-1]
    assert equipment['power_kw'] == 1.2
    assert equipment['category'] == 'critical'  # never a divisible cycle
    assert len(equipment['required_hours']) == 2
    assert max(equipment['required_hours']) < 12
    assert min(equipment['required_hours']) >= 8
    assert equipment['required_hours'][1] == equipment['required_hours'][0] + 1
    assert response['result'] == client.post('/api/simulate', json=response['request']).json()


def test_cannot_move_essential_hours_or_invent_unknown_equipment(client):
    response = ask(client, 'Run refrigerator for 2 hours')
    assert response['result'] is None
    assert 'will not move them automatically' in response['message']
    response = ask(client, 'Schedule the new x-ray machine')
    assert response['result'] is None
    assert response['question'] is not None


def test_shortage_is_explicit_not_a_guarantee(client):
    response = ask(client, 'Will we have enough electricity tomorrow?', {'scenario': 'high_demand'})
    assert response['result']['status'] == 'CRITICAL_SHORTAGE'
    assert response['result']['optimized']['metrics']['critical_unserved_kwh'] == pytest.approx(1.32)
    assert 'isn’t enough power' in response['message']


def test_battery_change_is_not_canned(client):
    response = ask(client, 'The battery is at 0%')
    assert response['result']['effective_config']['initial_battery_kwh'] == 0
    assert response['result']['optimized']['metrics']['critical_unserved_kwh'] > 0


def test_unknown_and_invalid_duration_ask_rather_than_guess(client):
    assert ask(client, 'Please help with something else')['result'] is None
    assert ask(client, 'Run laundry for -3 hours')['result'] is None
    assert ask(client, 'We need a new oxygen unit. Will there be enough power tomorrow?')['result'] is None
    assert ask(client, 'What if we have three cloudy days?')['result'] is None
    assert client.post('/api/assistant', json={'message': '', 'plan': {'scenario': 'normal'}}).status_code == 422


def test_local_assistant_and_forecast_status_work_without_external_network(client, monkeypatch):
    def offline(*args, **kwargs):
        raise AssertionError('No external service is needed')
    monkeypatch.setattr(socket, 'create_connection', offline)
    assert ask(client, 'Check battery reliability')['result'] is not None
    forecast = client.get('/api/planning-status').json()['forecast']
    assert forecast['available'] is False
    assert forecast['source'] is None and forecast['updated_at'] is None
    assert forecast['forecast_date'] is None and forecast['requested_date']
