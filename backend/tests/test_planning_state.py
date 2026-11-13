"""Revisioned activity workflows run the real simulator/MILP, never canned energy."""
import asyncio
import json
from copy import deepcopy
import pytest
from fastapi.testclient import TestClient
from app.main import create_app
from app.planning_state import PlanningStore
from app.planning_models import (ActivityDraft, CreatePlanningSession, CreateActivityProposal, ConfirmActivityProposal,
    UpdateActivityProposal, RecomputePlanningState)
from app.scenarios import load_catalog
from app.forecast_models import ForecastLocation
from test_weather_forecast import service_for
from test_local_agent import agent_with

BASE = '/api/planning/sessions'


def initial():
    return {'selected_clinic_id':'reviewed-clinic','clinic_name':'Operator clinic',
        'location':{'latitude':-.0917,'longitude':34.768},'planning_date':'2026-11-14',
        'midnight_battery_kwh':2.,'clinic':{'scenario':'normal', 'battery_capacity_kwh':4.,
        'initial_battery_kwh':2.,'reserve_kwh':.5,'pv_capacity_kw':1.,
        'charge_efficiency':.9,'discharge_efficiency':.9,'max_charge_kw':2.,'max_discharge_kw':2.,
        'equipment':[{'id':'fridge','name':'Vaccine refrigerator','category':'critical','power_kw':.1,'required_hours':list(range(24))},
            {'id':'pump','name':'Water pump','category':'flexible','max_power_kw':.5,'required_energy_kwh':1.,
             'allowed_hours':list(range(8,17)),'baseline_allocations':[{'hour':8,'requested_kwh':.5},{'hour':9,'requested_kwh':.5}],'divisible':True}]}}


def details(**changes):
    return {'name':'Vaccination campaign','planning_date':'2026-11-14','start_hour':10,'end_hour':15,
        'equipment_ids':['fridge']} | changes


def post(client, path, payload):
    r=client.post(path,json=payload)
    assert r.status_code==200,r.text
    return r.json()


def create(client):
    return post(client,BASE,initial())


def test_returned_clinic_configuration_matches_the_strict_public_contract():
    from app.planning_models import PlanningState
    service,_=service_for()
    with TestClient(create_app(forecast_service=service)) as c:
        state=create(c)
        assert all(value is not None for value in state['clinic'].values())
        # The same serialized state can be validated and the clinic reused in
        # another explicitly created session, without invalid null sentinels.
        PlanningState.model_validate_json(json.dumps(state))
        fresh=post(c,BASE,initial()|{'clinic':state['clinic']})
        assert fresh['equipment_inventory']==state['equipment_inventory']


def propose(client,state,**changes):
    return post(client,f"{BASE}/{state['id']}/proposals",{'expected_revision':state['revision'],'details':details(**changes)})


def confirm(client,state,key='click-001',proposal=None):
    return post(client,f"{BASE}/{state['id']}/proposals/{proposal or state['active_proposal_id']}/confirm",
        {'expected_revision':state['revision'],'idempotency_key':key})


def test_partial_draft_corrections_same_id_then_single_idempotent_confirmation():
    service,weather=service_for()
    with TestClient(create_app(forecast_service=service)) as c:
        s=create(c)
        s=post(c,f"{BASE}/{s['id']}/proposals",{'expected_revision':0,'details':{'name':'Vaccination campaign'}})
        pid=s['active_proposal_id']; assert s['input_revision']==0
        assert 'start_hour' in s['proposals'][0]['missing_fields']
        for patch in ({'start_hour':9},{'start_hour':10},{'planning_date':'2026-11-14','end_hour':15,'equipment_ids':['fridge']}):
            r=c.patch(f"{BASE}/{s['id']}/proposals/{pid}",json={'expected_revision':s['revision'],'details':patch})
            assert r.status_code==200,r.text
            s=r.json(); assert s['active_proposal_id']==pid
        assert len(s['proposals'])==1 and not weather
        s=confirm(c,s)
        assert len(s['confirmed_activities'])==1
        assert s['confirmed_activities'][0]['details']['start_hour']==10
        assert s['plan_status']=='current'
        assert s['computed_plan']['input_revision']==s['input_revision']==1
        assert len(s['computed_plan']['simulation']['equipment'])==2
        assert s['computed_plan']['simulation']['optimized']['metrics']['critical_requested_kwh']==pytest.approx(2.4)
        rev=s['revision']; generation=s['computed_plan']['generation']
        for key in ('click-001','different-key'):
            duplicate=post(c,f"{BASE}/{s['id']}/proposals/{pid}/confirm",{'expected_revision':0,'idempotency_key':key})
            assert duplicate['revision']==rev
            assert len(duplicate['confirmed_activities'])==1
            assert duplicate['computed_plan']['generation']==generation


def test_proposals_dont_change_plan_rejection_and_revision_conflict():
    service,_=service_for()
    with TestClient(create_app(forecast_service=service)) as c:
        s=create(c)
        s=post(c,f"{BASE}/{s['id']}/recompute",{'expected_revision':0})
        plan=deepcopy(s['computed_plan'])
        s=propose(c,s)
        assert s['computed_plan']==plan
        pid=s['active_proposal_id']
        r=c.patch(f"{BASE}/{s['id']}/proposals/{pid}",json={'expected_revision':0,'details':{'start_hour':11}})
        assert r.status_code==409 and r.json()['error']['code']=='REVISION_CONFLICT'
        s=post(c,f"{BASE}/{s['id']}/proposals/{pid}/reject",{'expected_revision':s['revision']})
        assert s['proposals'][0]['status']=='rejected'
        assert s['computed_plan']==plan and not s['confirmed_activities']
        r=c.post(f"{BASE}/{s['id']}/proposals/{pid}/confirm",json={'expected_revision':s['revision'],'idempotency_key':'rejected'})
        assert r.status_code==409


def test_missing_power_specs_not_defaulted_and_confirmation_atomic():
    service,weather=service_for()
    with TestClient(create_app(forecast_service=service)) as c:
        s=propose(c,create(c),equipment_ids=['new-light'],additional_equipment=[{'id':'new-light','name':'Campaign light','category':'critical','required_hours':[10,11]}])
        assert 'additional_equipment.0.power_kw' in s['proposals'][0]['missing_fields']
        r=c.post(f"{BASE}/{s['id']}/proposals/{s['active_proposal_id']}/confirm",json={'expected_revision':s['revision'],'idempotency_key':'missing'})
        assert r.status_code==422 and r.json()['error']['code']=='PROPOSAL_INCOMPLETE'
        current=c.get(f"{BASE}/{s['id']}").json()
        assert current==s and not weather
        r=c.patch(f"{BASE}/{s['id']}/proposals/{s['active_proposal_id']}",json={'expected_revision':s['revision'],'details':{
            'additional_equipment':[{'id':'new-light','name':'Campaign light','category':'critical','power_kw':.2,'required_hours':[10,11]}]}})
        assert r.status_code==200,r.text
        s=confirm(c,r.json())
        assert s['computed_plan']['simulation']['optimized']['metrics']['critical_requested_kwh']==pytest.approx(2.8)
        assert len(s['equipment_inventory'])==3


def test_shared_equipment_constraints_union_and_confirmed_weather_recovery_preserves_demand():
    service,weather=service_for()
    body=initial(); body['clinic']['equipment'][0]['required_hours']=[10]
    with TestClient(create_app(forecast_service=service)) as c:
        s=post(c,BASE,body)
        for name,hours in [('Campaign A',[10,11]),('Campaign B',[11,12])]:
            s=propose(c,s,name=name,equipment_constraints=[{'equipment_id':'fridge','required_hours':hours}])
            s=confirm(c,s,key=name)
        raw=s['computed_plan']['simulation']
        assert raw['equipment'][0]['required_hours']==[10,11,12]
        assert raw['optimized']['metrics']['critical_requested_kwh']==pytest.approx(.3)
        original_solar=raw['optimized']['metrics']['total_solar_kwh']
        s=post(c,f"{BASE}/{s['id']}/recompute",{'expected_revision':s['revision'],'sunshine_factor':.5,'include_recovery':True})
        assert len(s['confirmed_activities'])==2
        plan=s['computed_plan']; assert plan['input_revision']==s['input_revision']
        assert plan['simulation']['optimized']['metrics']['total_solar_kwh']==pytest.approx(original_solar*.5)
        assert plan['recovery']['reference']['optimized']['metrics']['critical_requested_kwh']==pytest.approx(.3)
        assert all(o['metrics']['essential_requested_kwh']==pytest.approx(.3) for o in plan['recovery']['options'])
        s=post(c,f"{BASE}/{s['id']}/recompute",{'expected_revision':s['revision']})
        assert s['sunshine_factor']==.5 and s['computed_plan']['sunshine_factor']==.5


@pytest.mark.parametrize('change',[
    {'equipment_ids':['unknown']},
    {'equipment_constraints':[{'equipment_id':'fridge','allowed_hours':[10]}]},
    {'equipment_ids':['pump'],'equipment_constraints':[{'equipment_id':'pump','allowed_hours':[1]}]},
    {'equipment_constraints':[{'equipment_id':'fridge','required_hours':[9]}]},
    {'start_hour':15,'end_hour':10},
    {'duration_hours':8},
    {'additional_equipment':[{'id':'fridge','name':'Replacement fridge','category':'critical','power_kw':.01,'required_hours':[10]}]},
])
def test_invalid_or_protected_constraints_rejected_without_mutation(change):
    service,weather=service_for()
    with TestClient(create_app(forecast_service=service)) as c:
        s=create(c)
        r=c.post(f"{BASE}/{s['id']}/proposals",json={'expected_revision':0,'details':details(**change)})
        assert r.status_code==422,r.text
        assert c.get(f"{BASE}/{s['id']}").json()==s and not weather


def test_combined_flexible_window_capacity_cannot_destroy_confirmed_work():
    service,_=service_for()
    with TestClient(create_app(forecast_service=service)) as c:
        s=propose(c,create(c),equipment_ids=['pump'],equipment_constraints=[{'equipment_id':'pump','allowed_hours':[10]}])
        r=c.post(f"{BASE}/{s['id']}/proposals/{s['active_proposal_id']}/confirm",json={'expected_revision':s['revision'],'idempotency_key':'impossible'})
        assert r.status_code==422
        assert c.get(f"{BASE}/{s['id']}").json()==s


def test_reviewed_confirmed_updates_version_conflict_and_key_reuse():
    service,_=service_for()
    with TestClient(create_app(forecast_service=service)) as c:
        s=confirm(c,propose(c,create(c)))
        aid=s['confirmed_activities'][0]['id']
        pids=[]
        for start in (11,12):
            s=post(c,f"{BASE}/{s['id']}/proposals",{'expected_revision':s['revision'],'target_activity_id':aid,'details':{'start_hour':start}})
            pids.append(s['active_proposal_id'])
        s=confirm(c,s,key='revision-1',proposal=pids[0])
        assert s['confirmed_activities'][0]['id']==aid
        assert s['confirmed_activities'][0]['version']==2
        assert s['confirmed_activities'][0]['details']['start_hour']==11
        for key,code in [('revision-1','IDEMPOTENCY_CONFLICT'),('revision-2','REVISION_CONFLICT')]:
            r=c.post(f"{BASE}/{s['id']}/proposals/{pids[1]}/confirm",json={'expected_revision':s['revision'],'idempotency_key':key})
            assert r.status_code==409 and r.json()['error']['code']==code


def test_weather_failure_after_confirmation_keeps_activity_and_discards_old_result():
    service,_=service_for()
    with TestClient(create_app(forecast_service=service)) as c:
        s=create(c)
        s=post(c,f"{BASE}/{s['id']}/recompute",{'expected_revision':0})
        assert s['computed_plan']
        async def failed(_):
            raise RuntimeError('secret provider internals')
        service.get=failed
        s=confirm(c,propose(c,s))
        assert len(s['confirmed_activities'])==1
        assert s['computed_plan'] is None and s['forecast_reference'] is None
        assert s['plan_status']=='failed' and s['plan_error']=='CALCULATION_UNAVAILABLE'
        assert 'secret' not in json.dumps(s)


def test_old_weather_result_cannot_overwrite_new_confirmed_input_or_new_generation():
    async def scenario():
        catalog=load_catalog(); store=PlanningStore(); lock=asyncio.Lock()
        service,_=service_for()
        snapshot=await service.get(ForecastLocation(latitude=-.0917,longitude=34.768))
        entered=asyncio.Event(); released=asyncio.Event()
        class Slow:
            async def get(self,_):
                entered.set(); await released.wait(); return snapshot
        s=await store.create(CreatePlanningSession.model_validate_json(json.dumps(initial())),catalog)
        old=asyncio.create_task(store.recompute(s.id,RecomputePlanningState(expected_revision=0),catalog,Slow(),lock))
        await entered.wait()
        s=store.read(s.id)
        s=await store.propose(s.id,CreateActivityProposal(expected_revision=s.revision,details=ActivityDraft.model_validate_json(json.dumps(details()))))
        s,changed=await store.confirm(s.id,s.active_proposal_id,ConfirmActivityProposal(expected_revision=s.revision,idempotency_key='new'))
        assert changed and s.computed_plan is None
        fresh=await store.recompute(s.id,RecomputePlanningState(expected_revision=s.revision,sunshine_factor=.5),catalog,service,lock)
        released.set(); await old
        final=store.read(s.id)
        assert final.computed_plan==fresh.computed_plan
        assert final.computed_plan.input_revision==final.input_revision==2
        assert final.sunshine_factor==.5
    asyncio.run(scenario())


def test_recovery_selection_requires_current_comparison_generation():
    service,_=service_for()
    with TestClient(create_app(forecast_service=service)) as c:
        s=create(c)
        s=post(c,f"{BASE}/{s['id']}/recompute",{'expected_revision':0,'include_recovery':True})
        plan=s['computed_plan']
        select={'expected_revision':s['revision'],'input_revision':s['input_revision'],'generation':plan['generation'],'option_id':'reschedule'}
        s=post(c,f"{BASE}/{s['id']}/recovery-selection",select)
        assert s['selected_recovery_intervention_id']=='reschedule'
        s=post(c,f"{BASE}/{s['id']}/recompute",{'expected_revision':s['revision'],'include_recovery':True})
        select['expected_revision']=s['revision']
        r=c.post(f"{BASE}/{s['id']}/recovery-selection",json=select)
        assert r.status_code==409 and r.json()['error']['code']=='STALE_RESULT'
        assert s['selected_recovery_intervention_id'] is None
