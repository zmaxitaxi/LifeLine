import type { EffectiveConfig, PlanResult, SimulationResponse } from "./api";
import type { SolarForecast } from "./forecast";

export interface RecoveryMetrics {
  essential_requested_kwh: number;
  essential_served_kwh: number;
  essential_unserved_kwh: number;
  original_flexible_required_kwh: number;
  tested_flexible_required_kwh: number;
  flexible_completed_kwh: number;
  flexible_unfinished_kwh: number;
  explicitly_postponed_kwh: number;
  minimum_battery_kwh: number;
  reserve_shortfall_kwh: number;
  reserve_breach_boundaries: number[];
  conversion_losses_kwh: number;
}
export interface RecoveryOption {
  id: string;
  label: string;
  kind: "existing" | "scheduling" | "solar" | "battery" | "output" | "optional";
  rank: number | null;
  config: EffectiveConfig;
  plan: PlanResult;
  simulation: SimulationResponse;
  metrics: RecoveryMetrics;
  infrastructure_changes: {field: "pv_capacity_kw" | "battery_capacity_kwh" | "max_discharge_kw"; before: number; after: number; unit: "kW" | "kWh"}[];
  work_changes: {equipment_id: string; name: string; original_required_kwh: number; tested_required_kwh: number; explicitly_postponed_kwh: number}[];
  essential_shortage_reduction_kwh: number;
  minimum_battery_improvement_kwh: number;
  flexible_completion_improvement_kwh: number;
  normalized_change_magnitude: number;
  modeled_essential_and_reserve_met: boolean;
  modeled_all_requirements_met: boolean;
  backup_deficits: {hour: number; electrical_energy_kwh: number}[];
  remaining_constraints: string[];
}
export interface RecoveryResponse {
  weather_mode: "live_forecast" | "existing_scenario";
  forecast: SolarForecast | null;
  planning_date: string | null;
  timezone: string;
  sunshine_factor: number;
  reference: SimulationResponse;
  existing: RecoveryOption;
  options: RecoveryOption[];
  problem_detected: boolean;
  triggers: string[];
  recommended_option_id: string;
  operational_option_id: string;
  smallest_tested_resolving_option_id: string | null;
  summary: string;
  next_action: string;
  assumptions: string[];
  limitations: string[];
}
