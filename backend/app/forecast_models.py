"""Public contracts for forecast-backed planning; the energy model stays 24-hour."""
from datetime import date, datetime
from typing import Annotated, Literal
from pydantic import Field, model_validator
from .models import Energy, SimulationRequest, SimulationResponse, StrictModel


class ForecastLocation(StrictModel):
    latitude: Annotated[float, Field(ge=-90, le=90)]
    longitude: Annotated[float, Field(ge=-180, le=180)]


class ForecastHour(StrictModel):
    start: datetime
    end: datetime
    shortwave_radiation_w_m2: float
    irradiance_kwh_m2: float


class ForecastDay(StrictModel):
    date: date
    hours: list[ForecastHour]
    simulation_supported: bool
    warnings: list[str]


class SolarForecast(StrictModel):
    source: Literal['Open-Meteo Forecast API'] = 'Open-Meteo Forecast API'
    data_kind: Literal['weather_model_forecast'] = 'weather_model_forecast'
    requested_location: ForecastLocation
    model_grid_location: ForecastLocation
    timezone: str
    retrieved_at: datetime
    expires_at: datetime
    cache_status: Literal['live', 'cached', 'stale']
    source_url: str
    attribution_url: str = 'https://open-meteo.com/'
    licence_url: str = 'https://creativecommons.org/licenses/by/4.0/'
    interval_convention: str = 'Open-Meteo preceding-hour mean, aligned to local interval starts by overlap integration.'
    days: list[ForecastDay]
    warnings: list[str]


class ForecastPlanRequest(ForecastLocation):
    clinic: SimulationRequest
    day: Literal['today', 'tomorrow'] = 'tomorrow'
    midnight_battery_kwh: Energy
    reduced_sunshine_factors: Annotated[list[Annotated[float, Field(ge=0, lt=1)]], Field(max_length=3)] = [.75, .5]

    @model_validator(mode='after')
    def unique_factors(self):
        if len(set(self.reduced_sunshine_factors)) != len(self.reduced_sunshine_factors):
            raise ValueError('Use unique reduced-sunshine factors')
        return self


class ForecastStressCase(StrictModel):
    sunshine_factor: float
    plan: SimulationResponse


class ForecastPlanResponse(StrictModel):
    forecast: SolarForecast
    planning_date: date
    midnight_battery_kwh: float
    initial_battery_basis: str
    plan: SimulationResponse
    uncertainty_cases: list[ForecastStressCase]
    assessment: str
    actions: list[str]
    limitations: list[str]


class GuidedPlanRequest(ForecastPlanRequest):
    question: Annotated[str, Field(min_length=1, max_length=2000)]


class PlannerToolCall(StrictModel):
    name: Literal['get_clinic_configuration', 'get_solar_forecast', 'plan_forecast']
    arguments: dict


class PlannerContext(ForecastLocation):
    clinic: SimulationRequest
    midnight_battery_kwh: Energy | None = None


class PlannerToolRequest(PlannerContext):
    tool_call: PlannerToolCall


class PlanForecastArguments(StrictModel):
    day: Literal['today', 'tomorrow'] = 'tomorrow'
    reduced_sunshine_factors: Annotated[list[Annotated[float, Field(ge=0, lt=1)]], Field(max_length=3)] = [.75, .5]


class EmptyArguments(StrictModel):
    pass


class GuidedForecastResponse(StrictModel):
    mode: Literal['deterministic_guided_fallback'] = 'deterministic_guided_fallback'
    needs_clarification: bool
    tool_calls: list[PlannerToolCall]
    message: str
    result: ForecastPlanResponse | None
