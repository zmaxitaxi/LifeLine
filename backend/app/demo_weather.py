"""Explicit offline sample conditions, never disguised as a live forecast."""
from datetime import datetime, timedelta, timezone
import math
from zoneinfo import ZoneInfo
from .forecast_models import SolarForecast, ForecastDay, ForecastHour
from .weather_outlook_models import WeatherOutlook, CurrentWeather, DailyWeather

SOURCE = 'LifeLine synthetic demo weather'
SOURCE_URL = 'https://github.com/zmaxitaxi/LifeLine/blob/main/docs/DEMO_WEATHER.md'
WARNING = ('SYNTHETIC DEMO WEATHER: assumed clear-day irradiation and sample temperatures, not observations or a live forecast. '
           'The declared demo timezone is Africa/Nairobi; these conditions are not a geographic weather prediction.')


class DemoWeatherService:
    def __init__(self, clock=None):
        self.clock = clock or (lambda: datetime.now(timezone.utc))

    async def get(self, location):
        now = self.clock()
        zone = ZoneInfo('Africa/Nairobi')
        today = now.astimezone(zone).date()
        days = []
        for offset in (0, 1):
            day = today + timedelta(days=offset)
            midnight = datetime(day.year, day.month, day.day, tzinfo=zone)
            hours = []
            for hour in range(24):
                radiation = 800. * math.sin(math.pi * (hour + .5 - 6) / 12) if 6 <= hour < 18 else 0.
                hours.append(ForecastHour(start=midnight + timedelta(hours=hour),
                    end=midnight + timedelta(hours=hour+1),
                    shortwave_radiation_w_m2=radiation, irradiance_kwh_m2=radiation/1000))
            days.append(ForecastDay(date=day, hours=hours, simulation_supported=True, warnings=[WARNING]))
        return SolarForecast(source=SOURCE, data_kind='synthetic_demo_weather', weather_mode='demo',
            requested_location=location, model_grid_location=location,
            timezone='Africa/Nairobi', retrieved_at=now, expires_at=now+timedelta(hours=1),
            cache_status='cached', source_url=SOURCE_URL, attribution_url=SOURCE_URL, licence_url='',
            interval_convention='Assumed hourly mean W/m², zero outside 06:00–18:00 in the declared demo timezone; kWh/m² = W/m² ÷ 1000 for each one-hour slot.',
            days=days, warnings=[WARNING])


class DemoOutlookService(DemoWeatherService):
    async def get(self, location):
        now = self.clock()
        local = now.astimezone(ZoneInfo('Africa/Nairobi'))
        days = [DailyWeather(date=local.date()+timedelta(days=offset), weather_code=0,
            condition='clear', description='Sample clear conditions', temperature_min_c=20.,
            temperature_max_c=28., precipitation_probability_pct=0.) for offset in range(7)]
        return WeatherOutlook(source=SOURCE, data_kind='synthetic_demo_weather', weather_mode='demo',
            requested_location=location, model_grid_location=location, timezone='Africa/Nairobi',
            provider_utc_offset_seconds=10800, retrieved_at=now, expires_at=now+timedelta(hours=1),
            cache_status='cached', source_url=SOURCE_URL, attribution_url=SOURCE_URL, licence_url='',
            current=CurrentWeather(valid_at=now, interval_seconds=3600, temperature_c=24.,
                weather_code=0, condition='clear', description='Sample clear conditions', is_day=6<=local.hour<18),
            days=days, daily_period_basis='Synthetic sample daily rows, not a seven-day energy calculation.', warnings=[WARNING])
