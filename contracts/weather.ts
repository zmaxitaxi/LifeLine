import type { ForecastLocation } from "./forecast";

export type WeatherCondition = "clear" | "mainly_clear" | "partly_cloudy" | "overcast" | "fog" | "drizzle" | "freezing_drizzle" | "rain" | "freezing_rain" | "snow" | "rain_showers" | "snow_showers" | "thunderstorm" | "unavailable";
export interface WeatherOutlook {
  source: "Open-Meteo Forecast API";
  data_kind: "weather_model_current_and_daily_forecast";
  requested_location: ForecastLocation;
  model_grid_location: ForecastLocation;
  timezone: string;
  provider_utc_offset_seconds: number;
  retrieved_at: string;
  expires_at: string;
  cache_status: "live" | "cached" | "stale";
  source_url: string;
  attribution_url: string;
  licence_url: string;
  current: {
    valid_at: string;
    interval_seconds: number;
    temperature_c: number | null;
    weather_code: number | null;
    condition: WeatherCondition;
    description: string;
    is_day: boolean | null;
  };
  days: {
    date: string;
    weather_code: number | null;
    condition: WeatherCondition;
    description: string;
    temperature_min_c: number | null;
    temperature_max_c: number | null;
    precipitation_probability_pct: number | null;
  }[];
  daily_period_basis: string;
  warnings: string[];
}
