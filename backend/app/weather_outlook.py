"""Actual current and seven-day Open-Meteo weather for display, never PV input."""
import asyncio
from collections import OrderedDict
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
import httpx
from .forecast_models import ForecastLocation
from .weather_forecast import FORECAST_URL, ForecastError, _number
from .weather_outlook_models import CurrentWeather, DailyWeather, WeatherOutlook

UTC=timezone.utc
TTL=timedelta(minutes=10)
MAX_STALE=timedelta(hours=1)
PERIOD_BASIS=('Daily weather aggregates use the provider UTC offset fixed at retrieval. '
    'Their calendar labels are preserved; boundaries can differ by one hour across daylight-saving changes. '
    'They are an outlook, not seven-day clinic energy simulations.')


def condition(code):
    if code is None: return 'unavailable','Conditions unavailable'
    if code==0: return 'clear','Clear sky'
    if code==1: return 'mainly_clear','Mainly clear'
    if code==2: return 'partly_cloudy','Partly cloudy'
    if code==3: return 'overcast','Overcast'
    if code in (45,48): return 'fog','Fog'
    if code in (51,53,55): return 'drizzle','Drizzle'
    if code in (56,57): return 'freezing_drizzle','Freezing drizzle'
    if code in (61,63,65): return 'rain','Rain'
    if code in (66,67): return 'freezing_rain','Freezing rain'
    if code in (71,73,75,77): return 'snow','Snow'
    if code in (80,81,82): return 'rain_showers','Rain showers'
    if code in (85,86): return 'snow_showers','Snow showers'
    if code in (95,96,99): return 'thunderstorm','Thunderstorms'
    raise ValueError('Unsupported weather code')


def optional_number(value,low,high):
    if value is not None and not _number(value,low,high):
        raise ValueError('Unsupported weather value')
    return None if value is None else float(value)


def optional_code(value):
    if value is not None and type(value) is not int:
        raise ValueError('Unsupported weather code')
    condition(value)
    return value


def parse_outlook(payload,location,retrieved_at,source_url,ttl=TTL):
    invalid=ForecastError('FORECAST_DATA_INVALID','The current/week weather summary could not be verified. Please retry.')
    try:
        zone=ZoneInfo(payload['timezone'])
        offset=payload['utc_offset_seconds']
        if type(offset) is not int or not -43200<=offset<=50400 or offset!=int(retrieved_at.astimezone(zone).utcoffset().total_seconds()):
            raise ValueError('Unsupported timezone offset')
        current=payload['current'];cu=payload['current_units'];daily=payload['daily'];du=payload['daily_units']
        if any(cu.get(k)!=v for k,v in {'time':'unixtime','interval':'seconds','temperature_2m':'°C','weather_code':'wmo code','is_day':''}.items()):
            raise ValueError('Unsupported current units')
        if any(du.get(k)!=v for k,v in {'time':'unixtime','weather_code':'wmo code','temperature_2m_max':'°C','temperature_2m_min':'°C','precipitation_probability_max':'%'}.items()):
            raise ValueError('Unsupported daily units')
        if type(current['time']) is not int or type(current['interval']) is not int or not 0<current['interval']<=3600:
            raise ValueError('Unsupported current time')
        valid_at=datetime.fromtimestamp(current['time'],UTC)
        if not -3600 <= (retrieved_at-valid_at).total_seconds() <= 6*3600:
            raise ValueError('Outdated current sample')
        if current['is_day'] is not None and (type(current['is_day']) is not int or current['is_day'] not in (0,1)):
            raise ValueError('Unsupported day/night flag')
        code=optional_code(current['weather_code']);kind,label=condition(code)
        now=CurrentWeather(valid_at=valid_at,interval_seconds=current['interval'],
            temperature_c=optional_number(current['temperature_2m'],-100,70),weather_code=code,
            condition=kind,description=label,is_day=None if current['is_day'] is None else bool(current['is_day']))
        fields=('time','weather_code','temperature_2m_max','temperature_2m_min','precipitation_probability_max')
        if any(not isinstance(daily[k],list) or len(daily[k])!=7 for k in fields):
            raise ValueError('Seven complete date rows required')
        fixed=timezone(timedelta(seconds=offset));today=retrieved_at.astimezone(fixed).date()
        days=[]
        for index,timestamp in enumerate(daily['time']):
            if type(timestamp) is not int:
                raise ValueError('Unsupported daily time')
            boundary=datetime.fromtimestamp(timestamp,fixed)
            if boundary.hour or boundary.minute or boundary.second or boundary.microsecond or boundary.date()!=today+timedelta(days=index):
                raise ValueError('Unsupported daily boundary')
            code=optional_code(daily['weather_code'][index]);kind,label=condition(code)
            low=optional_number(daily['temperature_2m_min'][index],-100,70)
            high=optional_number(daily['temperature_2m_max'][index],-100,70)
            if low is not None and high is not None and low>high:
                raise ValueError('Invalid temperature range')
            days.append(DailyWeather(date=boundary.date(),weather_code=code,condition=kind,description=label,
                temperature_min_c=low,temperature_max_c=high,
                precipitation_probability_pct=optional_number(daily['precipitation_probability_max'][index],0,100)))
        if not _number(payload['latitude'],-90,90) or not _number(payload['longitude'],-180,180):
            raise ValueError('Invalid model grid location')
        missing=(now.temperature_c is None or now.weather_code is None or now.is_day is None or
            any(d.temperature_min_c is None or d.temperature_max_c is None or d.weather_code is None or d.precipitation_probability_pct is None for d in days))
        if now.temperature_c is None and all(d.temperature_min_c is None and d.temperature_max_c is None for d in days):
            raise ValueError('Weather is unavailable')
        return WeatherOutlook(requested_location=location,
            model_grid_location=ForecastLocation(latitude=payload['latitude'],longitude=payload['longitude']),
            timezone=payload['timezone'],provider_utc_offset_seconds=offset,retrieved_at=retrieved_at,
            expires_at=retrieved_at+ttl,cache_status='live',source_url=source_url,current=now,days=days,
            daily_period_basis=PERIOD_BASIS,warnings=([
                'Some provider fields are missing and remain unavailable; no values were filled in.'] if missing else [])+[
                'Current conditions and the weekly outlook are weather-model output, not station observations or measured clinic generation.'])
    except (KeyError,TypeError,ValueError,OverflowError,ZoneInfoNotFoundError):
        raise invalid from None


class WeatherOutlookService:
    def __init__(self,transport=None,clock=None,ttl=TTL,max_stale=MAX_STALE,max_entries=64):
        self.transport=transport;self.clock=clock or (lambda:datetime.now(UTC))
        self.ttl,self.max_stale,self.max_entries=ttl,max_stale,max_entries
        self._cache=OrderedDict();self._lock=asyncio.Lock()

    async def get(self,location):
        key=(location.latitude,location.longitude)
        async with self._lock:
            now=self.clock();cached=self._cache.get(key)
            rollover=bool(cached and now.astimezone(ZoneInfo(cached.timezone)).date()!=cached.retrieved_at.astimezone(ZoneInfo(cached.timezone)).date())
            if cached and not rollover and now-cached.retrieved_at<self.ttl:
                self._cache.move_to_end(key)
                return cached.model_copy(deep=True,update={'cache_status':'cached'})
            params=dict(latitude=location.latitude,longitude=location.longitude,timezone='auto',timeformat='unixtime',
                forecast_days=7,temperature_unit='celsius',current='temperature_2m,weather_code,is_day',
                daily='weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max')
            try:
                async with httpx.AsyncClient(transport=self.transport,timeout=httpx.Timeout(8.,connect=4.),follow_redirects=False) as client:
                    for attempt in range(2):
                        try:
                            response=await client.get(FORECAST_URL,params=params,headers={'User-Agent':'LifeLine-hackathon-prototype/1.0'})
                            response.raise_for_status();break
                        except httpx.HTTPError as exc:
                            transient=isinstance(exc,(httpx.TimeoutException,httpx.NetworkError)) or (isinstance(exc,httpx.HTTPStatusError) and exc.response.status_code>=500)
                            if attempt or not transient:raise
                            await asyncio.sleep(.2)
                    if len(response.content)>100_000:raise ValueError('Unexpected response size')
                    result=parse_outlook(response.json(),location,self.clock(),FORECAST_URL+'?'+urlencode(params),self.ttl)
                self._cache[key]=result;self._cache.move_to_end(key)
                while len(self._cache)>self.max_entries:self._cache.popitem(last=False)
                return result.model_copy(deep=True)
            except (httpx.HTTPError,ValueError,ForecastError) as exc:
                if cached and not rollover and now-cached.retrieved_at<=self.max_stale:
                    return cached.model_copy(deep=True,update={'cache_status':'stale','warnings':cached.warnings+[
                        'Weather refresh failed. This is a cached outlook up to one hour old; original retrieval time retained.']})
                if isinstance(exc,ForecastError):raise
                raise ForecastError('FORECAST_UNAVAILABLE','The current/week weather summary is unavailable. Please retry.') from None
