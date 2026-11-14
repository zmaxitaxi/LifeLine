"""Unforced native content, actual tool results and scoped presentation."""
import json
import pytest
from fastapi.testclient import TestClient
from app.main import create_app
from app.planning_conversation import render_grounded_reply, validate_reply_content
from app.planning_state import PlanningError
from app.planning_models import PlanningState
from test_local_agent import agent_with
from test_weather_forecast import service_for
from test_planning_state import create, propose, post, BASE
from test_planning_agent import ask


def conversation(kind,message):
    # Existing fixture callers now produce genuine no-tool content on the wire.
    return {'content':message}


def state_model(state):
    return PlanningState.model_validate_json(json.dumps(state))


@pytest.mark.parametrize('question,message',[
    ('Hello','Hello! What would you like to explore?'),
    ('Hello, how are things?','Hello! How can I help?'),
    ('Thanks',"You're welcome!"),
    ('Could an 8 kWh battery be an idea?','An unevaluated 8 kWh battery might help if storage is the bottleneck. Shall I compare it with the current system?'),
    ('What could adding batteries do?','Extra storage might help if storage is the bottleneck. It does not create energy; we can test the idea if you want.'),
    ('Could cloudier weather matter tomorrow?','If sunshine is lower, solar energy could be lower too. That idea has not been tested against the clinic plan.'),
])
def test_free_native_reply_has_no_forced_tool_subset_or_weather(question,message):
    agent,calls=agent_with([{'content':message}]);service,weather=service_for()
    with TestClient(create_app(forecast_service=service,agent_service=agent)) as client:
        state=create(client);reply=ask(client,state,question)
        assert reply['mode']=='local_tool_agent' and reply['message']==message
        assert reply['tool_calls']==[] and reply['state']==state and not weather
        assert reply['presentation']['kind']=='conversation'
        assert reply['presentation']['option_ids']==[] and not reply['presentation']['show_schedule']
        wire=json.loads(next(call.content for call in calls if call.method=='POST'))
        names={tool['function']['name'] for tool in wire['tools']}
        assert {'respond_to_user','recompute_clinic_plan','explain_current_plan','propose_activity'}<=names
        assert 'conversational_reply' not in names


def test_direct_clarification_can_precede_a_proposal_and_history_contains_assistant():
    first='Which device does this activity need?'
    agent,calls=agent_with([{'content':first},{'content':'Would you like to stage those details for review?'}])
    service,weather=service_for()
    with TestClient(create_app(forecast_service=service,agent_service=agent)) as client:
        state=create(client);reply=ask(client,state,'I am thinking about a campaign.')
        assert not reply['state']['proposals']
        reply=ask(client,state,'It uses the fridge.')
        wire=json.loads(calls[-1].content)
        assert {'role':'assistant','content':first} in wire['messages']
        assert not reply['state']['proposals'] and not weather


@pytest.mark.parametrize('bad',[
    'The clinic will have 9999 kWh available.', 'Your clinic has enough power.',
    'I confirmed your activity.', 'I updated your battery settings.', 'Turn off the refrigerator.',
    'Tomorrow will be rainy.', 'The model shows zero kWh of essential shortfall.',
])
def test_unsupported_direct_claim_is_rejected_without_mutation(bad):
    good='We can examine that as an unevaluated idea if you would like.'
    agent,_=agent_with([{'content':bad},{'content':good}]);service,weather=service_for()
    with TestClient(create_app(forecast_service=service,agent_service=agent)) as client:
        state=create(client);reply=ask(client,state,'Could another approach help?')
        assert reply['message']==good and reply['state']==state and not weather


def test_calculation_can_be_followed_by_direct_prose_without_a_composer_tool():
    message='The model shows 0.000 kWh of essential shortfall in the existing baseline. Please review the assumptions.'
    agent,calls=agent_with([{'name':'recompute_clinic_plan','arguments':{}}],syntheses=[{'content':message}])
    service,weather=service_for()
    with TestClient(create_app(forecast_service=service,agent_service=agent)) as client:
        reply=ask(client,create(client),'Calculate this clinic plan.')
        assert reply['mode']=='local_tool_agent' and reply['message']==message
        assert reply['tool_calls']==['recompute_clinic_plan'] and weather
        assert reply['state']['plan_status']=='current'
        assert reply['presentation']['kind']=='conversation'
        wire=json.loads(calls[-1].content)
        assert len(wire['tools'])>1 and not any(tool['function']['name']=='compose_planning_reply' for tool in wire['tools'])


def test_optional_presentation_can_show_one_tested_option_and_no_schedule():
    agent,calls=agent_with([]);service,weather=service_for()
    with TestClient(create_app(forecast_service=service,agent_service=agent)) as client:
        state=create(client)
        state=post(client,f"{BASE}/{state['id']}/recompute",{'expected_revision':state['revision'],'include_recovery':True})
        option=state['computed_plan']['recovery']['options'][0]
        authored='Here is a tested comparison for review.'
        agent,_=agent_with([{'name':'respond_to_user','arguments':{'message':authored,
            'presentation':{'kind':'calculation','option_ids':[option['id']],'show_schedule':False}}}])
        client.app.state.agent=agent;count=len(weather)
        reply=ask(client,state,'Show this relevant option.')
        assert reply['message']==authored and reply['state']==state and len(weather)==count
        assert reply['presentation']['option_ids']==[option['id']]
        assert reply['presentation']['input_revision']==state['input_revision']
        assert reply['presentation']['generation']==state['computed_plan']['generation']
        assert not reply['presentation']['show_schedule']


def test_fake_option_presentation_cannot_create_a_card_or_trigger_an_implicit_calculation():
    agent,_=agent_with([{'name':'respond_to_user','arguments':{'message':'Here is an idea to discuss.',
        'presentation':{'kind':'conversation','option_ids':['made-up'],'show_schedule':False}}},
        {'content':'This is only an unevaluated idea.'}])
    service,weather=service_for()
    with TestClient(create_app(forecast_service=service,agent_service=agent)) as client:
        state=create(client);reply=ask(client,state,'Could we explore alternatives?')
        assert reply['message']=='This is only an unevaluated idea.'
        assert reply['presentation']['option_ids']==[] and not weather and reply['state']==state


def test_exact_selected_explanation_is_read_only_but_the_model_receives_all_valid_tools():
    service,weather=service_for();agent,calls=agent_with([{'name':'explain_current_plan','arguments':{}}])
    with TestClient(create_app(forecast_service=service,agent_service=agent)) as client:
        state=create(client);state=post(client,f"{BASE}/{state['id']}/recompute",{'expected_revision':state['revision'],'include_recovery':True})
        option=[item for item in state['computed_plan']['recovery']['options'] if item['kind']=='output'][-1]
        state=post(client,f"{BASE}/{state['id']}/recovery-selection",{'expected_revision':state['revision'],
            'input_revision':state['input_revision'],'generation':state['computed_plan']['generation'],'option_id':option['id']})
        count=len(weather);reply=ask(client,state,'Explain the exact selected plan without recalculating.')
        assert reply['mode']=='local_tool_agent',reply['message']
        assert reply['state']==state and len(weather)==count and reply['tool_calls']==['explain_current_plan']
        assert reply['presentation']['option_ids']==[option['id']]
        wire=json.loads(next(call.content for call in calls if call.method=='POST'))
        assert 'recompute_clinic_plan' in {tool['function']['name'] for tool in wire['tools']}


def test_one_grounded_option_is_valid_without_mandatory_three_option_prose():
    facts={'option_output':'The tested output option leaves 0.123 kWh unserved.'}
    message='The modeled output option leaves 0.123 kWh unserved.'
    assert render_grounded_reply({'message':message,'fact_references':['option_output']},facts,set(),{'option_output','option_battery','option_solar'})==message


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
        assert d['state']==s and not d['state']['proposals']


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


def test_natural_clarification_does_not_need_a_technical_draft_or_model_preface():
    message='What time does the campaign start?'
    assert render_grounded_reply({'message':message,'fact_references':['missing_detail']},
        {'missing_detail':'Please provide the local start time.'},{'missing_detail'},set())==message




def test_energy_settings_are_staged_then_followed_up_in_same_draft_without_confirmation():
    agent,_=agent_with([{'name':'propose_energy_settings','arguments':{'battery_capacity_kwh':8.}},
        {'name':'update_energy_settings_draft','arguments':{'initial_battery_pct':50.}}])
    service,weather=service_for()
    with TestClient(create_app(forecast_service=service,agent_service=agent)) as client:
        state=create(client)
        reply=ask(client,state,'Set the battery capacity to 8 kWh for review.');state=reply['state']
        draft=state['active_energy_proposal_id']
        assert state['energy_settings']['battery_capacity_kwh']==4.
        assert reply['presentation']['kind']=='energy_review'
        reply=ask(client,state,'Use a starting battery charge of 50% in that draft.');state=reply['state']
        assert state['active_energy_proposal_id']==draft and len(state['energy_proposals'])==1
        assert state['energy_proposals'][0]['proposed_energy_settings']['initial_battery_kwh']==4.
        assert state['energy_settings']['initial_battery_kwh']==2. and not weather


def test_existing_device_runtime_constraint_needs_physical_reference_and_device_runtime():
    from app.planning_agent import DraftTool,validate_grounding
    from app.planning_models import ActivityDraft
    service,_=service_for()
    with TestClient(create_app(forecast_service=service)) as client:
        state=state_model(create(client))
    for text in ('The campaign lasts 3 hours.','The vaccine campaign lasts 3 hours.'):
        tool=DraftTool(details=ActivityDraft(equipment_constraints=[{'equipment_id':'pump','required_duration_hours':3}]),evidence={'equipment_constraints':text})
        with pytest.raises(PlanningError):validate_grounding(tool,text,state)
    text='The Water pump must operate for 3 hours.'
    tool=DraftTool(details=ActivityDraft(equipment_constraints=[{'equipment_id':'pump','required_duration_hours':3}]),evidence={'equipment_constraints':text})
    validate_grounding(tool,text,state)


@pytest.mark.parametrize('bad',[
    'The clinic is safe tomorrow.', 'The battery will last through the night.',
    'We have sufficient electricity.', 'The power settings are now active.',
    'The activity has been confirmed.', 'Confirmed!',
])
def test_direct_prose_cannot_assert_availability_or_adopt_pending_changes(bad):
    service,weather=service_for()
    agent,_=agent_with([{'content':bad},{'content':'These changes are still pending operator review.'}])
    with TestClient(create_app(forecast_service=service,agent_service=agent)) as client:
        state=propose(client,create(client))
        state=post(client,f"{BASE}/{state['id']}/energy-proposals",{'expected_revision':state['revision'],'settings':{'battery_capacity_kwh':8.}})
        reply=ask(client,state,'Can we talk about those drafts?')
        assert reply['message']=='These changes are still pending operator review.'
        assert reply['state']==state and not weather and not reply['state']['confirmed_activities']


@pytest.mark.parametrize('message',[
    'I cannot determine whether the clinic is safe tomorrow.',
    'I cannot determine whether we have sufficient electricity without checking the plan.',
    'A larger battery might help if storage is limiting; that idea has not been evaluated.',
])
def test_uncertain_and_hypothetical_prose_is_not_an_affirmative_assurance(message):
    service,weather=service_for();agent,_=agent_with([{'content':message}])
    with TestClient(create_app(forecast_service=service,agent_service=agent)) as client:
        state=create(client);reply=ask(client,state,'What do you think, without calculating yet?')
        assert reply['message']==message and reply['state']==state and not weather


def test_existing_confirmed_activity_can_be_discussed_while_a_different_draft_is_pending():
    from test_planning_state import confirm
    service,_=service_for()
    with TestClient(create_app(forecast_service=service)) as client:
        state=confirm(client,propose(client,create(client),name='Morning vaccination campaign'))
        state=propose(client,state,name='New afternoon campaign')
        message='The earlier Morning vaccination campaign has been confirmed. The new afternoon draft remains unconfirmed.'
        agent,_=agent_with([{'content':message}]);client.app.state.agent=agent
        reply=ask(client,state,'Which activity is already confirmed?')
        assert reply['message']==message and reply['state']==state


def test_effective_confirmed_runtime_replaces_baseline_in_read_only_fact_context():
    from test_planning_state import confirm
    from app.planning_conversation import collect_reply_facts
    service,weather=service_for()
    with TestClient(create_app(forecast_service=service)) as client:
        state=create(client)
        state=propose(client,state,start_hour=9,end_hour=15,equipment_ids=['pump'],
            equipment_constraints=[{'equipment_id':'pump','required_duration_hours':3}])
        state=confirm(client,state)
        # Storage intentionally retains the baseline physical inventory separately.
        assert next(item for item in state['equipment_inventory'] if item['id']=='pump')['required_energy_kwh']==1.
        facts=collect_reply_facts(state_model(state))
        assert 'Water pump' in facts['equipment_inventory'] and '1.5 kWh' in facts['equipment_inventory']
        assert '3 hours' in facts['equipment_inventory']
        message='The confirmed Water pump requirement is 3 hours of daily operation, corresponding to 1.5 kWh in this model.'
        agent,calls=agent_with([{'content':message}]);client.app.state.agent=agent
        count=len(weather);reply=ask(client,state,'How long must the pump run now?')
        assert reply['mode']=='local_tool_agent' and reply['message']==message
        assert reply['state']==state and len(weather)==count
        wire=json.loads(next(call.content for call in calls if call.method=='POST'))
        assert 'explicit confirmed minimum total daily device runtime 3 hours' in wire['messages'][1]['content']


def test_truthful_pending_settings_update_is_not_mistaken_for_adoption():
    service,weather=service_for()
    authored='The proposed energy settings have been updated to reflect a 40% starting battery charge. The proposed day-start stored energy is now 4.8 kWh. The current stored-energy reading remains unchanged at 2.4 kWh.'
    agent,_=agent_with([{'name':'update_energy_settings_draft','arguments':{'initial_battery_pct':40.}}],syntheses=[{'content':authored}])
    with TestClient(create_app(forecast_service=service,agent_service=agent)) as client:
        state=create(client)
        state=post(client,f"{BASE}/{state['id']}/energy-proposals",{'expected_revision':state['revision'],
            'settings':{'battery_capacity_kwh':12.},'current_battery_reading':{'energy_kwh':2.4,'measured_at':'2026-11-13T22:00:00Z'}})
        active=state['active_energy_proposal_id'];reading=state['energy_proposals'][0]['current_battery_reading']
        reply=ask(client,state,'Use a 40% starting battery charge in the same draft; leave the reading alone.')
        assert reply['mode']=='local_tool_agent' and reply['message']==authored
        assert reply['state']['active_energy_proposal_id']==active
        assert reply['state']['energy_settings']==state['energy_settings']
        assert reply['state']['current_battery_reading'] is None
        assert reply['state']['energy_proposals'][0]['current_battery_reading']==reading and not weather


@pytest.mark.parametrize('message',[
    'The proposed energy settings are now active.',
    'The pending energy settings have been applied.',
    'The draft settings have been updated and are now confirmed.',
])
def test_actual_draft_update_still_cannot_be_described_as_adopted(message):
    service,weather=service_for()
    agent,_=agent_with([{'name':'update_energy_settings_draft','arguments':{'initial_battery_pct':40.}}],
        syntheses=[{'content':message},{'content':'The settings draft remains unconfirmed and available for review.'}])
    with TestClient(create_app(forecast_service=service,agent_service=agent)) as client:
        state=create(client)
        state=post(client,f"{BASE}/{state['id']}/energy-proposals",{'expected_revision':state['revision'],'settings':{'battery_capacity_kwh':12.}})
        reply=ask(client,state,'Use a 40% starting battery charge in that draft.')
        assert reply['message']=='The settings draft remains unconfirmed and available for review.'
        assert reply['state']['energy_settings']==state['energy_settings'] and not weather
