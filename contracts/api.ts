/**
 * LifeLine API contract v1.0 — planned implementation, not an API client.
 * Numeric values are finite. Hour is a slot index 0..23, boundary is 0..24.
 * See docs/BUILD_BRIEF.md for validation and cross-field constraints.
 */
export type ScenarioId = "normal" | "storm" | "high_demand";
export type RiskStatus = "OK" | "RESERVE_AT_RISK" | "CRITICAL_SHORTAGE";

export interface EffectiveConfig {
  battery_capacity_kwh: number;
  initial_battery_kwh: number;
  reserve_kwh: number;
  pv_capacity_kw: number;
  charge_efficiency: number;
  discharge_efficiency: number;
  max_charge_kw: number;
  max_discharge_kw: number;
  additional_critical_kw: number;
}

/** Omitted properties use preset defaults; explicit null is invalid. */
export interface SimulationRequest {
  scenario: ScenarioId;
  battery_capacity_kwh?: number;
  initial_battery_kwh?: number;
  reserve_kwh?: number;
  pv_capacity_kw?: number;
  charge_efficiency?: number;
  discharge_efficiency?: number;
  max_charge_kw?: number;
  max_discharge_kw?: number;
  /** Override permitted only for high_demand, including explicit zero. */
  additional_critical_kw?: number;
}

export interface HealthResponse {
  status: "ok";
  api_version: "1.0";
}

export interface ScenarioSummary {
  id: ScenarioId;
  name: string;
  description: string;
  data_source: "synthetic";
  defaults: EffectiveConfig;
  /** Describes defaults only; never a substitute for computed status. */
  expected_status: RiskStatus;
}

export interface ScenarioListResponse {
  api_version: "1.0";
  scenarios: ScenarioSummary[];
}

export interface CriticalEquipment {
  id: string;
  name: string;
  category: "critical";
  power_kw: number;
  required_hours: number[];
}

export interface FlexibleEquipment {
  id: string;
  name: string;
  category: "flexible";
  max_power_kw: number;
  required_energy_kwh: number;
  allowed_hours: number[];
  baseline_allocations: RequestedTaskAllocation[];
  divisible: true;
}

export type Equipment = CriticalEquipment | FlexibleEquipment;

export interface RequestedTaskAllocation {
  hour: number;
  requested_kwh: number;
}

export interface TaskAllocation {
  hour: number;
  served_kwh: number;
}

export interface FlexibleTaskResult {
  task_id: string;
  requested_kwh: number;
  served_kwh: number;
  /** Unserved within this horizon; no next-day placement is promised. */
  deferred_kwh: number;
  /** Served allocations only, sorted by hour, no duplicate hours. */
  allocations: TaskAllocation[];
}

export interface HourlyResult {
  hour: number;
  pv_kwh: number;
  critical_requested_kwh: number;
  critical_served_kwh: number;
  critical_unserved_kwh: number;
  /** Baseline fixed request or optimized allocation. */
  flexible_planned_kwh: number;
  flexible_served_kwh: number;
  /** Missed scheduled energy; horizon deferral lives in task results. */
  flexible_unserved_kwh: number;
  charge_input_kwh: number;
  discharge_output_kwh: number;
  curtailed_kwh: number;
  soc_start_kwh: number;
  soc_end_kwh: number;
}

export interface PlanMetrics {
  total_solar_kwh: number;
  critical_requested_kwh: number;
  critical_unserved_kwh: number;
  /** Energy-weighted; null if requested critical energy is zero. */
  critical_coverage_pct: number | null;
  min_soc_kwh: number;
  final_soc_kwh: number;
  flexible_requested_kwh: number;
  flexible_served_kwh: number;
  flexible_deferred_kwh: number;
  curtailed_kwh: number;
  conversion_loss_kwh: number;
  critical_shortage_hours: number[];
  reserve_breach_boundaries: number[];
}

export interface PlanResult {
  status: RiskStatus;
  /** Exactly 24 records sorted by hour, with continuous battery states. */
  hourly: HourlyResult[];
  metrics: PlanMetrics;
  flexible_tasks: FlexibleTaskResult[];
}

export interface SimulationWarning {
  code: "CRITICAL_UNSERVED" | "RESERVE_BELOW_TARGET" | "FLEXIBLE_DEFERRED";
  plan: "baseline" | "optimized";
  message: string;
}

export interface Recommendation {
  severity: "info" | "warning" | "critical";
  title: string;
  explanation: string;
  task_id?: string;
  hours?: number[];
}

export interface SimulationResponse {
  api_version: "1.0";
  model_version: string;
  scenario: ScenarioId;
  scenario_name: string;
  data_source: "synthetic";
  timezone: "Africa/Nairobi";
  horizon_hours: 24;
  dt_hours: 1;
  pv_performance_ratio: number;
  effective_config: EffectiveConfig;
  equipment: Equipment[];
  assumptions: string[];
  /** Always equals optimized.status, never a preassigned scenario label. */
  status: RiskStatus;
  baseline: PlanResult;
  optimized: PlanResult;
  warnings: SimulationWarning[];
  recommendations: Recommendation[];
}

export interface ApiErrorResponse {
  error: {
    code:
      | "INVALID_REQUEST"
      | "SOLVER_UNAVAILABLE"
      | "SOLVER_TIME_LIMIT"
      | "NUMERICAL_ERROR"
      | "INTERNAL_ERROR";
    message: string;
    /** Empty unless individual request fields need correction. */
    details: Array<{
      loc: Array<string | number>;
      message: string;
      type: string;
    }>;
  };
}
