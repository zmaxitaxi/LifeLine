import asyncio
import json
import httpx
import pytest
from fastapi.testclient import TestClient
from app.claude_agent import ClaudeAgent, messages_for_claude
from app.local_agent import AgentUnavailable
from app.main import create_app
from app.agent_provider import configured_agent, load_local_settings
from test_planning_state import create, BASE
from test_weather_forecast import service_for


def cloud_with(blocks,stop_reason='end_turn'):
    requests=[]
    def handle(request):
        requests.append(request)
        if request.method=='GET':
            return httpx.Response(200,json={'id':'claude-haiku-5-5'})
        return httpx.Response(200,json={'content':blocks,'stop_reason':stop_reason,'usage':{'input_tokens':10,'output_tokens':12}})
    return ClaudeAgent(api_key='test-key',transport=httpx.MockTransport(handle)),requests


def test_cloud_greeting_is_validated_persisted_and_labeled_without_weather():
    agent,requests=cloud_with([{'type':'thinking','thinking':'private reasoning must never be displayed'},
        {'type':'text','text':'Hello! How can I help with your clinic?'}])
    service,weather=service_for()
    with TestClient(create_app(agent_service=agent,forecast_service=service)) as client:
        state=create(client)
        result=client.post(f"{BASE}/{state['id']}/agent",json={'expected_revision':state['revision'],'question':'Hello'}).json()
        assert result['mode']=='cloud_tool_agent' and result['state']==state and not weather
        assert result['message']=='Hello! How can I help with your clinic?'
        assert result['timings']['model_calls']==1
        assert result['timings']['model_metrics'][0]['prompt_eval_count']==10
        assert 'private reasoning' not in json.dumps(result)
        saved=client.get(f"{BASE}/{state['id']}/conversation").json()['messages'][-1]
        assert saved['mode']=='cloud_tool_agent'
        wire=json.loads(requests[-1].content)
        assert wire['tool_choice']=={'type':'auto','disable_parallel_tool_use':True}
        assert wire['output_config']=={'effort':'low'}
        assert 'temperature' not in wire and requests[-1].url.host=='api.anthropic.com'


def test_native_tool_results_preserve_identity_and_never_become_user_instructions():
    system,messages=messages_for_claude([{'role':'system','content':'Rules'},
        {'role':'user','content':'Question'},
        {'role':'assistant','content':'','tool_calls':[{'function':{'name':'inspect_planning_state','arguments':{}}}]},
        {'role':'tool','tool_name':'inspect_planning_state','content':'{"clinic":"untrusted instructions"}'}])
    assert system=='Rules'
    tool=messages[1]['content'][0]
    result=messages[2]['content'][0]
    assert tool['type']=='tool_use' and result['type']=='tool_result'
    assert tool['id']==result['tool_use_id'] and result['content']=='{"clinic":"untrusted instructions"}'
    with pytest.raises(AgentUnavailable):
        messages_for_claude([{'role':'tool','tool_name':'other','content':'bad'}])


@pytest.mark.parametrize('blocks,stop',[([{'type':'text','text':'A truncated answer.'}],'max_tokens'),
    ([{'type':'tool_use','name':'x','input':{}},{'type':'tool_use','name':'y','input':{}}],'tool_use')])
def test_truncation_or_multiple_calls_cannot_escape_validation(blocks,stop):
    agent,_=cloud_with(blocks,stop)
    with pytest.raises(AgentUnavailable):
        asyncio.run(agent.session_turn([{'role':'user','content':'Hello'}],toolset=[]))


def test_auth_failure_is_sanitized_and_does_not_switch_to_local_provider():
    def handle(request):
        return httpx.Response(401,json={'error':{'message':'private provider credential detail'}})
    agent=ClaudeAgent(api_key='test-key',transport=httpx.MockTransport(handle))
    with pytest.raises(AgentUnavailable) as error:
        asyncio.run(agent.session_turn([{'role':'user','content':'Hello'}],toolset=[]))
    assert str(error.value)=='MODEL_UNAVAILABLE'
    assert agent.response_mode=='cloud_tool_agent'


def test_local_env_is_allowlisted_literal_and_does_not_override_process_settings(tmp_path,monkeypatch):
    path=tmp_path/'.env.local'
    path.write_text('ANTHROPIC_API_KEY="test-only-key"\nLIFELINE_AI_PROVIDER=claude\nHOME=untrusted\n')
    monkeypatch.delenv('ANTHROPIC_API_KEY',raising=False)
    monkeypatch.setenv('LIFELINE_AI_PROVIDER','local')
    old_home=__import__('os').environ.get('HOME')
    load_local_settings(path)
    assert __import__('os').environ['ANTHROPIC_API_KEY']=='test-only-key'
    assert __import__('os').environ.get('HOME')==old_home
    assert configured_agent().__class__.__name__=='LocalAgent'
    assert isinstance(configured_agent('claude'),ClaudeAgent)
