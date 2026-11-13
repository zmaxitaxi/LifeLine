"""Open-Meteo adapter. No LLM, invented weather, or hidden synthetic fallback."""
import asyncio
from collections import OrderedDict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import math
from urllib.parse import urlencode
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
import httpx
from .forecast_models import ForecastDay, ForecastHour, ForecastLocation, SolarForecast

UTC = timezone.utc
FORECAST_URL = 'https://api.open-meteo.com/v1/forecast'
TTL = timedelta(minutes=15)
MAX_STALE = timedelta(hours=1)


class ForecastError(Exception):
    def __init__(self, code, message, status=503):
        super().__init__(message)
        self.code, self.message, self.status = code, message, status


def _number(value, low, high):
    return type(value) in (int, float) and math.isfinite(value) and low <= value <= high


@dataclass(frozen=True)
class ForecastSeries:
    location: ForecastLocation
    grid_location: ForecastLocation
    timezone: str
    retrieved_at: datetime
    # Each timestamp ENDS the preceding one-hour radiation interval.
    times: tuple[int, ...]
    radiation: tuple[float, ...]
    extraterrestrial: tuple[float, ...]
    source_url: str


def parse_forecast(payload, location, retrieved_at, source_url):
    """Reject incomplete/unphysical upstream data instead of filling gaps."""
    invalid = ForecastError('FORECAST_DATA_INVALID', 'The weather provider returned incomplete or unsupported hourly radiation data. Select a labeled historical or synthetic mode, or retry.')
    try:
        zone = payload['timezone']
        ZoneInfo(zone)
        units, hourly = payload['hourly_units'], payload['hourly']
        if units['time'] != 'unixtime' or any(units[k] != 'W/m²' for k in ('shortwave_radiation', 'terrestrial_radiation')):
            raise invalid
        times, radiation, toa = (hourly[k] for k in ('time', 'shortwave_radiation', 'terrestrial_radiation'))
        if not 48 <= len(times) <= 100 or len(radiation) != len(times) or len(toa) != len(times):
            raise invalid
        if any(type(t) is not int for t in times) or any(b-a != 3600 for a,b in zip(times,times[1:])):
            raise invalid
        if any(not _number(v, 0, 2000) for v in (*radiation, *toa)):
            raise invalid
        if not _number(payload['latitude'], -90, 90) or not _number(payload['longitude'], -180, 180):
            raise invalid
        return ForecastSeries(location, ForecastLocation(latitude=payload['latitude'], longitude=payload['longitude']), zone,
                              retrieved_at, tuple(times), tuple(radiation), tuple(toa), source_url)
    except (KeyError, TypeError, ValueError, ZoneInfoNotFoundError):
        raise invalid from None


def local_day(series, day):
    """Integrate interval overlaps, including fractional-hour time zones."""
    zone = ZoneInfo(series.timezone)
    start = datetime.combine(day, datetime.min.time(), zone)
    end = datetime.combine(day+timedelta(days=1), datetime.min.time(), zone)
    start_epoch, end_epoch = int(start.timestamp()), int(end.timestamp())
    supported = end_epoch-start_epoch == 24*3600
    warnings = [] if supported else [
        f'This local day has {(end_epoch-start_epoch)/3600:g} hours. The current simulator requires 24 hourly slots; this day cannot be simulated without changing the model.']
    hours, nighttime_adjustments = [], 0
    for a in range(start_epoch, end_epoch, 3600):
        b = min(a+3600, end_epoch)
        energy, covered = 0., 0
        adjusted = False
        for finish, ghi, toa in zip(series.times, series.radiation, series.extraterrestrial):
            overlap = max(0, min(b,finish)-max(a,finish-3600))
            if overlap:
                covered += overlap
                # TOA is the provider's astronomical preceding-hour mean. Do
                # not impose the synthetic model's 06–18 daylight window.
                if toa <= 1e-6:
                    adjusted |= ghi > 0
                    ghi = 0.
                energy += ghi*overlap/3600/1000
        if covered != b-a:
            raise ForecastError('FORECAST_DATA_INVALID', 'Forecast intervals do not fully cover the selected local day. No missing radiation values have been substituted.')
        nighttime_adjustments += adjusted
        hours.append(ForecastHour(start=datetime.fromtimestamp(a,UTC).astimezone(zone), end=datetime.fromtimestamp(b,UTC).astimezone(zone),
                                  shortwave_radiation_w_m2=energy*1000/((b-a)/3600), irradiance_kwh_m2=energy))
    if nighttime_adjustments:
        warnings.append(f'Radiation in {nighttime_adjustments} intervals was set to zero where the provider’s astronomical radiation is zero.')
    return ForecastDay(date=day, hours=hours, simulation_supported=supported, warnings=warnings)


class ForecastService:
    """Bounded process-local cache; injected transport/clock keep tests offline."""
    def __init__(self, transport=None, clock=None, ttl=TTL, max_stale=MAX_STALE, max_entries=64):
        self.transport = transport
        self.clock = clock or (lambda: datetime.now(UTC))
        self.ttl, self.max_stale, self.max_entries = ttl, max_stale, max_entries
        self._cache = OrderedDict()
        self._lock = asyncio.Lock()

    async def get(self, location):
        key = (location.latitude, location.longitude)
        async with self._lock:
            now = self.clock()
            series = self._cache.get(key)
            status, warning = 'cached', None
            rolled_day = bool(series and now.astimezone(ZoneInfo(series.timezone)).date() != series.retrieved_at.astimezone(ZoneInfo(series.timezone)).date())
            if series is None or now-series.retrieved_at >= self.ttl or rolled_day:
                params = dict(latitude=location.latitude, longitude=location.longitude,
                              hourly='shortwave_radiation,terrestrial_radiation', timezone='auto',
                              timeformat='unixtime', forecast_days=3)
                try:
                    async with httpx.AsyncClient(transport=self.transport, timeout=httpx.Timeout(8., connect=4.), follow_redirects=False) as client:
                        for attempt in range(2):
                            try:
                                response = await client.get(FORECAST_URL, params=params, headers={'User-Agent':'LifeLine-hackathon-prototype/1.0'})
                                response.raise_for_status()
                                break
                            except httpx.HTTPError as exc:
                                transient = isinstance(exc, (httpx.TimeoutException, httpx.NetworkError)) or (isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code >= 500)
                                if attempt or not transient:
                                    raise
                                await asyncio.sleep(.2)
                        if len(response.content) > 200_000:
                            raise ValueError('Unexpected forecast size')
                        received_at = self.clock()
                        candidate = parse_forecast(response.json(), location, received_at, FORECAST_URL+'?'+urlencode(params))
                        # Validate coverage before replacing a known-good cache.
                        self._bundle(candidate, received_at, 'live', None)
                    series, status = candidate, 'live'
                    self._cache[key] = series
                    self._cache.move_to_end(key)
                    while len(self._cache) > self.max_entries:
                        self._cache.popitem(last=False)
                except (httpx.HTTPError, ValueError, ForecastError) as exc:
                    if series is None or now-series.retrieved_at > self.max_stale or rolled_day:
                        if isinstance(exc, ForecastError):
                            raise exc
                        raise ForecastError('FORECAST_UNAVAILABLE', 'Live weather is unavailable. Retry, or explicitly select historical NASA data or a synthetic scenario. No fallback weather has been presented as a live forecast.') from None
                    status, warning = 'stale', 'Forecast refresh failed. Using a cached forecast less than one hour old; its original retrieval time is retained. It may no longer represent the latest forecast.'
            return self._bundle(series, self.clock(), status, warning)

    def _bundle(self, series, now, status, warning):
        today = now.astimezone(ZoneInfo(series.timezone)).date()
        return SolarForecast(requested_location=series.location, model_grid_location=series.grid_location, timezone=series.timezone,
            retrieved_at=series.retrieved_at, expires_at=series.retrieved_at+self.ttl, cache_status=status,
            source_url=series.source_url, days=[local_day(series,today), local_day(series,today+timedelta(days=1))],
            warnings=([warning] if warning else [])+[
                'Numerical weather-model forecast, not a ground observation or measured clinic electricity generation.',
                'Today includes elapsed hours from the current forecast series; it is not a now-to-midnight simulation.'])
