import type { SimulationRequest, SimulationResponse } from "./api";

export interface ForecastLocation {
  latitude: number;
  longitude: number;
}
export interface ForecastHour {
  start: string;
  end: string;
  shortwave_radiation_w_m2: number;
  irradiance_kwh_m2: number;
}
export interface ForecastDay {
  date: string;
  hours: ForecastHour[];
  simulation_supported: boolean;
  warnings: string[];
}
export interface SolarForecast {
  source: "Open-Meteo Forecast API";
  data_kind: "weather_model_forecast";
  requested_location: ForecastLocation;
  model_grid_location: ForecastLocation;
  timezone: string;
  retrieved_at: string;
  expires_at: string;
  cache_status: "live" | "cached" | "stale";
  source_url: string;
  attribution_url: string;
  licence_url: string;
  interval_convention: string;
  days: ForecastDay[];
  warnings: string[];
}
export interface ForecastPlanRequest extends ForecastLocation {
  clinic: SimulationRequest;
  day: "today" | "tomorrow";
  midnight_battery_kwh: number;
  reduced_sunshine_factors?: number[];
}
export interface ForecastPlanResponse {
  forecast: SolarForecast;
  planning_date: string;
  midnight_battery_kwh: number;
  initial_battery_basis: string;
  plan: SimulationResponse;
  uncertainty_cases: { sunshine_factor: number; plan: SimulationResponse }[];
  assessment: string;
  actions: string[];
  limitations: string[];
}
export interface GuidedForecastResponse {
  mode: "deterministic_guided_fallback";
  needs_clarification: boolean;
  message: string;
  tool_calls: { name: string; arguments: Record<string, unknown> }[];
  result: ForecastPlanResponse | null;
  selected_sunshine_factor: number;
}
