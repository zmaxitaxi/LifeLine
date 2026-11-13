"""Synthetic model/weather transport, real API, simulator and optimizer."""
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient
from app.main import create_app
from test_local_agent import agent_with
from test_weather_forecast import service_for
from app.weather_forecast import ForecastError

if __name__=='__main__':
    value=json.loads(sys.stdin.read())
    name=value.get('tool','plan_forecast')
    arguments=value.get('arguments',{'day':'tomorrow'})
    agent,_=agent_with([{'name':name,'arguments':arguments}],failure=value.get('failure'))
    class UnavailableWeather:
        async def get(self, location):
            raise ForecastError('FORECAST_UNAVAILABLE','Synthetic browser-test network failure')
    service=UnavailableWeather() if value.get('weather_failure') else service_for()[0]
    with TestClient(create_app(forecast_service=service,agent_service=agent)) as client:
        response=client.post('/api/agent/stream' if value.get('stream') else '/api/agent/ask',json=value['body'])
    print(json.dumps({'status':response.status_code,'body':response.text if value.get('stream') else response.json()},allow_nan=False))
