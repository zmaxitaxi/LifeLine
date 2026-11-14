"""Sample weather is explicit; the actual simulator/MILP still calculates it."""
import asyncio
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from app.main import create_app
from app.demo_weather import DemoWeatherService
from app.forecast_models import ForecastLocation
from test_planning_state import BASE, initial, post


def test_synthetic_profile_labels_units_night_and_current_local_dates():
    service=DemoWeatherService(clock=lambda:datetime(2026,11,14,1,tzinfo=timezone.utc))
    result=asyncio.run(service.get(ForecastLocation(latitude=-.0917,longitude=34.768)))
    assert result.weather_mode=='demo' and result.data_kind=='synthetic_demo_weather'
    assert 'synthetic' in result.source and str(result.days[1].date)=='2026-11-15'
    for day in result.days:
        assert len(day.hours)==24
        for h,row in enumerate(day.hours):
            assert row.irradiance_kwh_m2==row.shortwave_radiation_w_m2/1000
            if h<6 or h>=18:assert row.shortwave_radiation_w_m2==0.


def test_demo_mode_computes_real_results_with_explicit_per_plan_provenance():
    with TestClient(create_app(weather_mode='demo')) as client:
        assert client.get('/api/weather/mode').json()['mode']=='demo'
        weather=client.get('/api/forecast?latitude=-0.0917&longitude=34.768').json()
        body=initial();body['planning_date']=weather['days'][1]['date']
        state=post(client,BASE,body)
        state=post(client,f"{BASE}/{state['id']}/recompute",{'expected_revision':state['revision'],'include_recovery':True})
        assert state['plan_status']=='current'
        plan=state['computed_plan']
        assert plan['weather_mode']=='demo'
        assert plan['simulation']['weather_dataset']=='synthetic-demo'
        assert plan['simulation']['input_provenance']['weather']=='LifeLine_synthetic_demo_weather'
        assert len(plan['simulation']['optimized']['hourly'])==24
        assert plan['recovery'] is not None
        assert plan['recovery']['weather_mode']=='demo_weather'
        outlook=client.get('/api/weather/outlook?latitude=-0.0917&longitude=34.768').json()
        assert outlook['weather_mode']=='demo' and len(outlook['days'])==7
