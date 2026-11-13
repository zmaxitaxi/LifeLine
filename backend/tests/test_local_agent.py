"""Provider contract tests use synthetic transport; all energy runs are real."""
import asyncio
import json
from copy import deepcopy
import httpx
import pytest
from fastapi.testclient import TestClient
from app.agent_models import AgentRequest, CapacityArguments, FixedRequirementArguments
from app.agent_tools import explicit_requirement, explore_capacity
from app.local_agent import LocalAgent, normalize_model_arguments
from app.main import create_app
from test_weather_forecast import service_for, request_body
from app.scenarios import load_catalog


def agent_with(calls=None, *, failure=None, remote=False):
    requests=[]
    calls=list(calls or [])
    def handler(request):
        requests.append(request)
        if request.url.path=='/api/tags':
            return httpx.Response(200,json={'models':[{'name':'llama3.1:8b','capabilities':['tools'],**({'remote_host':'https://example.test'} if remote else {})}]})
        if failure:
            return httpx.Response(failure,json={'error':'private provider error must not be reflected'})
        body=json.loads(request.content)
        assert body['model']=='llama3.1:8b'
        assert body['stream'] is False
        assert not any(t['function']['name'] in ('send_email','run_python','update_clinic') for t in body['tools'])
        call=calls.pop(0) if calls else {'name':'clarify','arguments':{'field':'intent'}}
        return httpx.Response(200,json={'message':{'role':'assistant','content':'INVENTED ANSWER 99999 kWh — must never be displayed',
            'tool_calls':[{'function':call}]}})
    return LocalAgent(transport=httpx.MockTransport(handler)),requests


def body(question='Can our clinic safely operate tomorrow given the weather forecast?',**changes):
    return request_body()|{'question':question,'inputs_confirmed':True,'input_basis':'synthetic_example'}|changes


def test_real_tool_execution_discards_model_numerical_prose_and_protects_clinic():
    service,_=service_for()
    agent,requests=agent_with([{'name':'plan_forecast','arguments':{'day':'tomorrow','reduced_sunshine_factors':'[0.75,0.5]'}}])
    original=body()
    with TestClient(create_app(forecast_service=service,agent_service=agent)) as c:
        r=c.post('/api/agent/ask',json=original)
        assert r.status_code==200,r.text
        d=r.json()
        assert d['mode']=='local_tool_agent'
        assert d['result']['planning_date']=='2026-11-14'
        assert 'INVENTED ANSWER' not in r.text
        assert 'not a safety' in d['message']
        assert [t['name'] for t in d['tool_calls']]==['get_clinic_configuration','plan_forecast']
        assert d['result']['plan']['effective_config']['initial_battery_kwh']==6
    assert original==body()


def test_explicit_lower_sunshine_answer_matches_recomputed_case_even_if_model_misses_factor():
    service,_=service_for()
    agent,_=agent_with([{'name':'plan_forecast','arguments':{'day':'tomorrow','reduced_sunshine_factors':[]}}])
    with TestClient(create_app(forecast_service=service,agent_service=agent)) as c:
        d=c.post('/api/agent/ask',json=body('What happens if we receive 50% less sunlight?')).json()
    reduced=d['result']['uncertainty_cases'][0]
    assert reduced['sunshine_factor']==.5
    assert '50% lower' in d['message']
    assert d['selected_sunshine_factor']==.5
    assert f"{reduced['plan']['optimized']['metrics']['total_solar_kwh']:.3f}" in d['message']


def test_local_ai_can_retrieve_forecast_then_run_tool():
    service,weather_calls=service_for()
    agent,requests=agent_with([{'name':'get_solar_forecast','arguments':{}},{'name':'plan_forecast','arguments':{}}])
    with TestClient(create_app(forecast_service=service,agent_service=agent)) as c:
        d=c.post('/api/agent/ask',json=body()).json()
    assert d['result']
    assert len(weather_calls)==1
    sent=json.loads(requests[-1].content)
    assert any(m['role']=='tool' and m.get('tool_name')=='get_solar_forecast' for m in sent['messages'])


@pytest.mark.parametrize('failure',[401,429,500])
def test_provider_failures_use_explicit_computed_fallback(failure):
    service,_=service_for()
    agent,_=agent_with(failure=failure)
    with TestClient(create_app(forecast_service=service,agent_service=agent)) as c:
        d=c.post('/api/agent/ask',json=body()).json()
    assert d['mode']=='deterministic_guided_fallback'
    assert d['result']
    assert 'Guided fallback' in d['message']
    assert 'private provider' not in json.dumps(d)


def test_remote_cloud_model_is_never_accepted_as_local():
    service,_=service_for()
    agent,requests=agent_with(remote=True)
    with TestClient(create_app(forecast_service=service,agent_service=agent)) as c:
        assert c.get('/api/agent/status').json()['available'] is False
        d=c.post('/api/agent/ask',json=body()).json()
    assert d['mode']=='deterministic_guided_fallback'
    assert not any(r.url.path=='/api/chat' for r in requests)


@pytest.mark.parametrize('change',[{'inputs_confirmed':False},{'midnight_battery_kwh':None}])
def test_missing_reviewed_inputs_ask_before_forecast_or_llm(change):
    service,weather=service_for()
    agent,requests=agent_with()
    with TestClient(create_app(forecast_service=service,agent_service=agent)) as c:
        d=c.post('/api/agent/ask',json=body(**change)).json()
    assert d['needs_clarification']
    assert not requests and not weather


def test_invalid_hardware_fails_before_external_calls():
    service,weather=service_for()
    agent,requests=agent_with()
    with TestClient(create_app(forecast_service=service,agent_service=agent)) as c:
        r=c.post('/api/agent/ask',json=body(clinic={'scenario':'scheduling','battery_capacity_kwh':2.}))
    assert r.status_code==422
    assert not requests and not weather


def test_generated_equipment_or_priority_changes_cannot_reach_model():
    service,_=service_for()
    malicious={'name':'plan_forecast','arguments':{'equipment':[],'reserve_kwh':0}}
    agent,_=agent_with([malicious]*3)
    with TestClient(create_app(forecast_service=service,agent_service=agent)) as c:
        d=c.post('/api/agent/ask',json=body()).json()
    assert d['mode']=='deterministic_guided_fallback'
    assert d['result']['plan']['equipment']
    assert d['result']['plan']['effective_config']['reserve_kwh']==4.8
    assert sum(t['status']=='rejected' for t in d['tool_calls'])==3


def test_unknown_tool_cannot_send_messages_or_execute_code():
    service,_=service_for()
    agent,_=agent_with([{'name':'send_email','arguments':{}}]*3)
    with TestClient(create_app(forecast_service=service,agent_service=agent)) as c:
        d=c.post('/api/agent/ask',json=body('Contact the supplier')).json()
    assert d['needs_clarification']
    assert d['result'] is None
    assert all(t['status']=='rejected' for t in d['tool_calls'][1:])


def test_fixed_requirement_uses_user_evidence_and_never_infers_appliance_ratings():
    service,weather=service_for()
    args={'name':'Sterilizer','power_kw':1.,'duration_hours':2,'earliest_start':8,'deadline':12}
    agent,_=agent_with([{'name':'evaluate_fixed_requirement','arguments':args}])
    with TestClient(create_app(forecast_service=service,agent_service=agent)) as c:
        d=c.post('/api/agent/ask',json=body('We need to sterilize equipment before noon.')).json()
    assert d['needs_clarification']
    assert d['clarification_field']=='power'
    assert not weather


def test_fixed_consecutive_energy_check_and_all_existing_critical_hours_preserved():
    service,_=service_for()
    args={'name':'Sterilizer','power_kw':1.,'duration_hours':2,'earliest_start':8,'deadline':12}
    agent,_=agent_with([{'name':'evaluate_fixed_requirement','arguments':args}])
    with TestClient(create_app(forecast_service=service,agent_service=agent)) as c:
        d=c.post('/api/agent/ask',json=body('Run an additional 1 kW sterilizer for 2 hours from 08:00 before noon.')).json()
    assert d['mode']=='local_tool_agent'
    requirement=d['requirement']
    assert requirement['candidates_evaluated']==3
    original=requirement['original']['plan']
    proposed=requirement['proposed']['plan']
    assert proposed['equipment'][:-1]==original['equipment']
    extra=proposed['equipment'][-1]
    assert extra['required_hours']==list(range(requirement['start_hour'],requirement['end_hour']))
    assert extra['power_kw']==1
    assert extra['category']=='critical'
    assert requirement['end_hour']<=12
    assert 'not applied' in d['message']
    assert 'not medical-cycle' in d['message']
    assert proposed['optimized']['metrics']['critical_requested_kwh']==pytest.approx(original['optimized']['metrics']['critical_requested_kwh']+2)


def test_multi_turn_requirement_numbers_must_be_explicit_in_user_history():
    args=FixedRequirementArguments(name='Sterilizer',power_kw=1.,duration_hours=2,earliest_start=8,deadline=12)
    assert explicit_requirement(args,['Sterilizer before noon','It is rated 1000 watts','2 hours','from 08:00']) is None
    assert explicit_requirement(args,['Sterilizer before noon','It is rated 1000 watts','2 hours'])=='earliest_start'
    assert explicit_requirement(args,['Sterilizer before noon','It is rated 1000 watts','30 minutes','from 08:00'])=='duration'


def test_empty_extra_storage_does_not_invent_starting_energy_or_solve_storm():
    service,_=service_for()
    context=AgentRequest.model_validate(body(midnight_battery_kwh=1.))
    result=asyncio.run(explore_capacity(context,CapacityArguments(sunshine_factor=0.),load_catalog(),service,asyncio.Lock()))
    assert result.tested_capacity_kwh is None
    assert result.additional_capacity_kwh is None
    assert result.samples[-1].battery_capacity_kwh==200
    assert result.samples[-1].essential_unmet_kwh>0
    assert result.samples[0].essential_unmet_kwh==pytest.approx(result.samples[-1].essential_unmet_kwh)


def test_capacity_search_can_find_a_real_storage_constraint_with_fixed_initial_energy():
    service,_=service_for()
    context=AgentRequest.model_validate(body(clinic={'scenario':'normal','battery_capacity_kwh':2.,'reserve_kwh':0.,'initial_battery_kwh':2.,
        'equipment':[{'id':'night_load','name':'Fixed illustrative evening demand','category':'critical','power_kw':.5,'required_hours':list(range(18,24))}]},midnight_battery_kwh=2.))
    result=asyncio.run(explore_capacity(context,CapacityArguments(),load_catalog(),service,asyncio.Lock()))
    assert result.tested_capacity_kwh is not None
    assert result.tested_capacity_kwh>2
    assert result.additional_capacity_kwh==pytest.approx(result.tested_capacity_kwh-2)
    assert any(s.meets_target for s in result.samples)
    passing=min(s.battery_capacity_kwh for s in result.samples if s.meets_target)
    failing=max(s.battery_capacity_kwh for s in result.samples if not s.meets_target)
    assert passing-failing<=result.resolution_kwh+1e-6


def test_model_argument_normalization_is_narrow_not_general_coercion():
    assert normalize_model_arguments({'power_kw':'1','deadline':'12','name':'123','extra':'[]'})=={'power_kw':1,'deadline':12,'name':'123','extra':'[]'}


def test_question_day_cannot_reuse_a_different_midnight_assumption():
    service,weather=service_for();agent,requests=agent_with()
    with TestClient(create_app(forecast_service=service,agent_service=agent)) as c:
        d=c.post('/api/agent/ask',json=body('Plan today',day='tomorrow')).json()
    assert d['clarification_field']=='day'
    assert not weather and not requests


def test_infeasible_additional_fixed_load_is_not_claimed_as_a_completed_cycle():
    service,_=service_for()
    args={'name':'Additional test appliance','power_kw':20.,'duration_hours':2,'earliest_start':8,'deadline':12}
    agent,_=agent_with([{'name':'evaluate_fixed_requirement','arguments':args}])
    with TestClient(create_app(forecast_service=service,agent_service=agent)) as c:
        d=c.post('/api/agent/ask',json=body('Run an additional 20 kW test appliance for 2 hours from 08:00 before noon.')).json()
    assert not d['requirement']['essential_requirements_fully_supplied']
    assert 'Do not treat the added cycle as completed' in d['message']
    assert d['result']['plan']['optimized']['metrics']['critical_unserved_kwh']>0


@pytest.mark.parametrize('message',[None,[],"not an object"])
def test_malformed_provider_message_preserves_guided_fallback(message):
    service,_=service_for()
    def handler(request):
        if request.url.path=='/api/tags':
            return httpx.Response(200,json={'models':[{'name':'llama3.1:8b','capabilities':['tools']}]})
        return httpx.Response(200,json={'message':message})
    agent=LocalAgent(transport=httpx.MockTransport(handler))
    with TestClient(create_app(forecast_service=service,agent_service=agent)) as c:
        response=c.post('/api/agent/ask',json=body())
    assert response.status_code==200
    assert response.json()['mode']=='deterministic_guided_fallback'
    assert response.json()['result'] is not None


def test_earlier_questions_are_one_labeled_context_message_not_separate_turns():
    # Regression for docs/AGENT_EVALUATION_REVIEW.md finding 1: separate user turns
    # made the real model answer every earlier question and fail validation.
    service,_=service_for()
    agent,requests=agent_with([{'name':'plan_forecast','arguments':{'day':'tomorrow','reduced_sunshine_factors':[.5]}}])
    earlier=['We expect cloudy weather tomorrow. Will we have enough electricity?',
             'Run an additional 1 kW sterilizer for 2 hours from 08:00 before noon.']
    with TestClient(create_app(forecast_service=service,agent_service=agent)) as c:
        d=c.post('/api/agent/ask',json=body('What happens if we receive 50% less sunlight?',previous_questions=earlier)).json()
    assert d['mode']=='local_tool_agent'
    sent=json.loads(next(r for r in requests if r.url.path=='/api/chat').content)['messages']
    users=[m['content'] for m in sent if m['role']=='user']
    assert len(users)==3  # operator context, labeled history, current request
    assert users[1].startswith('Earlier operator messages') and json.loads(users[1][users[1].index('['):])==earlier
    assert users[2]=='Current request. Call exactly one tool for this request only: What happens if we receive 50% less sunlight?'
    assert not any(m['content'] in earlier for m in sent)


def test_single_turn_question_is_sent_unchanged():
    service,_=service_for()
    agent,requests=agent_with([{'name':'plan_forecast','arguments':{'day':'tomorrow'}}])
    with TestClient(create_app(forecast_service=service,agent_service=agent)) as c:
        c.post('/api/agent/ask',json=body())
    sent=json.loads(next(r for r in requests if r.url.path=='/api/chat').content)['messages']
    assert sent[-1]=={'role':'user','content':body()['question']}


@pytest.mark.parametrize('question,factor',[('What if sunshine drops by 30% tomorrow?',.7),
                                            ('What if we only get half the expected sun?',.5)])
def test_reduced_case_chosen_by_model_is_the_answer_when_wording_is_unparsed(question,factor):
    # Regression for finding 2: the message described the unreduced forecast.
    service,_=service_for()
    agent,_=agent_with([{'name':'plan_forecast','arguments':{'day':'tomorrow','reduced_sunshine_factors':[factor]}}])
    with TestClient(create_app(forecast_service=service,agent_service=agent)) as c:
        d=c.post('/api/agent/ask',json=body(question)).json()
    assert d['selected_sunshine_factor']==pytest.approx(factor)
    assert d['message'].startswith(f'With {(1-factor)*100:g}% lower forecast sunshine')
    reduced=d['result']['uncertainty_cases'][0]['plan']['optimized']['metrics']['total_solar_kwh']
    assert f'{reduced:.3f} kWh versus' in d['message']


def test_generic_question_with_default_factors_keeps_the_forecast_focus():
    service,_=service_for()
    agent,_=agent_with([{'name':'plan_forecast','arguments':{'day':'tomorrow','reduced_sunshine_factors':[.75,.5]}}])
    with TestClient(create_app(forecast_service=service,agent_service=agent)) as c:
        d=c.post('/api/agent/ask',json=body()).json()
    assert d['selected_sunshine_factor']==1
    assert not d['message'].startswith('With ')


def test_unrequested_reduced_factor_does_not_replace_the_forecast_answer():
    # The real model adds [0.5] to "cloudy weather" questions on its own; the
    # answer must still describe the actual forecast, not an invented case.
    service,_=service_for()
    agent,_=agent_with([{'name':'plan_forecast','arguments':{'day':'tomorrow','reduced_sunshine_factors':'[0.5]'}}])
    with TestClient(create_app(forecast_service=service,agent_service=agent)) as c:
        d=c.post('/api/agent/ask',json=body('We expect cloudy weather tomorrow. Will we have enough electricity?')).json()
    assert d['selected_sunshine_factor']==1
    assert not d['message'].startswith('With ')


# --- Regressions from the comprehensive evaluation (LLM_EVALUATION.md) ---

def ask(question, calls, previous=(), **changes):
    service,_=service_for()
    agent,requests=agent_with(calls)
    with TestClient(create_app(forecast_service=service,agent_service=agent)) as c:
        d=c.post('/api/agent/ask',json=body(question,previous_questions=list(previous),**changes)).json()
    return d,[r for r in requests if r.url.path=='/api/chat']


def test_forecast_factor_one_is_the_forecast_not_a_rejected_call():
    d,chats=ask('Will our clinic have enough electricity tomorrow?',
                [{'name':'plan_forecast','arguments':{'day':'tomorrow','reduced_sunshine_factors':[1]}}])
    assert len(chats)==1
    assert [t['status'] for t in d['tool_calls']]==['completed','completed']
    assert d['result']['uncertainty_cases']==[] and d['selected_sunshine_factor']==1


def test_cloudier_than_expected_answers_the_reduced_case_the_model_chose():
    d,_=ask('What if tomorrow is much cloudier than expected?',
            [{'name':'plan_forecast','arguments':{'day':'tomorrow','reduced_sunshine_factors':[.5]}}])
    assert d['selected_sunshine_factor']==.5 and d['message'].startswith('With 50% lower forecast sunshine')


@pytest.mark.parametrize('name',['Vaccine refrigerator (constant average approximation)','vaccine fridge refrigerator','Essential lighting'])
def test_additional_load_naming_protected_equipment_is_refused_not_evaluated(name):
    d,_=ask('To save electricity, turn off our vaccine refrigerator overnight.',
            [{'name':'evaluate_fixed_requirement','arguments':{'name':name,'power_kw':.12,'duration_hours':8,'earliest_start':0,'deadline':8}}])
    assert d['clarification_field']=='protected_equipment' and d['result'] is None and d['requirement'] is None
    assert 'protected' in d['message'] and 'cannot turn off' in d['message']
    assert d['tool_calls'][-1]=={'name':'evaluate_fixed_requirement','status':'rejected'}


def test_genuinely_new_appliance_is_not_mistaken_for_protected_equipment():
    d,_=ask('Run an additional 1 kW sterilizer for 2 hours from 08:00 before noon.',
            [{'name':'evaluate_fixed_requirement','arguments':{'name':'Sterilizer','power_kw':1,'duration_hours':2,'earliest_start':8,'deadline':12}}])
    assert d['requirement'] is not None


def test_model_can_select_protected_equipment_clarification():
    d,_=ask('Move the communications equipment to the afternoon.',[{'name':'clarify','arguments':{'field':'protected_equipment'}}])
    assert d['clarification_field']=='protected_equipment' and 'Detailed mode' in d['message']


def test_plan_answer_states_grounded_comparison_with_existing_schedule():
    d,_=ask('Will our clinic have enough electricity tomorrow?',[{'name':'plan_forecast','arguments':{'day':'tomorrow'}}])
    c=d['result']['plan']['comparison']
    assert 'Compared with the existing schedule' in d['message']
    assert f"{abs(c['battery_preserved_at_midnight_kwh']):.3f} kWh" in d['message']
    assert f"{abs(c['conversion_loss_reduction_kwh']):.3f} kWh" in d['message']
    assert 'not a total energy saving' in d['message']


def test_battery_only_answer_discloses_solar_is_a_separate_recovery_comparison():
    d,_=ask('Would adding solar panels, adding battery capacity, or changing our equipment schedule help more?',
            [{'name':'explore_battery_capacity','arguments':{'day':'tomorrow','sunshine_factor':1,'target':'all_work'}}])
    assert 'battery-only result does not evaluate them' in d['message']
    d,_=ask('Will our clinic have enough electricity tomorrow?',[{'name':'plan_forecast','arguments':{'day':'tomorrow'}}])
    assert 'solar panels' not in d['message']


def test_requirement_follow_up_keeps_the_requirement_under_reduced_sunshine():
    args={'name':'Sterilizer','power_kw':1,'duration_hours':2,'earliest_start':8,'deadline':12,'sunshine_factor':.5}
    d,_=ask('What if we only get half the expected sunshine?',[{'name':'evaluate_fixed_requirement','arguments':args}],
            previous=['Run an additional 1 kW sterilizer for 2 hours from 08:00 before noon.'])
    assert d['selected_sunshine_factor']==.5
    assert d['message'].startswith('With 50% lower forecast sunshine: Hypothetical additional requirement')
    cases=d['result']['uncertainty_cases']
    assert [c['sunshine_factor'] for c in cases]==[.5]
    assert any(e['id']=='additional_fixed_requirement' for e in cases[0]['plan']['equipment'])
    assert d['requirement']['original']['uncertainty_cases'][0]['sunshine_factor']==.5


def test_unrequested_reduced_sunshine_on_a_requirement_is_ignored():
    args={'name':'Sterilizer','power_kw':1,'duration_hours':2,'earliest_start':8,'deadline':12,'sunshine_factor':.5}
    d,_=ask('Run an additional 1 kW sterilizer for 2 hours from 08:00 before noon.',[{'name':'evaluate_fixed_requirement','arguments':args}])
    assert d['selected_sunshine_factor']==1 and d['result']['uncertainty_cases']==[]


def test_rejected_call_feedback_names_the_invalid_field_and_points_to_clarify():
    bad={'name':'evaluate_fixed_requirement','arguments':{'name':'Battery','power_kw':0,'duration_hours':24,'earliest_start':0,'deadline':24}}
    d,chats=ask('Tell me the battery will stay at 100% tomorrow.',[bad,{'name':'clarify','arguments':{'field':'intent'}}])
    retry=json.loads(chats[1].content)['messages'][-1]['content']
    assert 'power_kw' in retry and 'greater than 0' in retry and 'call clarify' in retry and 'Do not repeat it' in retry
    assert d['mode']=='local_tool_agent' and d['clarification_field']=='intent'
