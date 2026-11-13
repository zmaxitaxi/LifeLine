"""Malformed bundled data must stop startup, before any healthy API response."""

from copy import deepcopy
import json
import pytest
from pydantic import ValidationError
from fastapi.testclient import TestClient
from app.main import create_app
from app.scenarios import CONFIG_PATH, ScenarioCatalog, load_catalog


def mutate(data, case):
    if case=='unknown': data['unexpected']=1
    elif case=='duplicate_scenario': data['scenarios'][1]['id']='scheduling'
    elif case=='missing_scenario': data['scenarios'].pop()
    elif case=='unknown_scenario': data['scenarios'][0]['id']='other'
    elif case=='cloud_length': data['scenarios'][0]['cloud_factors'].pop()
    elif case=='cloud_bounds': data['scenarios'][0]['cloud_factors'][0]=1.01
    elif case=='cloud_nan': data['scenarios'][0]['cloud_factors'][0]=float('nan')
    elif case=='cloud_bool': data['scenarios'][0]['cloud_factors'][0]=True
    elif case=='capacity': data['scenarios'][0]['overrides']['battery_capacity_kwh']=1
    elif case=='reserve': data['defaults']['reserve_kwh']=30
    elif case=='duplicate_id': data['flexible_equipment'][0]['id']=data['critical_equipment'][0]['id']
    elif case=='reserved_id': data['critical_equipment'][0]['id']='additional_protected_load'
    elif case=='critical_hours': data['critical_equipment'][0]['required_hours']=[24]
    elif case=='duplicate_critical': data['critical_equipment'][0]['required_hours']=[0,0]
    elif case=='negative_power': data['critical_equipment'][0]['power_kw']=-1
    elif case=='negative_task': data['flexible_equipment'][0]['required_energy_kwh']=-1
    elif case=='null': data['scenarios'][0]['overrides']['pv_capacity_kw']=None
    elif case=='boolean': data['defaults']['initial_battery_kwh']=True
    elif case=='string_number': data['defaults']['initial_battery_kwh']='14'
    elif case=='bad_window': data['flexible_equipment'][0]['allowed_hours']=[-1]
    elif case=='duplicate_window': data['flexible_equipment'][0]['allowed_hours']=[18,18]
    elif case=='empty_window': data['flexible_equipment'][0]['allowed_hours']=[]
    elif case=='outside_window': data['flexible_equipment'][0]['baseline_allocations'][0]['hour']=2
    elif case=='over_power': data['flexible_equipment'][0]['baseline_allocations'][0]['requested_kwh']=5
    elif case=='over_energy': data['flexible_equipment'][0]['required_energy_kwh']=.1
    elif case=='duplicate_allocation': data['flexible_equipment'][0]['baseline_allocations'][1]['hour']=18
    elif case=='extra_load_scope': data['scenarios'][0]['additional_critical_hours']=[20]
    elif case=='duplicate_extra_hours': data['scenarios'][-1]['additional_critical_hours']=[20,20]
    elif case=='empty_extra_hours': data['scenarios'][-1]['additional_critical_hours']=[]
    elif case=='not_divisible': data['flexible_equipment'][0]['divisible']=False
    elif case=='numeric_divisible': data['flexible_equipment'][0]['divisible']=1
    elif case=='bool_dt': data['dt_hours']=True
    elif case=='float_daylight': data['pv_model']['sunrise_hour']=6.0


@pytest.mark.parametrize('case', ['unknown','duplicate_scenario','missing_scenario','unknown_scenario',
    'cloud_length','cloud_bounds','cloud_nan','cloud_bool','capacity','reserve','duplicate_id','reserved_id',
    'critical_hours','duplicate_critical','negative_power','negative_task','null','boolean','string_number',
    'bad_window','duplicate_window','empty_window','outside_window','over_power','over_energy',
    'duplicate_allocation','extra_load_scope','duplicate_extra_hours','empty_extra_hours',
    'not_divisible','numeric_divisible','bool_dt','float_daylight'])
def test_bad_configuration_rejected_at_startup(case, tmp_path):
    data = json.loads(CONFIG_PATH.read_text())
    mutate(data,case)
    path = tmp_path/'bad.json'
    path.write_text(json.dumps(data))
    with pytest.raises(ValidationError):
        with TestClient(create_app(path)):
            pytest.fail('Invalid configuration must never reach a running service')


def test_config_path_independent_of_working_directory(monkeypatch,tmp_path):
    monkeypatch.chdir(tmp_path)
    assert len(load_catalog().scenarios)==4


def test_unfulfillable_flexible_work_is_deferred_not_a_config_error():
    data = json.loads(CONFIG_PATH.read_text())
    data['flexible_equipment'][0]['required_energy_kwh']=100
    catalog = ScenarioCatalog.model_validate(deepcopy(data))
    assert catalog.flexible_equipment[0].required_energy_kwh==100
