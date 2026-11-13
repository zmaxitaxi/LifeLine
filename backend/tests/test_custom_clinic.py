import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from app.main import create_app
from app.models import SimulationRequest
from app.scenarios import load_catalog, load_weather
from test_energy_balance import assert_physics


@pytest.fixture(scope='module')
def client():
    with TestClient(create_app()) as value:
        yield value


def critical(power=.42,hours=None):
    return dict(id='custom-essential',name='User-defined essential load',category='critical',power_kw=power,
                required_hours=[4,5,6,18,22] if hours is None else hours)


def flexible():
    return dict(id='custom-pump',name='Optional auxiliary pump',category='flexible',max_power_kw=.37,
                required_energy_kwh=1.11,allowed_hours=[10,11,12,13,14,15,16,17,18,19,20],
                baseline_allocations=[dict(hour=h,requested_kwh=.37) for h in [18,19,20]],divisible=True)


def solve(client,payload):
    response=client.post('/api/simulate',json=payload)
    assert response.status_code==200,response.text
    result=response.json()
    request=SimulationRequest.model_validate(payload)
    catalog=load_catalog()
    inputs=catalog.build_inputs(request,catalog.resolve(request))
    for name in ('baseline','heuristic','optimized'):
        assert_physics(inputs,result[name])
    return result


@pytest.mark.parametrize('dataset',['synthetic','kisumu-2025-01-14'])
def test_unfamiliar_equipment_and_system_are_really_calculated(client,dataset):
    payload=dict(scenario='normal',pv_capacity_kw=2.7,battery_capacity_kwh=9,initial_battery_kwh=3.3,
                 reserve_kwh=1.2,weather_dataset=dataset,equipment=[critical(),flexible()])
    result=solve(client,payload)
    assert result['data_source']==('user_defined' if dataset=='synthetic' else 'mixed')
    assert result['optimized']['metrics']['critical_requested_kwh']==pytest.approx(2.1)
    assert result['optimized']['metrics']['flexible_requested_kwh']==pytest.approx(1.11)
    assert result['optimized']['metrics']['flexible_served_kwh']==pytest.approx(1.11)
    assert [e['id'] for e in result['equipment']]==['custom-essential','custom-pump']
    changed=solve(client,payload|{'equipment':[critical(.65),flexible()]})
    assert changed['optimized']['metrics']['critical_requested_kwh']==pytest.approx(3.25)


def test_remove_all_equipment_and_add_again(client):
    empty=solve(client,dict(scenario='normal',equipment=[]))
    assert empty['optimized']['metrics']['critical_coverage_pct'] is None
    assert empty['optimized']['metrics']['flexible_requested_kwh']==0
    added=solve(client,dict(scenario='normal',equipment=[critical()]))
    assert added['optimized']['metrics']['critical_requested_kwh']==pytest.approx(2.1)


def test_capacity_explorer_separates_power_from_stored_energy(client):
    initial=dict(scenario='normal',equipment=[critical(4.66,[20,21])])
    base=solve(client,initial)
    larger=solve(client,initial|{'battery_capacity_kwh':40})
    stronger=solve(client,initial|{'max_discharge_kw':6})
    assert base['diagnosis']['assessment']=='INFRASTRUCTURE_LIMITATION'
    assert base['diagnosis']['discharge_limited_hours']==[20,21]
    assert base['optimized']['metrics']['critical_unserved_kwh']==pytest.approx(1.32)
    assert larger['optimized']['metrics']['critical_unserved_kwh']==pytest.approx(1.32)
    assert stronger['optimized']['metrics']['critical_unserved_kwh']==0


def test_storage_capacity_can_limit_use_of_abundant_daytime_solar(client):
    payload=dict(scenario='normal',equipment=[critical(.5,list(range(18,24)))],battery_capacity_kwh=.1,
                 initial_battery_kwh=.1,reserve_kwh=0)
    small=solve(client,payload)
    larger=solve(client,payload|{'battery_capacity_kwh':4})
    assert 'STORAGE_OR_TIMING_LIMIT' in small['diagnosis']['constraints']
    assert small['optimized']['metrics']['critical_unserved_kwh']>2
    assert larger['optimized']['metrics']['critical_unserved_kwh']==0


def test_total_energy_deficit_and_weather_only_adverse_test(client):
    payload=dict(scenario='normal',pv_capacity_kw=.2,battery_capacity_kwh=1,initial_battery_kwh=0,
                 reserve_kwh=0,equipment=[critical(2,list(range(24)))])
    result=solve(client,payload)
    assert 'TOTAL_ENERGY_DEFICIT' in result['diagnosis']['constraints']
    normal=solve(client,dict(scenario='scheduling',equipment=[critical(),flexible()]))
    adverse=solve(client,dict(scenario='scheduling',equipment=[critical(),flexible()],cloud_factors=[.1]*24))
    assert adverse['effective_config']==normal['effective_config']
    assert adverse['equipment']==normal['equipment']
    assert adverse['optimized']['metrics']['total_solar_kwh']==pytest.approx(.1*normal['optimized']['metrics']['total_solar_kwh'])


def test_window_restrictions_and_no_meaningful_schedule_gain(client):
    task=flexible();task['allowed_hours']=[18];task['baseline_allocations']=[dict(hour=18,requested_kwh=.37)]
    result=solve(client,dict(scenario='normal',equipment=[task]))
    assert result['optimized']['metrics']['flexible_served_kwh']==pytest.approx(.37)
    assert result['optimized']['metrics']['flexible_deferred_kwh']==pytest.approx(.74)
    assert result['diagnosis']['window_limited_tasks']==['custom-pump']
    noflex=solve(client,dict(scenario='normal',equipment=[critical()]))
    assert noflex['diagnosis']['assessment']=='ADEQUATE_CAPACITY'


@pytest.mark.parametrize('patch',[{'equipment':None},{'equipment':[critical(),critical()]},
    {'equipment':[critical(-1)]},{'equipment':[critical(1,[24])]},
    {'equipment':[flexible()|{'allowed_hours':[12]}]}, {'equipment':[critical()]*21},
    {'cloud_factors':[1]*23},{'cloud_factors':[1.1]*24},{'weather_dataset':'unknown'}])
def test_custom_invalid_values_are_rejected(client,patch):
    response=client.post('/api/simulate',json={'scenario':'normal'}|patch)
    assert response.status_code==422
    assert response.json()['error']['code']=='INVALID_REQUEST'


def test_nasa_data_provenance_units_and_offline_weather_endpoint(client):
    weather=load_weather()
    raw=json.loads((Path(__file__).resolve().parents[2]/'data/nasa_power_raw.json').read_text())
    assert raw['parameters']['ALLSKY_SFC_SW_DWN']['units']=='Wh/m^2'
    assert len(weather['irradiance_kwh_m2'])==24
    assert sum(weather['irradiance_kwh_m2'])==pytest.approx(6.91772)
    assert weather['irradiance_kwh_m2'][0]==raw['properties']['parameter']['ALLSKY_SFC_SW_DWN']['2025011321']/1000
    assert client.get('/api/weather').json()['datasets'][0]['id']==weather['id']
