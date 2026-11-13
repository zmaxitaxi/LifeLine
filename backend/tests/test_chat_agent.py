"""Chat clarification, genuine execution updates, and numerical grounding."""
import asyncio
from copy import deepcopy
import json
import pytest
from fastapi.testclient import TestClient
from app.agent_models import AgentRequest
from app.local_agent import ask_agent
from app.main import create_app
from app.scenarios import load_catalog
from app.weather_forecast import ForecastError
from test_local_agent import agent_with, body
from test_weather_forecast import service_for


def streamed(client, value):
    response=client.post('/api/agent/stream',json=value)
    assert response.status_code==200,response.text
    assert response.headers['content-type'].startswith('text/event-stream')
    return [json.loads(line[6:]) for line in response.text.splitlines() if line.startswith('data: ')]


def test_current_battery_is_a_readable_percentage_not_an_implicit_starting_charge():
    service,weather=service_for()
    agent,model_calls=agent_with()
    with TestClient(create_app(forecast_service=service,agent_service=agent)) as client:
        missing=client.post('/api/agent/ask',json=body(midnight_battery_kwh=None)).json()
        assert missing['clarification_field']=='current_battery'
        assert 'percentage' in missing['message'] and 'right now' in missing['message']
        current=client.post('/api/agent/ask',json=body(midnight_battery_kwh=None,current_battery_pct=60.)).json()
        assert current['clarification_field']=='starting_battery'
        assert current['suggested_starting_battery_pct']==60
        assert 'not a prediction' in current['message']
        assert current['result'] is None
        unconfirmed=client.post('/api/agent/ask',json=body(midnight_battery_kwh=None,starting_battery_pct=45.)).json()
        assert unconfirmed['needs_clarification'] and unconfirmed['result'] is None
    assert not model_calls and not weather


def test_confirmed_percentage_is_converted_by_backend_independently_of_current_reading():
    service,_=service_for()
    agent,model_calls=agent_with([{'name':'plan_forecast','arguments':{}}])
    request=body(midnight_battery_kwh=None,current_battery_pct=90.,starting_battery_pct=40.,starting_charge_confirmed=True)
    original=deepcopy(request)
    with TestClient(create_app(forecast_service=service,agent_service=agent)) as client:
        result=client.post('/api/agent/ask',json=request).json()
    assert request==original
    assert result['mode']=='local_tool_agent'
    assert result['result']['midnight_battery_kwh']==pytest.approx(3.2)  # 40% of 8 kWh
    for name in ('baseline','heuristic','optimized'):
        assert result['result']['plan'][name]['hourly'][0]['soc_start_kwh']==pytest.approx(3.2)
    sent=json.loads(model_calls[-1].content)
    assert '"initial_battery_kwh": 3.2' in sent['messages'][1]['content']
    assert 'INVENTED ANSWER' not in json.dumps(result)


def test_capacity_change_does_not_validate_an_unused_legacy_starting_energy():
    service,_=service_for()
    agent,_=agent_with([{'name':'plan_forecast','arguments':{}}])
    request=body(midnight_battery_kwh=None,starting_battery_pct=50.,starting_charge_confirmed=True,
                 clinic={'scenario':'scheduling','battery_capacity_kwh':4.,'reserve_kwh':1.})
    with TestClient(create_app(forecast_service=service,agent_service=agent)) as client:
        response=client.post('/api/agent/ask',json=request)
    assert response.status_code==200,response.text
    assert response.json()['result']['midnight_battery_kwh']==2


@pytest.mark.parametrize('value',[-1,101,True,'60'])
def test_invalid_current_percentages_are_rejected(value):
    service,_=service_for()
    agent,calls=agent_with()
    with TestClient(create_app(forecast_service=service,agent_service=agent)) as client:
        response=client.post('/api/agent/ask',json=body(current_battery_pct=value))
    assert response.status_code==422
    assert not calls


def test_conflicting_starting_energy_and_percentage_ask_for_correction():
    service,_=service_for()
    agent,calls=agent_with()
    with TestClient(create_app(forecast_service=service,agent_service=agent)) as client:
        response=client.post('/api/agent/ask',json=body(midnight_battery_kwh=6.,starting_battery_pct=50.,starting_charge_confirmed=True))
    assert response.status_code==422
    assert 'different assumptions' in response.json()['error']['message']
    assert not calls


def test_stream_contains_real_tool_stages_and_only_verified_numerical_answer():
    service,_=service_for()
    agent,_=agent_with([{'name':'get_solar_forecast','arguments':{}},{'name':'plan_forecast','arguments':{}}])
    with TestClient(create_app(forecast_service=service,agent_service=agent)) as client:
        events=streamed(client,body())
    assert events[-1]['type']=='answer'
    assert 'INVENTED ANSWER' not in json.dumps(events)
    activities=[e for e in events if e['type']=='activity']
    assert any(e['id']=='model-0' and e['status']=='running' for e in activities)
    assert any(e['id']=='forecast' and e['status']=='completed' for e in activities)
    assert any(e['id']=='simulation' and e['status']=='completed' for e in activities)
    assert [e['elapsed_ms'] for e in activities]==sorted(e['elapsed_ms'] for e in activities)
    answer=events[-1]['response']
    assert answer['mode']=='local_tool_agent'
    assert any(t['name']=='plan_forecast' and t['status']=='completed' for t in answer['tool_calls'])
    plan=answer['result']['plan']
    for name in ('baseline','optimized'):
        for hour in plan[name]['hourly']:
            expected=hour['soc_start_kwh']+hour['charge_input_kwh']*plan['effective_config']['charge_efficiency']-hour['discharge_output_kwh']/plan['effective_config']['discharge_efficiency']
            assert hour['soc_end_kwh']==pytest.approx(expected,abs=1e-6)
        assert plan[name]['hourly'][-1]['soc_end_kwh']==pytest.approx(plan[name]['metrics']['final_soc_kwh'])


def test_activity_is_emitted_while_local_model_is_still_running():
    async def scenario():
        entered=asyncio.Event()
        release=asyncio.Event()
        updates=[]
        class WaitingAgent:
            model='llama3.1:8b'
            async def status(self): return {'available':True}
            async def decide(self,messages):
                entered.set()
                await release.wait()
                return {'name':'plan_forecast','arguments':{}}
        async def progress(event): updates.append(event)
        service,_=service_for()
        task=asyncio.create_task(ask_agent(AgentRequest.model_validate(body()),load_catalog(),service,asyncio.Lock(),WaitingAgent(),progress=progress))
        await asyncio.wait_for(entered.wait(),timeout=2)
        assert not task.done()
        assert any(e['id']=='model-0' and e['status']=='running' for e in updates)
        assert not any(e['id']=='simulation' for e in updates)
        release.set()
        answer=await task
        assert answer.result is not None
    asyncio.run(scenario())


def test_followup_questions_use_user_provided_ratings_and_protect_existing_critical_hours():
    service,weather=service_for()
    args={'name':'Sterilizer','power_kw':1.,'duration_hours':2,'earliest_start':8,'deadline':12}
    agent,_=agent_with([{'name':'clarify','arguments':{'field':'power'}},{'name':'evaluate_fixed_requirement','arguments':args}])
    with TestClient(create_app(forecast_service=service,agent_service=agent)) as client:
        first=client.post('/api/agent/ask',json=body('We need to sterilize equipment before noon.')).json()
        assert first['clarification_field']=='power'
        assert 'label' in first['message'] and not weather
        response=client.post('/api/agent/ask',json=body('From 08:00 before noon.',previous_questions=[
            'We need to sterilize equipment before noon.','The sterilizer label says 1 kW.','It must run for 2 hours.'])).json()
    assert response['requirement'] is not None
    before=response['requirement']['original']['plan']['equipment']
    after=response['requirement']['proposed']['plan']['equipment']
    for equipment in before:
        assert next(e for e in after if e['id']==equipment['id'])==equipment
    added=after[-1]
    assert added['category']=='critical' and added['power_kw']==1
    assert len(added['required_hours'])==2
    assert added['required_hours'][1]-added['required_hours'][0]==1


def test_deterministic_fallback_remains_explicit_and_computes_real_results():
    service,_=service_for()
    agent,_=agent_with(failure=500)
    with TestClient(create_app(forecast_service=service,agent_service=agent)) as client:
        events=streamed(client,body())
    assert any(e.get('id')=='fallback' and e['status']=='warning' for e in events)
    response=events[-1]['response']
    assert response['mode']=='deterministic_guided_fallback'
    assert response['result'] and response['fallback_reason']
    assert response['result']['plan']['optimized']['hourly'][0]['soc_start_kwh']==6


def test_weather_failure_has_no_successful_streamed_plan_or_synthetic_substitute():
    class UnavailableWeather:
        async def get(self,location): raise ForecastError('FORECAST_UNAVAILABLE','Provider failed')
    agent,_=agent_with([{'name':'plan_forecast','arguments':{}}])
    with TestClient(create_app(forecast_service=UnavailableWeather(),agent_service=agent)) as client:
        events=streamed(client,body())
    assert events[-1]['type']=='error' and events[-1]['code']=='FORECAST_UNAVAILABLE'
    assert not any(e['type']=='answer' for e in events)
    assert not any(e.get('id')=='simulation' and e['status']=='completed' for e in events)
