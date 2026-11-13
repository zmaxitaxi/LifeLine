"""Current/week display adapter tests; all upstream values are test fixtures."""
import asyncio
from copy import deepcopy
from datetime import datetime,timedelta,timezone
import json
from zoneinfo import ZoneInfo
import httpx
import pytest
from fastapi.testclient import TestClient
from app.main import create_app
from app.forecast_models import ForecastLocation
from app.weather_outlook import WeatherOutlookService,parse_outlook
from app.weather_forecast import ForecastError

UTC=timezone.utc
NOW=datetime(2026,11,13,9,tzinfo=UTC)
LOCATION=ForecastLocation(latitude=-.0917,longitude=34.768)


def payload(now=NOW,zone='Africa/Nairobi'):
    offset=int(now.astimezone(ZoneInfo(zone)).utcoffset().total_seconds())
    fixed=timezone(timedelta(seconds=offset))
    start=datetime.combine(now.astimezone(fixed).date(),datetime.min.time(),fixed)
    return {'latitude':-.1,'longitude':34.75,'timezone':zone,'utc_offset_seconds':offset,
        'current_units':{'time':'unixtime','interval':'seconds','temperature_2m':'°C','weather_code':'wmo code','is_day':''},
        'current':{'time':int(now.timestamp())//900*900,'interval':900,'temperature_2m':19.3,'weather_code':2,'is_day':0},
        'daily_units':{'time':'unixtime','weather_code':'wmo code','temperature_2m_max':'°C','temperature_2m_min':'°C','precipitation_probability_max':'%'},
        'daily':{'time':[int(start.timestamp())+86400*i for i in range(7)],'weather_code':[0,1,2,3,61,71,95],
            'temperature_2m_max':[26.]*7,'temperature_2m_min':[18.]*7,'precipitation_probability_max':[10.,20.,30.,40.,50.,60.,70.]}}


def service_for(raw=None,now=NOW):
    calls=[]
    def handle(request):
        calls.append(request)
        assert request.url.host=='api.open-meteo.com'
        assert request.url.params['forecast_days']=='7'
        assert request.url.params['current']=='temperature_2m,weather_code,is_day'
        assert 'shortwave_radiation' not in str(request.url)
        return httpx.Response(200,content=json.dumps(raw or payload(now)))
    return WeatherOutlookService(transport=httpx.MockTransport(handle),clock=lambda:now),calls


def test_real_schema_units_conditions_and_nighttime_are_preserved():
    service,calls=service_for()
    with TestClient(create_app(outlook_service=service)) as c:
        r=c.get('/api/weather/outlook',params=LOCATION.model_dump());assert r.status_code==200,r.text
        d=r.json()
    assert len(calls)==1
    assert d['data_kind']=='weather_model_current_and_daily_forecast'
    assert d['current']['temperature_c']==19.3
    assert d['current']['is_day'] is False
    assert d['current']['condition']=='partly_cloudy'
    assert len(d['days'])==7
    assert [x['condition'] for x in d['days']]==['clear','mainly_clear','partly_cloudy','overcast','rain','snow','thunderstorm']
    assert d['days'][0]['temperature_min_c']==18
    assert d['days'][-1]['precipitation_probability_pct']==70
    assert d['timezone']=='Africa/Nairobi'
    assert 'not station observations' in ' '.join(d['warnings'])


@pytest.mark.parametrize('zone',['Africa/Nairobi','America/Los_Angeles','Asia/Kathmandu','Pacific/Kiritimati','Pacific/Honolulu'])
def test_seven_calendar_labels_use_provider_timezone_offset_not_host_day(zone):
    service,_=service_for(payload(zone=zone))
    result=asyncio.run(service.get(LOCATION))
    today=NOW.astimezone(ZoneInfo(zone)).date()
    assert [d.date for d in result.days]==[today+timedelta(days=i) for i in range(7)]
    assert result.current.valid_at==NOW


@pytest.mark.parametrize('now',[
    datetime(2026,3,7,12,tzinfo=UTC),datetime(2026,10,31,12,tzinfo=UTC)])
def test_week_across_dst_preserves_fixed_offset_provider_aggregates_and_dates(now):
    raw=payload(now,'America/Los_Angeles')
    result=parse_outlook(raw,LOCATION,now,'https://example.test')
    assert len(result.days)==7
    assert len({d.date for d in result.days})==7
    assert 'daylight-saving' in result.daily_period_basis
    assert result.days[-1].date-result.days[0].date==timedelta(days=6)


@pytest.mark.parametrize('mutate',[
    lambda p:p['current_units'].update(temperature_2m='°F'),
    lambda p:p['daily_units'].update(precipitation_probability_max='fraction'),
    lambda p:p['current'].update(temperature_2m=float('nan')),
    lambda p:p['current'].update(temperature_2m=True),
    lambda p:p['current'].update(weather_code=True),
    lambda p:p['current'].update(weather_code=6),
    lambda p:p['current'].update(is_day=2),
    lambda p:p.update(timezone='Invented/Zone'),
    lambda p:p['daily']['time'].pop(),
    lambda p:p['daily']['time'].__setitem__(1,p['daily']['time'][0]),
    lambda p:p['daily']['precipitation_probability_max'].__setitem__(2,101),
    lambda p:p['daily']['temperature_2m_min'].__setitem__(2,40),
])
def test_invalid_data_never_turns_into_invented_current_or_weekly_values(mutate):
    raw=payload();mutate(raw);service,_=service_for(raw)
    with TestClient(create_app(outlook_service=service)) as c:
        r=c.get('/api/weather/outlook',params=LOCATION.model_dump())
        assert r.status_code==503,r.text
        assert r.json()['error']['code']=='FORECAST_DATA_INVALID'
        assert 'days' not in r.json()
        assert c.post('/api/simulate',json={'scenario':'scheduling'}).status_code==200


def test_missing_individual_fields_remain_null_without_zero_fills():
    raw=payload();raw['current']['temperature_2m']=None
    raw['daily']['precipitation_probability_max'][3]=None
    raw['daily']['weather_code'][4]=None
    service,_=service_for(raw)
    result=asyncio.run(service.get(LOCATION))
    assert result.current.temperature_c is None
    assert result.days[3].precipitation_probability_pct is None
    assert result.days[4].weather_code is None
    assert result.days[4].condition=='unavailable'
    assert any('missing' in text for text in result.warnings)


def test_cache_retry_stale_and_expiry_keep_original_source_time():
    clock=[NOW];failed=[False];calls=[]
    def handle(request):
        calls.append(request)
        if failed[0]:raise httpx.ReadTimeout('private network detail')
        return httpx.Response(200,json=payload(clock[0]))
    service=WeatherOutlookService(transport=httpx.MockTransport(handle),clock=lambda:clock[0])
    async def run():
        a=await service.get(LOCATION);b=await service.get(LOCATION)
        assert a.cache_status=='live' and b.cache_status=='cached' and len(calls)==1
        b.days[0].temperature_min_c=999
        assert (await service.get(LOCATION)).days[0].temperature_min_c==18
        clock[0]+=timedelta(minutes=11);failed[0]=True
        stale=await service.get(LOCATION)
        assert stale.cache_status=='stale' and stale.retrieved_at==a.retrieved_at
        clock[0]+=timedelta(minutes=51)
        with pytest.raises(ForecastError) as exc:await service.get(LOCATION)
        assert 'private' not in exc.value.message
    asyncio.run(run())


def test_day_rollover_cannot_show_yesterdays_seven_days_as_current():
    clock=[datetime(2026,11,13,20,59,tzinfo=UTC)];failed=[False]
    def handle(request):
        if failed[0]:return httpx.Response(503)
        return httpx.Response(200,json=payload(clock[0]))
    service=WeatherOutlookService(transport=httpx.MockTransport(handle),clock=lambda:clock[0])
    async def run():
        await service.get(LOCATION)
        clock[0]+=timedelta(minutes=2);failed[0]=True
        with pytest.raises(ForecastError):await service.get(LOCATION)
    asyncio.run(run())


def test_bounded_cache_and_concurrent_deduplication():
    service,calls=service_for();service.max_entries=1
    async def run():
        await asyncio.gather(*(service.get(LOCATION) for _ in range(4)))
        assert len(calls)==1
        await service.get(ForecastLocation(latitude=1.,longitude=2.))
        await service.get(LOCATION)
        assert len(calls)==3 and len(service._cache)==1
    asyncio.run(run())


def test_outlook_failure_is_independent_of_solar_forecast_and_energy_model():
    from test_weather_forecast import service_for as solar_service,request_body
    def fail(request):return httpx.Response(429,json={'reason':'private provider message'})
    service=WeatherOutlookService(transport=httpx.MockTransport(fail),clock=lambda:NOW)
    with TestClient(create_app(outlook_service=service,forecast_service=solar_service()[0])) as c:
        assert c.get('/api/weather/outlook',params=LOCATION.model_dump()).status_code==503
        r=c.post('/api/forecast/plan',json=request_body())
        assert r.status_code==200
        assert r.json()['plan']['optimized']['metrics']['total_solar_kwh']>0
