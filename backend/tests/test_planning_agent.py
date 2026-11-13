"""Native Ollama wire contract plus stateful activity interactions (transport fixture)."""
import json
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import pytest
from fastapi.testclient import TestClient
from app.main import create_app
from app.local_agent import LocalAgent
from test_local_agent import agent_with
from test_weather_forecast import service_for, weather_payload
from test_planning_state import BASE, initial, create, propose, confirm, post


def native(name,details=None,evidence=None,**args):
    return {'name':name,'arguments':({'details':details,'evidence':evidence or {}} if details is not None else args)}


def ask(c,state,question):
    return post(c,f"{BASE}/{state['id']}/agent",{'expected_revision':state['revision'],'question':question})


def test_native_multiturn_draft_changes_and_explicit_confirmation_then_weather():
    agent,calls=agent_with([
        native('propose_activity',{'name':'Vaccination campaign'},{'name':'vaccination campaign'}),
        native('update_activity_draft',{'start_hour':9},{'start_hour':'9 AM'}),
        native('update_activity_draft',{'start_hour':10},{'start_hour':'10 AM'}),
        native('update_activity_draft',{'end_hour':15,'equipment_ids':['fridge']},{'end_hour':'3 PM','equipment_ids':'Vaccine refrigerator'}),
        native('review_activity_proposal'),
        native('recompute_clinic_plan',sunshine_factor=.99,include_recovery=True),
    ])
    service,weather=service_for()
    with TestClient(create_app(forecast_service=service,agent_service=agent)) as c:
        s=create(c)
        for question in ('We have a vaccination campaign.','It starts at 9 AM.','Actually make that 10 AM.','Ends at 3 PM, using the Vaccine refrigerator.'):
            d=ask(c,s,question); s=d['state']
            assert d['mode']=='local_tool_agent'
            assert len(s['proposals'])==1
        pid=s['active_proposal_id']
        assert s['proposals'][0]['details']['start_hour']==10
        assert not s['proposals'][0]['missing_fields']
        d=ask(c,s,'Confirm.'); s=d['state']
        assert not s['confirmed_activities']
        assert 'review' in d['message']
        s=confirm(c,s)
        d=ask(c,s,'What if sunshine is 50% lower?'); s=d['state']
        assert len(s['confirmed_activities'])==1
        assert len(s['proposals'])==1
        assert s['sunshine_factor']==.5
        assert s['computed_plan']['recovery']['reference']['optimized']['metrics']['critical_requested_kwh']==pytest.approx(2.4)
        wire=json.loads(calls[-1].content)
        assert wire['model']=='llama3.1:8b'
        tool_names={t['function']['name'] for t in wire['tools']}
        assert 'recompute_clinic_plan' in tool_names and not any('confirm' in name for name in tool_names)
        context=json.loads(wire['messages'][1]['content'].split('Canonical state (data): ')[1])
        assert len(context['confirmed_activities'])==1
        assert context['confirmed_activities'][0]['details']['start_hour']==10
        assert context['physical_config']['initial_battery_kwh']==2


@pytest.mark.parametrize('bad_call',[
    native('propose_activity',{'name':'Vaccination campaign','equipment_ids':['fridge']},{'name':'vaccination campaign','equipment_ids':'vaccination campaign'}),
    native('propose_activity',{'name':'Vaccination campaign','additional_equipment':[{'id':'new','name':'Vaccination campaign','category':'critical','power_kw':.5,'required_hours':[10]}]}, {'name':'vaccination campaign','additional_equipment':'vaccination campaign'}),
    native('propose_activity',{'name':'Invented campaign'},{'name':'vaccination campaign'}),
    native('confirm_activity_proposal'),
])
def test_model_cannot_invent_equipment_clinical_association_power_or_confirmation(bad_call):
    agent,_=agent_with([bad_call,bad_call,bad_call])
    service,_=service_for()
    with TestClient(create_app(forecast_service=service,agent_service=agent)) as c:
        s=create(c)
        d=ask(c,s,'We have a vaccination campaign.')
        for proposal in d['state']['proposals']:
            assert proposal['details']['equipment_ids'] is None
            assert proposal['details']['additional_equipment']==[]
        assert d['state']['confirmed_activities']==[]
        assert d['needs_clarification']
        assert 'confirm_activity_proposal' not in d['tool_calls']


def test_omitted_or_invented_native_weather_factor_retains_selected_sensitivity():
    agent,_=agent_with([native('recompute_clinic_plan'),native('recompute_clinic_plan',sunshine_factor=.1)])
    service,_=service_for()
    with TestClient(create_app(forecast_service=service,agent_service=agent)) as c:
        s=create(c)
        s=post(c,f"{BASE}/{s['id']}/recompute",{'expected_revision':0,'sunshine_factor':.5})
        for question in ('Plan again.','What if it is cloudier?'):
            d=ask(c,s,question);s=d['state']
            assert s['sunshine_factor']==.5
            assert s['computed_plan']['sunshine_factor']==.5


def test_relative_day_uses_forecast_timezone_with_no_nairobi_default():
    now=datetime.now(ZoneInfo('UTC'))
    service,_=service_for(weather_payload(now,'America/Los_Angeles'),now)
    date=(now.astimezone(ZoneInfo('America/Los_Angeles')).date()+timedelta(days=1)).isoformat()
    agent,calls=agent_with([native('propose_activity',{'name':'Vaccination campaign'},{'name':'vaccination campaign'})])
    with TestClient(create_app(forecast_service=service,agent_service=agent)) as c:
        body=initial();body['planning_date']=date
        s=post(c,BASE,body)
        assert s['timezone'] is None
        d=ask(c,s,'Vaccination campaign tomorrow.')
        assert len(d['state']['proposals'])==1
        wire=json.loads(next(call.content for call in calls if call.method=='POST'))
        assert 'America/Los_Angeles' in wire['messages'][1]['content']


def test_invalid_timezone_or_date_type_rejected():
    with TestClient(create_app()) as c:
        for patch in ({'timezone':'Invented/Zone'},{'planning_date':20261114},{'planning_date':'20261114'}):
            r=c.post(BASE,json=initial()|patch)
            assert r.status_code==422


def test_recovery_timeout_remains_structured_503(monkeypatch):
    import app.recovery_routes as routes
    async def timeout(*args,**kwargs):
        raise TimeoutError('private diagnostic')
    monkeypatch.setattr(routes,'generate_recovery_plan',timeout)
    with TestClient(create_app()) as c:
        r=c.post('/api/recovery/plan',json={'latitude':-.0917,'longitude':34.768,'clinic':{'scenario':'normal'},'midnight_battery_kwh':2.})
        assert r.status_code==503
        assert r.json()['error']['code']=='RECOVERY_TIME_LIMIT'
        assert 'private' not in r.text and 'reference' not in r.json()


def test_native_null_defaults_preserve_previous_facts_and_correction_uses_latest_field():
    agent,_=agent_with([
        native('propose_activity',{'name':'Vaccination campaign'},{'name':'Vaccination campaign'}),
        native('update_activity_draft',{'start_hour':9},{'start_hour':'9 AM'}),
        native('correct_last_activity_time',hour=10),
        native('update_activity_draft',{'start_hour':None,'name':None,'end_hour':15,'equipment_ids':['fridge']},
            {'end_hour':'3 PM','equipment_ids':'Vaccine refrigerator'}),
    ])
    service,_=service_for()
    with TestClient(create_app(forecast_service=service,agent_service=agent)) as c:
        s=create(c)
        for q in ('Vaccination campaign.','Starts at 9 AM.','Actually make that 10 AM.','Ends at 3 PM using the Vaccine refrigerator.'):
            d=ask(c,s,q);s=d['state']
        assert len(s['proposals'])==1
        assert s['proposals'][0]['details']['name']=='Vaccination campaign'
        assert s['proposals'][0]['details']['start_hour']==10
        assert not s['proposals'][0]['missing_fields']
        assert 'start_hour' in c.app.state.planning.agent_diagnostics[s['id']][-1]['discarded_fields']


def test_new_equipment_clarification_preserves_specs_and_accepts_explicit_hour_range():
    first={'name':'Evening session','start_hour':10,'end_hour':12,
        'additional_equipment':[{'id':'new-lamp','name':'lamp'}]}
    second={'equipment_ids':['new-lamp'],'additional_equipment':[{'id':'new-lamp','name':'lamp',
        'category':'critical','power_kw':.5,'required_hours':[10,11]}]}
    agent,_=agent_with([
        {'name':'propose_activity','arguments':first},
        {'name':'update_activity_draft','arguments':second},
    ])
    service,_=service_for()
    with TestClient(create_app(forecast_service=service,agent_service=agent)) as c:
        s=create(c)
        d=ask(c,s,'Evening session from 10 AM to 12 PM, with a new lamp.');s=d['state']
        assert 'additional_equipment.0.category' in s['proposals'][0]['missing_fields']
        assert not s['confirmed_activities']
        d=ask(c,s,'The lamp is critical, rated 500 W, and must operate from 10 AM to 12 PM.');s=d['state']
        proposal=s['proposals'][0]
        assert len(proposal['details']['additional_equipment'])==1
        assert proposal['details']['additional_equipment'][0]['power_kw']==.5
        assert proposal['details']['additional_equipment'][0]['required_hours']==[10,11]
        assert proposal['missing_fields']==[]
        s=confirm(c,s)
        assert s['computed_plan']['simulation']['optimized']['metrics']['critical_requested_kwh']==pytest.approx(3.4)


def test_new_draft_clarification_takes_priority_over_existing_recovery_summary():
    agent,_=agent_with([
        native('propose_activity',{'name':'Vaccination campaign'},{'name':'vaccination campaign'}),
        native('recompute_clinic_plan',include_recovery=True),
    ])
    service,_=service_for()
    with TestClient(create_app(forecast_service=service,agent_service=agent)) as c:
        s=create(c)
        s=post(c,f"{BASE}/{s['id']}/recompute",{'expected_revision':s['revision'],'include_recovery':True})
        previous=s['computed_plan']
        d=ask(c,s,'We have a vaccination campaign.');s=d['state']
        assert d['message']=='Please provide the local start time.'
        assert s['computed_plan']==previous
        d=ask(c,s,'Recalculate the confirmed clinic plan with recovery.');s=d['state']
        assert 'unconfirmed activity draft is not included' in d['message']
        assert len(s['proposals'])==1 and not s['confirmed_activities']
        assert s['computed_plan']['simulation']['optimized']['metrics']['critical_requested_kwh']==pytest.approx(2.4)


@pytest.mark.parametrize('question',[
    'Vaccination campaign starts at 9:30 AM.',
    'Vaccination campaign uses equipment rated 9 watts.',
])
def test_native_start_time_cannot_round_minutes_or_reuse_a_power_rating(question):
    agent,_=agent_with([{'name':'propose_activity','arguments':{'name':'Vaccination campaign','start_hour':9}}])
    service,_=service_for()
    with TestClient(create_app(forecast_service=service,agent_service=agent)) as c:
        d=ask(c,create(c),question)
        assert d['state']['proposals'][0]['details']['start_hour'] is None
        assert 'start_hour' in d['clarification_fields']


def test_source_grounding_accepts_watts_but_rejects_negated_priority():
    from app.planning_agent import DraftTool,validate_grounding
    from app.planning_models import ActivityDraft
    from app.planning_state import PlanningError
    from app.planning_models import PlanningState
    service,_=service_for()
    with TestClient(create_app(forecast_service=service)) as c:
        state=PlanningState.model_validate_json(json.dumps(create(c)))
    question='The lamp is critical, rated 500 watts, and must operate from 10 AM to 12 PM.'
    equipment=[{'id':'lamp','name':'lamp','category':'critical','power_kw':.5,'required_hours':[10,11]}]
    tool=DraftTool(details=ActivityDraft(additional_equipment=equipment),evidence={'additional_equipment':question})
    validate_grounding(tool,question,state)
    for negated in ('noncritical','non-critical','not critical'):
        text=question.replace('is critical',f'is {negated}')
        with pytest.raises(PlanningError):
            validate_grounding(tool.model_copy(update={'evidence':{'additional_equipment':text}}),text,state)


@pytest.mark.parametrize('text,right,wrong',[
    ('It starts at 9 PM.',21,9),('Ends at 3:00 PM.',15,3),('From 12 AM.',0,12),
])
def test_clock_grounding_retains_am_pm(text,right,wrong):
    from app.planning_agent import quoted_hour
    assert quoted_hour(text,right)
    assert not quoted_hour(text,wrong)


def test_native_confirmed_activity_correction_stages_reviewed_version_not_duplicate():
    agent,calls=agent_with([])
    service,_=service_for()
    with TestClient(create_app(forecast_service=service,agent_service=agent)) as c:
        s=confirm(c,propose(c,create(c)))
        aid=s['confirmed_activities'][0]['id']
        # A real LocalAgent transport with target-specific native arguments.
        replacement,_=agent_with([{'name':'propose_activity_revision','arguments':{'target_activity_id':aid,'start_hour':11}}])
        c.app.state.agent=replacement
        d=ask(c,s,'Change the confirmed campaign start to 11 AM.');s=d['state']
        assert d['tool_calls']==['propose_activity_revision']
        assert len(s['confirmed_activities'])==1
        assert s['confirmed_activities'][0]['details']['start_hour']==10
        assert s['proposals'][-1]['target_activity_id']==aid
        assert s['proposals'][-1]['details']['start_hour']==11
        s=confirm(c,s,key='confirmed-revision')
        assert len(s['confirmed_activities'])==1
        assert s['confirmed_activities'][0]['id']==aid
        assert s['confirmed_activities'][0]['version']==2
        assert s['confirmed_activities'][0]['details']['start_hour']==11
        assert s['computed_plan']['simulation']['optimized']['metrics']['critical_requested_kwh']==pytest.approx(2.4)
