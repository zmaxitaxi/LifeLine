"""Browser-test bridge: injected weather, actual API/model. Never imported by app."""
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient
from app.main import create_app
from test_weather_forecast import service_for

if __name__=='__main__':
    value=json.loads(sys.stdin.read())
    service,_=service_for()
    with TestClient(create_app(forecast_service=service)) as client:
        response=client.request(value.get('method','POST'),value['path'],json=value.get('body'))
    print(json.dumps({'status':response.status_code,'body':response.json()},allow_nan=False))
