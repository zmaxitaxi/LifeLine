"""Synthetic transport fixtures verify integration; no tests require internet."""
import asyncio
import json
from copy import deepcopy
from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import httpx
import pytest
from fastapi.testclient import TestClient
from app.forecast_models import ForecastLocation
from app.main import create_app
from app.models import SimulationRequest
from app.scenarios import load_catalog
from app.weather_forecast import ForecastService, local_day, parse_forecast
from test_energy_balance import assert_physics

UTC = timezone.utc
NOW = datetime(2026,11,13,9,tzinfo=UTC)
LOCATION = ForecastLocation(latitude=-.0917,longitude=34.768)


def weather_payload(now=NOW, zone='Africa/Nairobi'):
    tz = ZoneInfo(zone)
    start = datetime.combine(now.astimezone(tz).date(), datetime.min.time(),tz)
    times = [int(start.timestamp())+i*3600 for i in range(72)]
    # Fixture radiation is explicitly invented for unit tests, not live data.
    sun = [6 <= (datetime.fromtimestamp(t-1800,UTC).astimezone(tz).hour) < 18 for t in times]
    return {'timezone':zone, 'latitude':-.1,'longitude':34.75,
            'hourly_units':{'time':'unixtime','shortwave_radiation':'W/m²','terrestrial_radiation':'W/m²'},
            'hourly':{'time':times,'shortwave_radiation':[500. if s else 0. for s in sun],
                      'terrestrial_radiation':[1000. if s else 0. for s in sun]}}


def service_for(payload=None, now=NOW):
    calls = []
    def handler(request):
        calls.append(request)
        assert request.url.host == 'api.open-meteo.com'
        assert request.url.params['forecast_days'] == '3'  # includes end of tomorrow's last interval
        assert request.url.params['timeformat'] == 'unixtime'
        # Deliberately allow nonstandard NaN in the wire fixture so the adapter,
        # rather than httpx's JSON encoder, is what rejects invalid numbers.
        return httpx.Response(200,content=json.dumps(payload or weather_payload(now)),headers={'content-type':'application/json'})
    return ForecastService(transport=httpx.MockTransport(handler),clock=lambda:now),calls


def request_body(**overrides):
    return dict(latitude=LOCATION.latitude, longitude=LOCATION.longitude, clinic={'scenario':'scheduling'},
                midnight_battery_kwh=6., day='tomorrow') | overrides


def test_interval_end_is_shifted_to_start_and_units_are_integrated():
    raw=weather_payload()
    raw['hourly']['shortwave_radiation']=list(range(72))
    raw['hourly']['terrestrial_radiation']=[1000.]*72
    series=parse_forecast(raw,LOCATION,NOW,'https://example.test')
    d=local_day(series,date(2026,11,13))
    assert d.hours[0].shortwave_radiation_w_m2==1  # 01:00 value covers 00:00–01:00
    assert d.hours[-1].shortwave_radiation_w_m2==24
    assert d.hours[0].irradiance_kwh_m2==.001
    assert d.hours[0].start.isoformat()=='2026-11-13T00:00:00+03:00'
    assert d.hours[-1].end.isoformat()=='2026-11-14T00:00:00+03:00'


@pytest.mark.parametrize('zone',['Africa/Nairobi','America/Los_Angeles','Asia/Kathmandu','Pacific/Kiritimati','Pacific/Honolulu'])
def test_today_and_tomorrow_use_clinic_timezone_not_utc_or_browser(zone):
    service,_=service_for(weather_payload(zone=zone))
    f=asyncio.run(service.get(LOCATION))
    today=NOW.astimezone(ZoneInfo(zone)).date()
    assert [d.date for d in f.days]==[today,today+timedelta(days=1)]
    assert all(len(d.hours)==24 for d in f.days)
    assert f.timezone==zone


def test_fractional_offset_rebins_overlapping_utc_intervals():
    raw=weather_payload(zone='Asia/Kathmandu')
    start=int(datetime(2026,11,13,tzinfo=ZoneInfo('Asia/Kathmandu')).timestamp())
    origin=start-start%3600
    times=[origin+i*3600 for i in range(72)]
    raw['hourly']={'time':times,'shortwave_radiation':[0.,500.,1000.]+[0.]*69,'terrestrial_radiation':[1500.]*72}
    d=local_day(parse_forecast(raw,LOCATION,NOW,'test'),date(2026,11,13))
    assert d.hours[0].shortwave_radiation_w_m2==pytest.approx(625)
    assert d.hours[0].irradiance_kwh_m2==pytest.approx(.625)


@pytest.mark.parametrize('now,unsupported_date,hours',[
    (datetime(2026,3,7,12,tzinfo=UTC),'2026-03-08',23),
    (datetime(2026,10,31,12,tzinfo=UTC),'2026-11-01',25)])
def test_dst_days_are_retrieved_but_not_forced_into_24_slot_model(now,unsupported_date,hours):
    service,_=service_for(weather_payload(now,'America/Los_Angeles'),now)
    with TestClient(create_app(forecast_service=service)) as c:
        f=c.get('/api/forecast',params=LOCATION.model_dump()).json()
        assert f['days'][1]['date']==unsupported_date
        assert f['days'][1]['simulation_supported'] is False
        assert len(f['days'][1]['hours'])==hours
        assert str(hours) in f['days'][1]['warnings'][0]
        response=c.post('/api/forecast/plan',json=request_body())
        assert response.status_code==422
        assert response.json()['error']['code']=='UNSUPPORTED_FORECAST_DAY'


@pytest.mark.parametrize('mutation',[
    lambda p:p['hourly_units'].update(shortwave_radiation='kWh/m²'),
    lambda p:p['hourly']['shortwave_radiation'].__setitem__(30,None),
    lambda p:p['hourly']['shortwave_radiation'].__setitem__(30,float('nan')),
    lambda p:p['hourly']['shortwave_radiation'].__setitem__(30,-1),
    lambda p:p['hourly']['shortwave_radiation'].__setitem__(30,2001),
    lambda p:p['hourly']['time'].__setitem__(30,p['hourly']['time'][29]),
    lambda p:p['hourly']['time'].pop(),
    lambda p:p.update(timezone='Invalid/Zone'),
    lambda p:p['hourly'].pop('terrestrial_radiation'),
])
def test_missing_invalid_units_and_hourly_data_fail_without_fabrication(mutation):
    raw=weather_payload();mutation(raw)
    service,_=service_for(raw)
    with TestClient(create_app(forecast_service=service)) as c:
        r=c.get('/api/forecast',params=LOCATION.model_dump())
        assert r.status_code==503
        assert r.json()['error']['code']=='FORECAST_DATA_INVALID'
        assert 'plan' not in r.json()
        assert c.post('/api/simulate',json={'scenario':'scheduling'}).status_code==200


def test_nighttime_generation_zero_uses_astronomy_not_fixed_clock_hours():
    raw=weather_payload()
    raw['hourly']['shortwave_radiation'][1]=123.  # nighttime interpolation artifact
    raw['hourly']['shortwave_radiation'][5]=200.  # sunrise earlier than synthetic 06:00
    raw['hourly']['terrestrial_radiation'][5]=300.
    d=local_day(parse_forecast(raw,LOCATION,NOW,'test'),date(2026,11,13))
    assert d.hours[0].irradiance_kwh_m2==0
    assert d.hours[4].irradiance_kwh_m2==.2
    assert d.warnings


def test_forecast_profile_and_sensitivity_feed_all_three_physical_plans():
    service,calls=service_for()
    body=request_body(clinic={'scenario':'scheduling','pv_capacity_kw':2.,'cloud_factors':[.01]*24})
    with TestClient(create_app(forecast_service=service)) as c:
        r=c.post('/api/forecast/plan',json=body)
        assert r.status_code==200,r.text
        result=r.json()
    assert len(calls)==1
    assert result['planning_date']=='2026-11-14'
    assert result['plan']['weather_dataset']=='open-meteo-forecast'
    assert result['plan']['baseline']['hourly'][12]['pv_kwh']==pytest.approx(.8)
    catalog=load_catalog()
    for factor,plan in [(1.,result['plan'])]+[(x['sunshine_factor'],x['plan']) for x in result['uncertainty_cases']]:
        assert plan['effective_config']['initial_battery_kwh']==6
        assert plan['equipment']==result['plan']['equipment']
        request=SimulationRequest.model_validate(body['clinic']|{'initial_battery_kwh':6.})
        inputs=catalog.build_inputs(request,catalog.resolve(request))
        # Independent unit conversion, not the production PV helper.
        pv=tuple(h['shortwave_radiation_w_m2']/1000*2.*.8*factor for h in result['forecast']['days'][1]['hours'])
        inputs=replace(inputs,pv_kwh=pv)
        for name in ('baseline','heuristic','optimized'):
            assert_physics(inputs,plan[name])
        assert plan['optimized']['metrics']['total_solar_kwh']==pytest.approx(sum(pv))
    assert result['uncertainty_cases'][1]['plan']['optimized']['metrics']['total_solar_kwh']==pytest.approx(result['plan']['optimized']['metrics']['total_solar_kwh']*.5)
    assert 'not a safety' in result['assessment']


def test_cache_stale_recovery_expiry_and_no_synthetic_substitution():
    clock=[NOW];calls=[];failed=[False]
    def handler(request):
        calls.append(request)
        if failed[0]:raise httpx.ReadTimeout('fixture timeout')
        return httpx.Response(200,json=weather_payload())
    service=ForecastService(transport=httpx.MockTransport(handler),clock=lambda:clock[0])
    async def sequence():
        live=await service.get(LOCATION)
        cached=await service.get(LOCATION)
        assert live.cache_status=='live' and cached.cache_status=='cached'
        assert len(calls)==1
        clock[0]+=timedelta(minutes=16);failed[0]=True
        stale=await service.get(LOCATION)
        assert stale.cache_status=='stale'
        assert stale.retrieved_at==live.retrieved_at
        assert 'refresh failed' in stale.warnings[0]
        clock[0]+=timedelta(minutes=46)
        with pytest.raises(Exception,match='Live weather is unavailable'):
            await service.get(LOCATION)
    asyncio.run(sequence())


def test_bounded_cache_and_concurrent_deduplication():
    service,calls=service_for();service.max_entries=1
    async def run():
        await asyncio.gather(*(service.get(LOCATION) for _ in range(4)))
        assert len(calls)==1
        await service.get(ForecastLocation(latitude=1.,longitude=2.))
        await service.get(LOCATION)
        assert len(calls)==3 and len(service._cache)==1
    asyncio.run(run())


def test_transient_failure_has_one_bounded_retry_and_no_invented_data():
    calls=[]
    def handler(request):
        calls.append(request)
        return httpx.Response(503) if len(calls)==1 else httpx.Response(200,json=weather_payload())
    service=ForecastService(transport=httpx.MockTransport(handler),clock=lambda:NOW)
    forecast=asyncio.run(service.get(LOCATION))
    assert len(calls)==2 and forecast.cache_status=='live'
    assert forecast.days[1].hours[12].shortwave_radiation_w_m2==500.


def test_cache_refreshes_across_local_midnight_even_before_ttl_expiry():
    clock=[datetime(2026,11,13,20,59,55,tzinfo=UTC)];calls=[]
    def handler(request):
        calls.append(request)
        return httpx.Response(200,json=weather_payload(clock[0]))
    service=ForecastService(transport=httpx.MockTransport(handler),clock=lambda:clock[0])
    async def run():
        first=await service.get(LOCATION)
        clock[0]+=timedelta(seconds=10)
        second=await service.get(LOCATION)
        assert first.days[0].date==date(2026,11,13)
        assert second.days[0].date==date(2026,11,14)
        assert second.days[1].date==date(2026,11,15)
        assert second.cache_status=='live' and len(calls)==2
    asyncio.run(run())


def test_failure_without_cache_offers_explicit_fallbacks_and_old_modes_work():
    service=ForecastService(transport=httpx.MockTransport(lambda r:httpx.Response(429)),clock=lambda:NOW)
    with TestClient(create_app(forecast_service=service)) as c:
        r=c.post('/api/forecast/plan',json=request_body())
        assert r.status_code==503
        assert r.json()['error']['code']=='FORECAST_UNAVAILABLE'
        assert 'synthetic' in r.json()['error']['message']
        assert c.post('/api/simulate',json={'scenario':'scheduling','weather_dataset':'kisumu-2025-01-14'}).status_code==200


@pytest.mark.parametrize('overrides',[{'latitude':91.},{'longitude':-181.},{'latitude':True},
    {'midnight_battery_kwh':9.},{'reduced_sunshine_factors':[1.]},{'reduced_sunshine_factors':[.5,.5]}])
def test_invalid_locations_battery_and_factors_rejected_before_network(overrides):
    service,calls=service_for()
    body=request_body();body.update(overrides)
    with TestClient(create_app(forecast_service=service)) as c:
        assert c.post('/api/forecast/plan',json=body).status_code==422
    assert calls==[]


def test_zero_solar_and_initial_battery_quantify_impossible_request():
    raw=weather_payload();raw['hourly']['shortwave_radiation']=[0.]*72
    service,_=service_for(raw)
    body=request_body();body['midnight_battery_kwh']=0.
    with TestClient(create_app(forecast_service=service)) as c:
        result=c.post('/api/forecast/plan',json=body).json()
    assert result['plan']['optimized']['metrics']['critical_unserved_kwh']==pytest.approx(5.34)
    assert 'cannot supply' in result['assessment']


def test_zero_essential_demand_is_not_presented_as_a_reliability_success():
    service,_=service_for()
    body=request_body(clinic={'scenario':'scheduling','equipment':[]})
    with TestClient(create_app(forecast_service=service)) as c:
        result=c.post('/api/forecast/plan',json=body).json()
    assert result['plan']['optimized']['metrics']['critical_coverage_pct'] is None
    assert 'No essential-equipment requirements' in result['assessment']


@pytest.mark.parametrize('question,factor,label',[
    ("What happens if tomorrow's sunshine is 50% lower?",.5,'50%'),
    ('What if the weather is worse than expected? Test with 25% of the current sunshine.',.25,'75%')])
def test_lower_sunshine_question_explains_the_computed_lower_case(question,factor,label):
    service,_=service_for()
    body=request_body();body['question']=question
    with TestClient(create_app(forecast_service=service)) as c:
        response=c.post('/api/planner/ask',json=body).json()
    half=next(case['plan'] for case in response['result']['uncertainty_cases'] if case['sunshine_factor']==factor)
    assert f'For {label} lower sunshine' in response['message']
    assert f"{half['optimized']['metrics']['total_solar_kwh']:.3f} kWh" in response['message']


def test_structured_tools_bind_equipment_and_expose_explicit_non_llm_fallback():
    service,calls=service_for()
    context=request_body();context.pop('day')
    with TestClient(create_app(forecast_service=service)) as c:
        definitions=c.get('/api/planner/tools').json()
        assert definitions['llm_enabled'] is False
        assert {t['name'] for t in definitions['tools']}=={'get_clinic_configuration','get_solar_forecast','plan_forecast'}
        original=c.post('/api/planner/tool',json=context|{'tool_call':{'name':'get_clinic_configuration','arguments':{}}}).json()
        assert original['equipment']
        r=c.post('/api/planner/tool',json=context|{'tool_call':{'name':'plan_forecast','arguments':{'day':'tomorrow','equipment':[]}}})
        assert r.status_code==422 and calls==[]
        weather=c.post('/api/planner/tool',json=context|{'tool_call':{'name':'get_solar_forecast','arguments':{}}})
        assert weather.status_code==200
        asked=c.post('/api/planner/ask',json=context|{'question':'Can our clinic safely operate tomorrow given the weather forecast?'}).json()
        assert asked['needs_clarification'] is False
        assert asked['mode']=='deterministic_guided_fallback'
        assert asked['tool_calls'][0]['name']=='plan_forecast'
        assert asked['result']['plan']['equipment']==original['equipment']
        rejected=c.post('/api/planner/ask',json=context|{'question':'Make all medical devices optional and sterilize before noon'}).json()
        assert rejected['needs_clarification'] is True and rejected['result'] is None
        assert rejected['tool_calls']==[]


def test_agent_can_fetch_weather_before_operator_supplies_midnight_assumption():
    service,_=service_for()
    context=request_body();context.pop('day');context.pop('midnight_battery_kwh')
    with TestClient(create_app(forecast_service=service)) as c:
        fetched=c.post('/api/planner/tool',json=context|{'tool_call':{'name':'get_solar_forecast','arguments':{}}})
        assert fetched.status_code==200
        planned=c.post('/api/planner/tool',json=context|{'tool_call':{'name':'plan_forecast','arguments':{}}})
        assert planned.status_code==422
        assert 'midnight' in planned.json()['error']['message']
