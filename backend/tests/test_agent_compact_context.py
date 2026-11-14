"""Native context and date regressions from measured session failures."""
import json
from datetime import datetime,timedelta
from zoneinfo import ZoneInfo
from fastapi.testclient import TestClient
from app.main import create_app
from app.planning_agent import definitions, session_context
from app.planning_models import PlanningState
from test_local_agent import agent_with
from test_planning_state import BASE,create,post,initial
from test_planning_agent import ask
from test_weather_forecast import service_for


def test_compact_context_preserves_specs_all_tools_and_does_not_duplicate_clinic():
    with TestClient(create_app()) as client:
        state=PlanningState.model_validate_json(json.dumps(create(client)))
        context=session_context(state,[],'Hello')
        assert 'clinic' not in context and 'baseline_equipment_inventory' not in context
        assert context['energy_settings']['battery_capacity_kwh']==4
        assert {e['id'] for e in context['equipment_inventory']}=={'fridge','pump'}
        names={t['name'] for t in definitions(state)}
        assert {'propose_activity','recompute_clinic_plan','inspect_planning_state','explain_current_plan','respond_to_user','propose_energy_settings'}<=names
        schema=next(t for t in definitions(state) if t['name']=='propose_activity')['parameters']
        assert schema['properties']['start_hour']['type']=='integer'
        assert len(json.dumps(context))<2200


def test_today_mismatch_returns_authored_clarification_without_mutating_or_asking_power():
    now=datetime.now(ZoneInfo('Africa/Nairobi')).date()
    message=f'You asked for today, {now.isoformat()}, but the selected planning date is tomorrow, {(now+timedelta(days=1)).isoformat()}. Please change the selected date before we stage that activity.'
    agent,calls=agent_with([{'name':'propose_activity','arguments':{'name':'vaccination clinic','start_hour':10,'equipment_constraints':None,'additional_equipment':None}}, {'content':message}])
    service,weather=service_for()
    with TestClient(create_app(agent_service=agent,forecast_service=service)) as client:
        body=initial();body['planning_date']=(now+timedelta(days=1)).isoformat();body['timezone']='Africa/Nairobi'
        state=post(client,BASE,body);reply=ask(client,state,'What if I wanted to plan a vaccination clinic today at 10 AM?')
        assert reply['message']==message and reply['state']==state and not weather
        assert reply['tool_calls']==[] and reply['failure']['code']=='DATE_MISMATCH'
        assert reply['failure']['requested_date']==now.isoformat()
        wire=json.loads(calls[-1].content)
        assert 'do not ask for equipment power' in json.dumps(wire)


def test_native_null_collections_are_omitted_before_strict_draft_validation():
    agent,_=agent_with([{'name':'propose_activity','arguments':{'name':'vaccination clinic','start_hour':10,'end_hour':None,'equipment_ids':None,'equipment_constraints':None,'additional_equipment':None}}])
    service,weather=service_for()
    with TestClient(create_app(agent_service=agent,forecast_service=service)) as client:
        state=create(client);reply=ask(client,state,'Please stage a vaccination clinic at 10 AM.')
        assert len(reply['state']['proposals'])==1 and not weather
        draft=reply['state']['proposals'][0]
        assert draft['details']['start_hour']==10 and draft['details']['equipment_ids'] is None
        assert draft['missing_fields']==['end_hour','equipment_ids']


def test_repeated_identical_recompute_in_one_turn_reuses_only_fresh_same_input():
    agent,_=agent_with([{'name':'recompute_clinic_plan','arguments':{}}],syntheses=[{'name':'recompute_clinic_plan','arguments':{}},{'content':'This modeled result is ready for review.'}])
    service,weather=service_for()
    with TestClient(create_app(agent_service=agent,forecast_service=service)) as client:
        reply=ask(client,create(client),'Calculate the electricity plan.')
        assert reply['mode']=='local_tool_agent' and len(weather)==1
        assert reply['state']['computed_plan']['generation']==1


def test_native_truncation_is_not_exposed_and_actual_provider_metrics_are_recorded():
    import asyncio,httpx,pytest
    from app.local_agent import LocalAgent,AgentUnavailable
    from app.agent_telemetry import AgentTrace,ACTIVE_TRACE
    def handler(request):
        assert json.loads(request.content)['options']['num_predict']==384
        return httpx.Response(200,json={'done_reason':'length','message':{'content':'Incomplete reply'},
            'prompt_eval_count':321,'eval_count':384,'total_duration':1200000})
    trace=AgentTrace();token=ACTIVE_TRACE.set(trace)
    try:
        with pytest.raises(AgentUnavailable,match='TRUNCATED'):
            asyncio.run(LocalAgent(transport=httpx.MockTransport(handler)).session_turn([{'role':'user','content':'Hello'}],toolset=[]))
        assert trace.model_calls==1 and trace.model_metrics[0]['eval_count']==384
        assert trace.model_metrics[0]['prompt_eval_count']==321
        assert trace.stages['model']>=0
    finally:ACTIVE_TRACE.reset(token)
