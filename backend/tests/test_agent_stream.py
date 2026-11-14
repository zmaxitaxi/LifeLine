import json
from fastapi.testclient import TestClient
from app.main import create_app
from test_local_agent import agent_with
from test_weather_forecast import service_for
from test_planning_state import create, BASE


def test_stream_exposes_only_public_progress_and_final_validated_reply():
    model,_=agent_with([{'name':'respond_to_user','arguments':{'message':'Hello! How can I help with your clinic?'}}])
    service,_=service_for()
    with TestClient(create_app(agent_service=model,forecast_service=service)) as client:
        state=create(client)
        response=client.post(f"{BASE}/{state['id']}/agent/stream",json={'expected_revision':state['revision'],'question':'Hello'})
        assert response.status_code==200
        events=[json.loads(line[6:]) for line in response.text.splitlines() if line.startswith('data: ')]
        assert events[0]['type']=='progress'
        final=events[-1]['response']
        assert events[-1]['type']=='result' and final['message']=='Hello! How can I help with your clinic?'
        assert final['state']==state and final['timings']['first_progress_seconds'] is not None
        assert all(set(e)<= {'type','stage','status','elapsed_seconds'} for e in events[:-1])
        assert final['failure'] is None


def test_stale_stream_request_fails_before_starting_or_mutating_history():
    service,_=service_for()
    with TestClient(create_app(forecast_service=service)) as client:
        state=create(client)
        response=client.post(f"{BASE}/{state['id']}/agent/stream",json={'expected_revision':99,'question':'Hello'})
        assert response.status_code==409
        assert client.get(f"{BASE}/{state['id']}/conversation").json()['messages']==[]
