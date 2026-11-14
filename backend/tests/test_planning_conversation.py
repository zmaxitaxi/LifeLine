"""Native prose stays social or references source-backed complete fact clauses."""
import json
import pytest
from fastapi.testclient import TestClient
from app.main import create_app
from app.planning_conversation import validate_conversation, render_grounded_reply
from app.planning_state import PlanningError
from test_local_agent import agent_with
from test_weather_forecast import service_for
from test_planning_state import create, propose, post, BASE
from test_planning_agent import ask


def conversation(kind,message):
    return {'name':'conversational_reply','arguments':{'kind':kind,'message':message}}


@pytest.mark.parametrize('question,kind,message',[
    ('Hello','greeting','Hello! How can I help with your clinic planning?'),
    ('Thanks','thanks',"You're welcome! Let me know what you would like to explore next."),
    ('What can you help me with?','help','I can help draft clinic activities, review equipment requirements and compare modeled energy plans.'),
])
def test_social_native_reply_is_model_text_without_weather_or_state_mutation(question,kind,message):
    agent,calls=agent_with([conversation(kind,message)])
    service,weather=service_for()
    with TestClient(create_app(forecast_service=service,agent_service=agent)) as c:
        s=propose(c,create(c))
        before=s
        d=ask(c,s,question)
        assert d['message']==message
        assert d['mode']=='local_tool_agent' and not d['needs_clarification']
        assert d['tool_calls']==['conversational_reply']
        assert d['state']==before and not weather
        assert c.get(f"{BASE}/{s['id']}").json()==before
        sent=json.loads(next(call.content for call in calls if call.method=='POST'))
        assert {t['function']['name'] for t in sent['tools']}=={'conversational_reply'}


@pytest.mark.parametrize('message',[
    'You have 9999 kWh of energy.', 'Your clinic has enough power.',
    'The clinic is safe tomorrow.', 'Turn off the refrigerator.',
    'Your battery will last through the night.', 'All loads are met.',
    'I confirmed your campaign.', 'Buy another battery.',
])
def test_unsafe_social_prose_is_rejected_and_retry_has_no_side_effects(message):
    good='Hello! How can I help with your clinic planning?'
    agent,_=agent_with([conversation('greeting',message),conversation('greeting',good)])
    service,weather=service_for()
    with TestClient(create_app(forecast_service=service,agent_service=agent)) as c:
        s=create(c);d=ask(c,s,'Hello')
        assert d['message']==good and message not in d['message']
        assert d['state']==s and not weather


def test_conversation_cannot_bypass_calculation_for_mixed_or_operational_request():
    fake='Everything is fine at your clinic.'
    agent,_=agent_with([conversation('greeting',fake),{'name':'recompute_clinic_plan','arguments':{'include_recovery':True}}])
    service,weather=service_for()
    with TestClient(create_app(forecast_service=service,agent_service=agent)) as c:
        d=ask(c,create(c),'Hello, will we have enough electricity tomorrow? Compare recovery options.')
        assert d['tool_calls']==['recompute_clinic_plan']
        assert d['state']['plan_status']=='current' and weather
        assert fake not in d['message']
        assert d['message'].count('Tested option:')==3


@pytest.mark.parametrize('bad',[
    'Here is the answer: 99 kWh is available.',
    'Your clinic has enough power.',
    'Please review this: {{invented_fact}}',
    'Please review this: {{essential_summary}}',
])
def test_invalid_model_synthesis_returns_retry_preserving_real_result_without_canned_narrative(bad):
    calls=[{'name':'compose_planning_reply','arguments':{'message':bad,'fact_references':['essential_summary','scope']}}]*2
    agent,_=agent_with([{'name':'recompute_clinic_plan','arguments':{}}],syntheses=calls)
    service,_=service_for()
    with TestClient(create_app(forecast_service=service,agent_service=agent)) as c:
        d=ask(c,create(c),'Plan the confirmed clinic electricity.')
        assert d['mode']=='local_agent_unavailable'
        assert 'retry' in d['message']
        assert '99' not in d['message'] and bad not in d['message']
        assert d['state']['plan_status']=='current'
        assert d['state']['computed_plan']['simulation']['optimized']['metrics']['critical_requested_kwh']==pytest.approx(2.4)
        assert d['tool_calls']==['recompute_clinic_plan']


def test_synthesis_transport_failure_preserves_draft_and_explicitly_requests_retry():
    agent,_=agent_with([{'name':'propose_activity','arguments':{'name':'Vaccination campaign'}}],synthesis_failure=500)
    service,weather=service_for()
    with TestClient(create_app(forecast_service=service,agent_service=agent)) as c:
        d=ask(c,create(c),'We have a Vaccination campaign.')
        assert len(d['state']['proposals'])==1 and not d['state']['confirmed_activities']
        assert d['mode']=='local_agent_unavailable' and 'retry' in d['message']
        assert not weather and 'private' not in d['message']


def test_grounded_synthesis_requires_distinct_actual_recovery_options_and_cannot_relabel_quantities():
    facts={'essential_summary':'Essential shortfall is 0.123 kWh.','scope':'Model comparison only.',
        'option_output':'Tested output option leaves 0.123 kWh unserved.',
        'option_battery':'Tested battery option leaves 0.012 kWh unserved.',
        'option_scheduling':'Tested scheduling option leaves 0.000 kWh unserved.'}
    required={'essential_summary','scope'};options={'option_output','option_battery','option_scheduling'}
    with pytest.raises(PlanningError):
        render_grounded_reply({'message':'Please review this.','fact_references':['essential_summary','scope','option_output','option_output','option_output']},facts,required,options)
    text=render_grounded_reply({'message':'Here is the modeled comparison. Scheduling leaves 0.000 kWh unserved. Output leaves 0.123 kWh unserved. Battery leaves 0.012 kWh unserved. Review these modeled choices.','fact_references':['essential_summary','option_scheduling','option_output','option_battery','scope']},facts,required,options)
    assert '0.123 kWh' in text and '0.012 kWh' in text and '0.000 kWh' in text
    assert text.index('Scheduling')<text.index('Output')


def test_natural_full_message_is_returned_unchanged_and_metric_label_swaps_are_rejected():
    facts={'essential_summary':'Essential equipment requests 2.000 kWh; 1.200 kWh is unserved.',
        'battery_summary':'The lowest battery level is 6.000 kWh, against a 1.000 kWh reserve target.',
        'scope':'These are modeled results for review, not a clinical guarantee.'}
    refs=list(facts)
    message='The model shows an essential shortfall of 1.200 kWh. The lowest battery level is 6.000 kWh. Please review these modeled results; they are not a clinical guarantee.'
    assert render_grounded_reply({'message':message,'fact_references':refs},facts,{'essential_summary','scope'},set())==message
    with pytest.raises(PlanningError):
        render_grounded_reply({'message':message.replace('shortfall of 1.200','shortfall of 6.000'),'fact_references':refs},facts,{'essential_summary','scope'},set())


def test_explain_exact_selected_size_reads_existing_baseline_without_weather_or_resetting_selection():
    from app.planning_conversation import fact_references,synthesis_data
    from app.planning_models import PlanningState
    service,weather=service_for()
    agent,calls=agent_with([{'name':'explain_current_plan','arguments':{}}])
    with TestClient(create_app(forecast_service=service,agent_service=agent)) as c:
        s=create(c)
        s=post(c,f"{BASE}/{s['id']}/recompute",{'expected_revision':s['revision'],'include_recovery':True})
        recovery=s['computed_plan']['recovery'];candidates=[o for o in recovery['options'] if o['kind']=='output']
        chosen=candidates[-1]
        s=post(c,f"{BASE}/{s['id']}/recovery-selection",{'expected_revision':s['revision'],'input_revision':s['input_revision'],
            'generation':s['computed_plan']['generation'],'option_id':chosen['id']})
        before=json.loads(json.dumps(s));weather_count=len(weather)
        d=ask(c,s,'Explain the exact selected plan and compare it with the existing baseline.')
        assert d['mode']=='local_tool_agent',d['message']
        assert d['tool_calls']==['explain_current_plan']
        assert d['state']==before and len(weather)==weather_count
        assert f"{chosen['config']['max_discharge_kw']:g} kW" in d['message']
        wire=json.loads(next(call.content for call in calls if call.method=='POST'))
        assert [t['function']['name'] for t in wire['tools']]==['explain_current_plan']
        facts,required,options=fact_references(PlanningState.model_validate_json(json.dumps(s)),['explain_current_plan'])
        source=synthesis_data(PlanningState.model_validate_json(json.dumps(s)),facts)
        assert source['selected_option']['exact_selected_option_id']==chosen['id']
        assert not options and 'selected_option' in required
        assert source['essential_summary']['remaining_unserved_essential_energy']==f"{s['computed_plan']['simulation']['baseline']['metrics']['critical_unserved_kwh']:.3f} kWh"


@pytest.mark.parametrize('question',[
    'Calculate recovery options and explain the updated electricity plan.',
    'Recompute the plan with the latest forecast and explain the results.',
    'Test the plan with 50% less sunshine and explain the comparison.',
])
def test_explicit_calculation_plus_explanation_is_not_forced_into_read_only_tool(question):
    service,_=service_for()
    agent,calls=agent_with([{'name':'recompute_clinic_plan','arguments':{'include_recovery':True}}])
    with TestClient(create_app(forecast_service=service,agent_service=agent)) as c:
        s=create(c)
        d=ask(c,s,question)
        assert d['mode']=='local_tool_agent',d['message']
        assert d['tool_calls']==['recompute_clinic_plan']
        assert d['state']['plan_status']=='current'
        wire=json.loads(next(call.content for call in calls if call.method=='POST'))
        assert 'recompute_clinic_plan' in {tool['function']['name'] for tool in wire['tools']}


def test_native_nurse_duration_and_priority_synonyms_leave_energy_arithmetic_to_python():
    args={'name':'Campaign','start_hour':10,'end_hour':12,'equipment_ids':['portable-pump'],
        'additional_equipment':[{'id':'portable-pump','name':'portable pump','category':'optional',
            'max_power_kw':'0.5','required_duration_hours':'2','required_energy_kwh':999.,'allowed_hours':[10,11],'divisible':True}]}
    agent,_=agent_with([{'name':'propose_activity','arguments':args}])
    service,_=service_for()
    with TestClient(create_app(forecast_service=service,agent_service=agent)) as c:
        d=ask(c,create(c),'Campaign from 10 AM to 12 PM uses a portable pump rated 500 W. The portable pump is optional, may be interrupted, and must operate for 2 hours from 10 AM to 12 PM.')
        s=d['state'];assert d['mode']=='local_tool_agent',d['message']
        item=s['proposals'][0]['details']['additional_equipment'][0]
        assert item['category']=='flexible' and item['required_duration_hours']==2
        assert item['required_energy_kwh'] is None
        assert not s['proposals'][0]['missing_fields']
        from test_planning_state import confirm
        s=confirm(c,s)
        assert next(e for e in s['equipment_inventory'] if e['id']=='portable-pump')['required_energy_kwh']==1.


def test_native_cannot_convert_event_duration_into_device_runtime_or_ignore_explicit_kwh_conflict():
    from app.planning_agent import DraftTool,validate_grounding,normalize_activity_arguments
    from app.planning_models import PlanningState,ActivityDraft
    service,_=service_for()
    with TestClient(create_app(forecast_service=service)) as c:
        state=PlanningState.model_validate_json(json.dumps(create(c)))
    question='The campaign lasts 2 hours and includes a portable pump.'
    item={'id':'portable-pump','name':'portable pump','category':'flexible','max_power_kw':.5,
        'required_duration_hours':2,'allowed_hours':[10,11],'divisible':True}
    tool=DraftTool(details=ActivityDraft(additional_equipment=[item]),evidence={'additional_equipment':question})
    with pytest.raises(PlanningError):
        validate_grounding(tool,question,state)
    args={'name':'Campaign','start_hour':10,'end_hour':12,'additional_equipment':[item|{'required_energy_kwh':2.}]}
    agent,_=agent_with([{'name':'propose_activity','arguments':args}]*3)
    with TestClient(create_app(forecast_service=service,agent_service=agent)) as c:
        s=create(c)
        d=ask(c,s,'Campaign from 10 AM to 12 PM uses a flexible portable pump rated 500 W, requiring 2 hours and 2 kWh; it is interruptible.')
        assert d['state']==s and d['mode']=='local_agent_unavailable'


def test_native_reviewed_duration_revision_reuses_known_confirmed_specs_without_rating_question():
    from test_planning_state import confirm
    service,_=service_for()
    with TestClient(create_app(forecast_service=service)) as c:
        s=create(c)
        payload={'name':'Campaign','planning_date':s['planning_date'],'start_hour':10,'end_hour':12,'equipment_ids':['portable-pump'],
            'additional_equipment':[{'id':'portable-pump','name':'portable pump','category':'flexible','max_power_kw':.5,
                'required_duration_hours':2,'allowed_hours':[10,11],'divisible':True}]}
        s=post(c,f"{BASE}/{s['id']}/proposals",{'expected_revision':s['revision'],'details':payload})
        s=confirm(c,s);aid=s['confirmed_activities'][0]['id']
        agent,_=agent_with([{'name':'propose_activity_revision','arguments':{'target_activity_id':aid,
            'additional_equipment':[{'id':'portable-pump','required_duration_hours':1}]}}])
        c.app.state.agent=agent
        d=ask(c,s,'The portable pump now needs to operate for 1 hour. Stage a reviewed change to the confirmed campaign.')
        assert d['mode']=='local_tool_agent',d['message']
        proposal=d['state']['proposals'][-1]
        item=proposal['details']['additional_equipment'][0]
        assert item['max_power_kw']==.5 and item['required_duration_hours']==1
        assert proposal['missing_fields']==[] and proposal['target_activity_id']==aid
        assert next(e for e in d['state']['equipment_inventory'] if e['id']=='portable-pump')['required_energy_kwh']==1.


def test_natural_device_hours_and_watts_are_grounded_separately_from_local_clock_time():
    from app.planning_conversation import fact_references
    from app.planning_models import PlanningState
    from app.planning_agent import DraftTool,normalize_activity_arguments,validate_grounding
    service,_=service_for()
    with TestClient(create_app(forecast_service=service)) as c:
        s=create(c)
        detail={'name':'Campaign','planning_date':s['planning_date'],'start_hour':10,'end_hour':12,'equipment_ids':['portable-pump'],
            'additional_equipment':[{'id':'portable-pump','name':'portable pump','category':'flexible','max_power_kw':.5,
                'required_duration_hours':2,'allowed_hours':[10,11],'divisible':True}]}
        s=post(c,f"{BASE}/{s['id']}/proposals",{'expected_revision':s['revision'],'details':detail})
    facts,required,options=fact_references(PlanningState.model_validate_json(json.dumps(s)),['propose_activity'])
    message='The portable pump draft specifies 500 W and 2 hours of operation, equivalent to the Python-derived requirement of 1 kWh. Please review and explicitly confirm or reject this unconfirmed draft.'
    refs=['draft_details','draft_status','review_boundary']
    assert render_grounded_reply({'message':message,'fact_references':refs},facts,required,options)==message
    with pytest.raises(PlanningError):
        render_grounded_reply({'message':message.replace('2 hours','10 hours'),'fact_references':refs},facts,required,options)


@pytest.mark.parametrize('question,expected',[
    ('vaccine campaign tomorrow',False),('The activity uses the fridge.',True),
    ('It uses the Vaccine refrigerator.',True),
])
def test_device_reference_requires_physical_identity_not_event_topic(question,expected):
    from app.planning_agent import references_device
    known={'fridge':'Vaccine refrigerator','pump':'Water pump'}
    assert references_device('fridge',known['fridge'],question,known) is expected
    assert not references_device('fridge','Vaccine refrigerator','uses the fridge',known|{'other-fridge':'Second refrigerator'})


@pytest.mark.parametrize('question,kind',[
    ('Hello, how are you?','greeting'),('Can you tell me what this app does?','help'),
])
def test_model_can_select_social_reply_for_ordinary_variants(question,kind):
    message='Hello! I can help with clinic activity planning and equipment review.'
    agent,_=agent_with([conversation(kind,message)])
    service,weather=service_for()
    with TestClient(create_app(forecast_service=service,agent_service=agent)) as c:
        s=create(c);d=ask(c,s,question)
        assert d['mode']=='local_tool_agent' and d['message']==message
        assert d['state']==s and not weather
