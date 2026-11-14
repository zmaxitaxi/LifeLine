"""Display weather is separate from the validated hourly solar energy inputs."""
from datetime import date, datetime
from typing import Annotated, Literal
from pydantic import Field
from .models import StrictModel
from .forecast_models import ForecastLocation

WeatherCondition = Literal['clear','mainly_clear','partly_cloudy','overcast','fog','drizzle','freezing_drizzle',
    'rain','freezing_rain','snow','rain_showers','snow_showers','thunderstorm','unavailable']


class CurrentWeather(StrictModel):
    valid_at: datetime
    interval_seconds: int
    temperature_c: float | None
    weather_code: int | None
    condition: WeatherCondition
    description: str
    is_day: bool | None


class DailyWeather(StrictModel):
    date: date
    weather_code: int | None
    condition: WeatherCondition
    description: str
    temperature_min_c: float | None
    temperature_max_c: float | None
    precipitation_probability_pct: float | None


class WeatherOutlook(StrictModel):
    source: Literal['Open-Meteo Forecast API', 'LifeLine synthetic demo weather'] = 'Open-Meteo Forecast API'
    data_kind: Literal['weather_model_current_and_daily_forecast', 'synthetic_demo_weather'] = 'weather_model_current_and_daily_forecast'
    weather_mode: Literal['live', 'demo'] = 'live'
    requested_location: ForecastLocation
    model_grid_location: ForecastLocation
    timezone: str
    provider_utc_offset_seconds: int
    retrieved_at: datetime
    expires_at: datetime
    cache_status: Literal['live','cached','stale']
    source_url: str
    attribution_url: str = 'https://open-meteo.com/'
    licence_url: str = 'https://creativecommons.org/licenses/by/4.0/'
    current: CurrentWeather
    days: Annotated[list[DailyWeather],Field(min_length=7,max_length=7)]
    daily_period_basis: str
    warnings: list[str]
