"""HTTP contract, real-model integration, validation and technical failure checks."""

from dataclasses import asdict
import json
from pathlib import Path
import socket
from types import SimpleNamespace
import pytest
import scipy.optimize
from fastapi.testclient import TestClient
from app import main
from app.energy_simulator import NumericalError
from app.model_demo import load_inputs
from app.models import SimulationRequest, SimulationResponse
from app.optimizer import SolverError
from app.scenarios import load_catalog
from test_energy_balance import assert_physics


@pytest.fixture(scope='module')
def client():
    with TestClient(main.create_app(), raise_server_exceptions=False) as value:
        yield value


def assert_error(response, status, code):
    assert response.status_code == status, response.text
    body = response.json()
    assert set(body) == {'error'}  # never an invented risk/plan result on failure
    assert body['error']['code'] == code
    assert isinstance(body['error']['details'], list)
    assert 'Traceback' not in response.text
    return body['error']


def test_health_and_four_resolved_presets(client):
    assert client.get('/api/health').json() == {'status':'ok', 'api_version':'1.0'}
    response = client.get('/api/scenarios')
    assert response.status_code == 200
    presets = response.json()['scenarios']
    assert [s['id'] for s in presets] == ['scheduling', 'normal', 'storm', 'high_demand']
    assert presets[0]['defaults']['battery_capacity_kwh'] == 8
    assert presets[2]['defaults']['initial_battery_kwh'] == 6
    assert all(s['data_source'] == 'synthetic' for s in presets)


@pytest.mark.parametrize('scenario,expected', [('scheduling','OK'), ('normal','OK'),
    ('storm','RESERVE_AT_RISK'), ('high_demand','CRITICAL_SHORTAGE')])
def test_real_model_endpoint_and_physical_contract(client, scenario, expected):
    response = client.post('/api/simulate', json={'scenario':scenario})
    assert response.status_code == 200, response.text
    result = response.json()
    SimulationResponse.model_validate(result)
    assert result['status'] == result['optimized']['status'] == expected
    assert result['effective_config']['initial_battery_kwh'] == load_inputs(scenario).battery.initial_battery_kwh
    assert result['data_source'] == 'synthetic'
    assert result['timezone'] == 'Africa/Nairobi'
    for plan_name in ('baseline', 'heuristic', 'optimized'):
        assert_physics(load_inputs(scenario), result[plan_name])
    if scenario == 'high_demand':
        assert result['optimized']['metrics']['critical_unserved_kwh'] == pytest.approx(1.32)
        assert result['equipment'][-1]['id'] == 'additional_protected_load'
        assert result['equipment'][-1]['power_kw'] == 4.5
    if scenario == 'scheduling':
        comparison = result['comparison']
        assert comparison['same_flexible_work_completed']
        assert comparison['heuristic_matches_optimizer_metrics']
        assert comparison['battery_preserved_at_midnight_kwh'] == pytest.approx(2.210526315789473)
        assert comparison['minimum_battery_improvement_kwh'] == pytest.approx(.368421052631574)
        assert any(w['plan']=='baseline' and w['code']=='RESERVE_BELOW_TARGET' for w in result['warnings'])
        assert not any(w['plan']=='optimized' for w in result['warnings'])
        assert any(r['title']=='Sunshine-first matches key metrics' for r in result['recommendations'])


@pytest.mark.parametrize('scenario', ['storm', 'high_demand'])
def test_explanations_disclose_completion_tradeoff_and_all_plan_warnings(client, scenario):
    result = client.post('/api/simulate', json={'scenario':scenario}).json()
    assert result['comparison']['same_flexible_work_completed'] is False
    assert any(r['title']=='Work completion differs between schedules' for r in result['recommendations'])
    assert any(w['plan']=='optimized' and w['code']=='FLEXIBLE_DEFERRED' for w in result['warnings'])
    assert any(w['plan']=='heuristic' for w in result['warnings'])
    if scenario == 'high_demand':
        message = next(r['explanation'] for r in result['recommendations'] if r['severity']=='critical')
        assert '4 kW' in message and '20:00' in message and '21:00' in message
        assert '1.320000' in message


@pytest.mark.parametrize('field', ['battery_capacity_kwh','initial_battery_kwh','reserve_kwh','pv_capacity_kw',
    'charge_efficiency','discharge_efficiency','max_charge_kw','max_discharge_kw','additional_critical_kw'])
@pytest.mark.parametrize('bad', [None, True, '5', -1])
def test_strict_numeric_validation(client, field, bad):
    error = assert_error(client.post('/api/simulate', json={'scenario':'high_demand',field:bad}), 422,'INVALID_REQUEST')
    assert any(field in d['loc'] for d in error['details'])


@pytest.mark.parametrize('patch', [{'scenario':'unknown'}, {'scenario':None}, {'unexpected':1},
    {'battery_capacity_kwh':0}, {'battery_capacity_kwh':201}, {'pv_capacity_kw':101},
    {'charge_efficiency':0}, {'discharge_efficiency':1.01}, {'additional_critical_kw':11},
    {'max_charge_kw':101}, {'max_discharge_kw':101}, {'battery_capacity_kwh':1},
    {'initial_battery_kwh':21}, {'reserve_kwh':21}])
def test_bad_ranges_cross_fields_and_unknowns(client, patch):
    assert_error(client.post('/api/simulate', json={'scenario':'high_demand'} | patch),422,'INVALID_REQUEST')


@pytest.mark.parametrize('body', ['{"scenario":"normal","pv_capacity_kw":NaN}',
    '{"scenario":"normal","pv_capacity_kw":Infinity}', '{"scenario":"normal","pv_capacity_kw":-Infinity}',
    '{"scenario":', '[]', 'null', '{}', '"normal"'])
def test_invalid_json_or_nonfinite_values_have_serializable_errors(client, body):
    assert_error(client.post('/api/simulate', content=body, headers={'Content-Type':'application/json'}),422,'INVALID_REQUEST')


def test_explicit_zero_overrides_and_no_silent_clamping(client):
    response = client.post('/api/simulate', json={'scenario':'high_demand', 'additional_critical_kw':0,
        'pv_capacity_kw':0, 'initial_battery_kwh':0, 'reserve_kwh':0, 'max_charge_kw':0, 'max_discharge_kw':0})
    assert response.status_code == 200
    result = response.json()
    assert result['effective_config']['pv_capacity_kw'] == 0
    assert result['equipment'][-1]['power_kw'] == 0
    assert result['optimized']['metrics']['total_solar_kwh'] == 0
    assert result['status'] == 'CRITICAL_SHORTAGE'
    # A preset's expected status must never override computed results.
    assert_error(client.post('/api/simulate', json={'scenario':'normal','battery_capacity_kwh':8}),422,'INVALID_REQUEST')
    assert_error(client.post('/api/simulate', json={'scenario':'normal','additional_critical_kw':0}),422,'INVALID_REQUEST')


def test_reset_requests_do_not_retain_previous_overrides(client):
    changed = client.post('/api/simulate', json={'scenario':'scheduling', 'pv_capacity_kw':0}).json()
    reset = client.post('/api/simulate', json={'scenario':'scheduling'}).json()
    assert changed['effective_config']['pv_capacity_kw'] == 0
    assert reset['effective_config']['pv_capacity_kw'] == 1.5
    assert reset['optimized']['metrics']['total_solar_kwh'] > 9


def test_each_request_runs_fresh_model_calculations(client, monkeypatch):
    real = main.compare_schedules
    calls = []
    def counted(inputs):
        calls.append(inputs)
        return real(inputs)
    monkeypatch.setattr(main, 'compare_schedules', counted)
    for _ in range(2):
        assert client.post('/api/simulate', json={'scenario':'normal'}).status_code == 200
    assert len(calls) == 2


@pytest.mark.parametrize('exception,status,code', [
    (SolverError('SOLVER_TIME_LIMIT','private solver log'),503,'SOLVER_TIME_LIMIT'),
    (SolverError('SOLVER_UNAVAILABLE','private solver log'),503,'SOLVER_UNAVAILABLE'),
    (NumericalError('private solver log'),503,'NUMERICAL_ERROR'),
    (RuntimeError('private solver log'),500,'INTERNAL_ERROR')])
def test_technical_failures_are_not_physical_shortages(client, monkeypatch, exception, status, code):
    def fail(_):
        raise exception
    monkeypatch.setattr(main, 'compare_schedules', fail)
    response = client.post('/api/simulate', json={'scenario':'normal'})
    assert_error(response,status,code)
    assert 'private solver log' not in response.text


def test_actual_solver_timeout_maps_to_503(client, monkeypatch):
    monkeypatch.setattr(scipy.optimize,'milp',lambda *a,**kw: SimpleNamespace(status=1,success=False,x=None))
    assert_error(client.post('/api/simulate',json={'scenario':'normal'}),503,'SOLVER_TIME_LIMIT')


def test_invalid_response_is_not_published_as_healthy(client, monkeypatch):
    real = main.compare_schedules
    def corrupt(inputs):
        result = real(inputs)
        result['optimized']['metrics']['final_soc_kwh'] = float('nan')
        return result
    monkeypatch.setattr(main,'compare_schedules',corrupt)
    assert_error(client.post('/api/simulate',json={'scenario':'normal'}),500,'INTERNAL_ERROR')


def test_openapi_documents_custom_errors_and_three_way_comparison(client):
    schema = client.get('/openapi.json').json()
    endpoint = schema['paths']['/api/simulate']['post']
    for status in ('422','503','500'):
        assert endpoint['responses'][status]['content']['application/json']['schema']['$ref'].endswith('/ApiErrorResponse')
    assert {'heuristic','comparison'} <= set(schema['components']['schemas']['SimulationResponse']['properties'])
    for field, prop in schema['components']['schemas']['SimulationRequest']['properties'].items():
        if field != 'scenario':
            assert prop['type'] == 'number'  # optional but never nullable
            assert 'default' not in prop
    assert_error(client.get('/api/missing'),404,'INVALID_REQUEST')
    assert_error(client.get('/api/simulate'),405,'INVALID_REQUEST')


def test_exported_openapi_matches_running_contract(client):
    root = Path(__file__).resolve().parents[2]
    assert client.get('/openapi.json').json() == json.loads((root/'contracts/openapi.json').read_text())


def test_frontend_example_is_a_valid_computed_physical_response():
    root = Path(__file__).resolve().parents[2]
    result = json.loads((root/'contracts/examples/scheduling.response.json').read_text())
    SimulationResponse.model_validate(result)
    for name in ('baseline','heuristic','optimized'):
        assert_physics(load_inputs('scheduling'), result[name])


def test_validated_catalog_mapping_matches_person_one_inputs():
    catalog = load_catalog()
    for scenario in ('scheduling','normal','storm','high_demand'):
        request = SimulationRequest(scenario=scenario)
        assert asdict(catalog.build_inputs(request,catalog.resolve(request))) == asdict(load_inputs(scenario))


def test_api_calculations_need_no_outbound_network(client, monkeypatch):
    def offline(*args, **kwargs):
        raise AssertionError('Model execution must not open an outbound connection')
    monkeypatch.setattr(socket, 'create_connection', offline)
    for scenario in ('scheduling','normal','storm','high_demand'):
        assert client.post('/api/simulate',json={'scenario':scenario}).status_code == 200


def test_zero_critical_demand_yields_null_coverage_and_no_nan(tmp_path):
    from app.scenarios import CONFIG_PATH
    data = json.loads(CONFIG_PATH.read_text())
    for equipment in data['critical_equipment']:
        equipment['power_kw'] = 0
    path = tmp_path/'scenarios.json'
    path.write_text(json.dumps(data))
    with TestClient(main.create_app(path)) as other:
        response = other.post('/api/simulate',json={'scenario':'normal','reserve_kwh':0})
        assert response.status_code == 200
        result = response.json()
        assert result['optimized']['metrics']['critical_coverage_pct'] is None
        assert result['status'] == 'OK'
