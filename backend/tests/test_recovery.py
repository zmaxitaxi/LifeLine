"""Recovery interventions run the original model; numbers are never fixtures."""
from copy import deepcopy
import json
import httpx
import pytest
from fastapi.testclient import TestClient
from app.main import create_app
from app.local_agent import LocalAgent
from test_weather_forecast import service_for, request_body, weather_payload
from test_local_agent import agent_with


def critical(power=2.,hours=None):
    return {'id':'essential','name':'Operator-protected equipment','category':'critical','power_kw':power,'required_hours':hours or [20]}


def flexible():
    return {'id':'optional','name':'Operator-reviewed flexible work','category':'flexible','max_power_kw':1.,
        'required_energy_kwh':1.,'allowed_hours':[12,18],
        'baseline_allocations':[{'hour':18,'requested_kwh':1.}],'divisible':True}


def case(**changes):
    clinic={'scenario':'normal','battery_capacity_kwh':2.,'initial_battery_kwh':.5,'reserve_kwh':0.,
        'pv_capacity_kw':1.,'max_charge_kw':4.,'max_discharge_kw':4.,'charge_efficiency':1.,'discharge_efficiency':1.,
        'equipment':[critical(),flexible()]} | changes
    return request_body(clinic=clinic,midnight_battery_kwh=clinic['initial_battery_kwh']) | {'weather_mode':'existing_scenario'}


def evaluate(body):
    original=deepcopy(body)
    service,calls=service_for()
    with TestClient(create_app(forecast_service=service)) as client:
        response=client.post('/api/recovery/plan',json=body)
    assert response.status_code==200,response.text
    assert body==original
    if body.get('weather_mode')=='existing_scenario': assert not calls
    return response.json()


def test_rescheduling_resolves_real_fixed_schedule_shortage_without_reducing_work():
    d=evaluate(case()|{'focus':'scheduling'})
    assert d['problem_detected']
    assert d['existing']['metrics']['essential_unserved_kwh']==pytest.approx(1.)
    option=d['options'][0]
    assert option['id']=='reschedule'
    assert option['modeled_all_requirements_met']
    assert option['essential_shortage_reduction_kwh']==pytest.approx(1.)
    assert option['metrics']['flexible_completed_kwh']==pytest.approx(1.)
    assert d['reference']['equipment']==case()['clinic']['equipment']
    assert 'clinical safety' in d['summary']


def test_solar_capacity_candidates_resolve_generation_shortage_with_same_empty_battery():
    d=evaluate(case(pv_capacity_kw=.1,initial_battery_kwh=0.,equipment=[critical(1.,[12])])|{'focus':'solar'})
    candidates=[o for o in d['options'] if o['kind']=='solar']
    assert len(candidates)==3
    assert any(o['modeled_all_requirements_met'] for o in candidates)
    for o in candidates:
        assert o['config']['initial_battery_kwh']==0
        assert o['plan']['metrics']['critical_requested_kwh']==1
        assert [c['field'] for c in o['infrastructure_changes']]==['pv_capacity_kw']


def test_storage_limited_case_improves_without_invented_initial_charge():
    d=evaluate(case(pv_capacity_kw=2.,initial_battery_kwh=1.,equipment=[critical(3.)])|{'focus':'battery'})
    assert next(o for o in d['options'] if o['id']=='reschedule')['metrics']['essential_unserved_kwh']==pytest.approx(1.)
    assert any(o['modeled_all_requirements_met'] for o in d['options'])
    assert all(o['config']['initial_battery_kwh']==1. for o in d['options'])


def test_output_bottleneck_is_resolved_by_power_not_empty_storage():
    body=case(pv_capacity_kw=0.,battery_capacity_kwh=8.,initial_battery_kwh=8.,max_discharge_kw=1.,equipment=[critical(3.)])
    d=evaluate(body)
    assert 'DISCHARGE_POWER_LIMIT' in d['reference']['diagnosis']['constraints']
    assert any(o['kind']=='output' and o['modeled_all_requirements_met'] for o in d['options'])
    batteries=[o for o in d['options'] if o['kind']=='battery']
    assert all(o['metrics']['essential_unserved_kwh']==pytest.approx(2.) for o in batteries)
    assert d['existing']['backup_deficits']==[{'hour':20,'electrical_energy_kwh':2.}]
    assert all(o['config']['initial_battery_kwh']==8. for o in d['options'])


def test_more_empty_storage_does_not_create_energy():
    d=evaluate(case(pv_capacity_kw=0.,initial_battery_kwh=1.,equipment=[critical(2.)])|{'focus':'battery'})
    assert all(o['metrics']['essential_unserved_kwh']==pytest.approx(1.) for o in d['options'])
    assert d['smallest_tested_resolving_option_id'] is None
    assert 'did not remove' in d['summary']


def test_no_tested_option_can_meet_an_extreme_all_day_shortage():
    d=evaluate(case(pv_capacity_kw=0.,initial_battery_kwh=0.,max_discharge_kw=.1,equipment=[critical(10.,list(range(24)))]))
    assert d['smallest_tested_resolving_option_id'] is None
    assert all(not o['modeled_all_requirements_met'] for o in d['options'])
    assert 'No tested option' in d['summary']
    scheduled=next(o for o in d['options'] if o['id']=='reschedule')
    assert sum(p['electrical_energy_kwh'] for p in scheduled['backup_deficits'])==pytest.approx(scheduled['metrics']['essential_unserved_kwh'])


def test_optional_work_remains_unfinished_when_explicitly_postponed():
    d=evaluate(case(pv_capacity_kw=0.,initial_battery_kwh=2.)|{'focus':'optional','optional_load_ids':['optional']})
    postponed=next(o for o in d['options'] if o['kind']=='optional')
    assert postponed['metrics']['explicitly_postponed_kwh']==1.
    assert postponed['metrics']['flexible_unfinished_kwh']==1.
    assert postponed['metrics']['tested_flexible_required_kwh']==0
    assert not postponed['modeled_all_requirements_met']
    assert postponed['metrics']['essential_requested_kwh']==2
    assert postponed['work_changes'][0]['equipment_id']=='optional'


def test_protected_equipment_cannot_be_designated_optional_before_weather_fetch():
    service,calls=service_for()
    with TestClient(create_app(forecast_service=service)) as client:
        r=client.post('/api/recovery/plan',json=case()|{'weather_mode':'live_forecast','optional_load_ids':['essential']})
    assert r.status_code==422
    assert not calls


def test_all_candidate_metrics_and_deltas_derive_from_same_live_weather_and_physics():
    d=evaluate(case()|{'weather_mode':'live_forecast','sunshine_factor':.5})
    assert d['forecast']['source']=='Open-Meteo Forecast API'
    assert d['planning_date']=='2026-11-14'
    ref=d['existing']['plan']['metrics']
    for option in d['options']:
        m=option['metrics']; raw=option['plan']['metrics']; config=option['config']
        assert m['essential_unserved_kwh']==raw['critical_unserved_kwh']
        assert m['essential_served_kwh']+m['essential_unserved_kwh']==pytest.approx(ref['critical_requested_kwh'])
        assert option['essential_shortage_reduction_kwh']==pytest.approx(ref['critical_unserved_kwh']-raw['critical_unserved_kwh'])
        assert option['minimum_battery_improvement_kwh']==pytest.approx(raw['min_soc_kwh']-ref['min_soc_kwh'])
        assert config['initial_battery_kwh']==.5
        for h in option['plan']['hourly']:
            assert h['pv_kwh']+h['discharge_output_kwh']==pytest.approx(h['critical_served_kwh']+h['flexible_served_kwh']+h['charge_input_kwh']+h['curtailed_kwh'])
            assert h['soc_end_kwh']==pytest.approx(h['soc_start_kwh']+config['charge_efficiency']*h['charge_input_kwh']-h['discharge_output_kwh']/config['discharge_efficiency'])
            assert h['pv_kwh']==pytest.approx(d['forecast']['days'][1]['hours'][h['hour']]['irradiance_kwh_m2']*config['pv_capacity_kw']*.8*.5)
    assert sorted(o['rank'] for o in d['options'])==list(range(1,len(d['options'])+1))


@pytest.mark.parametrize('mutation',[lambda p:p['hourly']['shortwave_radiation'].__setitem__(30,None),lambda p:p.update(timezone='Invalid/Zone')])
def test_invalid_weather_cannot_turn_into_a_success_or_hidden_scenario(mutation):
    payload=weather_payload();mutation(payload)
    service,_=service_for(payload)
    with TestClient(create_app(forecast_service=service)) as client:
        r=client.post('/api/recovery/plan',json=case()|{'weather_mode':'live_forecast'})
    assert r.status_code==503
    assert 'reference' not in r.json()


def test_local_agent_tool_receives_existing_context_and_executes_computed_recovery():
    service,weather=service_for()
    agent,calls=agent_with([{'name':'generate_recovery_plan','arguments':{'focus':'solar'}}])
    body=case()|{'question':'What about more solar panels?','use_configured_context':True}
    body.pop('weather_mode')
    body.pop('midnight_battery_kwh')
    with TestClient(create_app(forecast_service=service,agent_service=agent)) as client:
        r=client.post('/api/agent/ask',json=body)
    assert r.status_code==200,r.text
    d=r.json()
    assert not d['needs_clarification']
    assert d['mode']=='local_tool_agent'
    assert d['recovery']['forecast']
    assert len(weather)==1
    assert d['recovery']['reference']['effective_config']['initial_battery_kwh']==.5
    assert 'INVENTED ANSWER' not in r.text
    assert any(t['name']=='generate_recovery_plan' and t['status']=='completed' for t in d['tool_calls'])


def test_agent_multi_turn_recovery_preserves_clinic_and_selected_stress_factor():
    service,_=service_for()
    agent,_=agent_with([{'name':'generate_recovery_plan','arguments':{'focus':'battery','sunshine_factor':1.}}])
    body=case()|{'question':'Would another battery help with 50% less sunshine?',
        'previous_questions':['We expect little sunshine tomorrow. How can we keep our clinic running?'],
        'inputs_confirmed':True}
    body.pop('weather_mode')
    with TestClient(create_app(forecast_service=service,agent_service=agent)) as client:
        d=client.post('/api/agent/ask',json=body).json()
    assert d['recovery']['sunshine_factor']==.5
    assert d['recovery']['reference']['equipment']==body['clinic']['equipment']
    assert all(o['config']['initial_battery_kwh']==.5 for o in d['recovery']['options'])


def test_followup_retains_previous_sunshine_factor_without_reasking():
    service,_=service_for()
    agent,_=agent_with([{'name':'generate_recovery_plan','arguments':{'focus':'solar'}}])
    body=request_body()|{'question':'What about more solar panels?','use_configured_context':True,'context_sunshine_factor':.5}
    with TestClient(create_app(forecast_service=service,agent_service=agent)) as client:
        d=client.post('/api/agent/ask',json=body).json()
    assert not d['needs_clarification']
    assert d['recovery']['sunshine_factor']==.5


def test_active_hypothetical_requirement_is_retained_in_recovery_comparison():
    service,_=service_for()
    agent,_=agent_with([{'name':'generate_recovery_plan','arguments':{'focus':'battery'}}])
    requirement={'name':'Additional charging','power_kw':.2,'duration_hours':2,'earliest_start':10,'deadline':14}
    body=request_body()|{'question':'Would another battery help?','use_configured_context':True,'active_requirement':requirement}
    with TestClient(create_app(forecast_service=service,agent_service=agent)) as client:
        d=client.post('/api/agent/ask',json=body).json()
    assert d['recovery']
    assert 'Hypothetical additional requirement retained' in d['message']
    assert d['recovery']['reference']['optimized']['metrics']['critical_requested_kwh']==pytest.approx(5.34+.4)
    assert all(o['metrics']['essential_requested_kwh']==pytest.approx(5.34+.4) for o in d['recovery']['options'])


def test_missing_real_starting_charge_is_not_invented_from_example_defaults():
    service,weather=service_for()
    agent,calls=agent_with()
    body=request_body()|{'question':'Plan tomorrow','midnight_battery_kwh':None,'use_configured_context':True,
        'input_basis':'operator_entered_unverified'}
    with TestClient(create_app(forecast_service=service,agent_service=agent)) as client:
        d=client.post('/api/agent/ask',json=body).json()
    assert d['needs_clarification']
    assert not calls and not weather


def test_invalid_initial_bounds_rejected_before_network():
    service,calls=service_for()
    with TestClient(create_app(forecast_service=service)) as client:
        r=client.post('/api/recovery/plan',json=case()|{'midnight_battery_kwh':10.,'weather_mode':'live_forecast'})
    assert r.status_code==422
    assert not calls


def test_historical_recovery_demo_computes_every_result_and_never_calls_weather():
    service,calls=service_for()
    with TestClient(create_app(forecast_service=service)) as client:
        body=client.get('/api/demos/recovery').json()['request']
        r=client.post('/api/recovery/plan',json=body)
    assert r.status_code==200,r.text
    d=r.json()
    assert not calls
    assert d['forecast'] is None
    assert d['planning_date']=='2025-01-14'
    assert d['reference']['weather_dataset']=='kisumu-2025-01-14'
    assert d['existing']['metrics']['essential_unserved_kwh']==pytest.approx(1.32)
    assert any(o['kind']=='output' and o['modeled_all_requirements_met'] for o in d['options'])


def test_failed_candidate_never_publishes_a_partial_success(monkeypatch):
    from app import recovery_planner
    from app.optimizer import SolverError
    original=recovery_planner.forecast_case
    invocations=[]
    def failing(*args):
        invocations.append(True)
        if len(invocations)>1:
            raise SolverError('SOLVER_TIME_LIMIT','private solver output')
        return original(*args)
    monkeypatch.setattr(recovery_planner,'forecast_case',failing)
    service,_=service_for()
    with TestClient(create_app(forecast_service=service)) as client:
        r=client.post('/api/recovery/plan',json=case()|{'weather_mode':'live_forecast'})
    assert r.status_code==503
    assert r.json()['error']['code']=='SOLVER_TIME_LIMIT'
    assert 'private solver output' not in r.text
    assert 'options' not in r.json()


def test_model_limit_saturation_and_zero_demand_do_not_claim_reliability():
    d=evaluate(case(battery_capacity_kwh=200.,pv_capacity_kw=100.,max_discharge_kw=100.,equipment=[]))
    assert len(d['options'])==1
    assert not d['options'][0]['modeled_essential_and_reserve_met']
    assert d['smallest_tested_resolving_option_id'] is None
    assert 'NO_ESSENTIAL_REQUIREMENTS_CONFIGURED' in d['options'][0]['remaining_constraints']


def test_streamed_recovery_reports_completed_calculations_and_verified_result():
    service,_=service_for()
    agent,_=agent_with([{'name':'generate_recovery_plan','arguments':{'focus':'output'}}])
    with TestClient(create_app(forecast_service=service,agent_service=agent)) as client:
        response=client.post('/api/agent/stream',json=request_body()|{'question':'Would higher output fix the shortage?','inputs_confirmed':True})
    events=[json.loads(line[6:]) for line in response.text.splitlines() if line.startswith('data: ')]
    assert events[-1]['type']=='answer'
    assert events[-1]['response']['recovery']
    activities=[e for e in events if e['type']=='activity']
    assert any(e['id']=='recovery-weather' and e['status']=='completed' for e in activities)
    outputs=[e for e in activities if e['id'].startswith('output-')]
    assert len([e for e in outputs if e['status']=='running'])==len([e for e in outputs if e['status']=='completed'])==3
