/**
 * LifeLine API contract v1.0 — implemented by backend/app/models.py.
 * Numeric values are finite. Hour is a slot index 0..23, boundary is 0..24.
 * See docs/BUILD_BRIEF.md for validation and cross-field constraints.
 */
export type ScenarioId = "scheduling" | "normal" | "storm" | "high_demand";
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
  equipment?: Equipment[];
  cloud_factors?: number[];
  weather_dataset?: "synthetic" | "kisumu-2025-01-14";
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
  equipment: Equipment[];
  cloud_factors: number[];
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
  plan: "baseline" | "heuristic" | "optimized";
  message: string;
}

export interface Recommendation {
  severity: "info" | "warning" | "critical";
  title: string;
  explanation: string;
  task_id?: string | null;
  hours?: number[] | null;
}

export interface ComparisonMetrics {
  /** Compare per-task served energy, not just the total. */
  same_flexible_work_completed: boolean;
  /** Signed optimized minus baseline stored energy at boundary 24. */
  battery_preserved_at_midnight_kwh: number;
  minimum_battery_improvement_kwh: number;
  /** Difference between minimum stored energy over boundaries 18..24. */
  evening_minimum_improvement_kwh: number;
  /** Signed baseline minus optimized conversion loss. */
  conversion_loss_reduction_kwh: number;
  /** Key metric equality within 1e-6, not necessarily identical allocations. */
  heuristic_matches_optimizer_metrics: boolean;
}

export interface SimulationResponse {
  api_version: "1.0";
  model_version: string;
  scenario: ScenarioId;
  scenario_name: string;
  data_source: "synthetic" | "user_defined" | "mixed";
  cloud_factors: number[];
  input_provenance: Record<string, string>;
  weather_dataset: string;
  diagnosis: {
    assessment: string;
    explanation: string;
    constraints: string[];
    discharge_limited_hours: number[];
    optimistic_energy_deficit_kwh: number;
    window_limited_tasks: string[];
  };
  timezone: string;
  horizon_hours: 24;
  dt_hours: 1;
  pv_performance_ratio: number;
  effective_config: EffectiveConfig;
  equipment: Equipment[];
  assumptions: string[];
  /** Always equals optimized.status, never a preassigned scenario label. */
  status: RiskStatus;
  baseline: PlanResult;
  heuristic: PlanResult;
  optimized: PlanResult;
  comparison: ComparisonMetrics;
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
      | "INTERNAL_ERROR"
      | "FORECAST_UNAVAILABLE"
      | "FORECAST_DATA_INVALID"
      | "UNSUPPORTED_FORECAST_DAY"
      | "AGENT_UNAVAILABLE";
    message: string;
    /** Empty unless individual request fields need correction. */
    details: Array<{
      loc: Array<string | number>;
      message: string;
      type: string;
    }>;
  };
}

/** The bundled assistant works without an external AI provider. */
export interface PlanningQuestion {
  kind:
    | "intent"
    | "equipment"
    | "deadline"
    | "duration"
    | "power"
    | "start"
    | "battery";
  prompt: string;
  task_id: string | null;
  equipment_name: string;
  power_w: number | null;
  deadline: number;
  duration_h: number | null;
}
export interface AssistantResponse {
  mode: "offline";
  message: string;
  question: PlanningQuestion | null;
  request: SimulationRequest | null;
  result: SimulationResponse | null;
  tools_used: string[];
}
export interface PlanningStatus {
  assistant: "offline";
  timezone: "Africa/Nairobi";
  forecast: {
    available: false;
    reason: string;
    source: null;
    forecast_date: null;
    requested_date: string;
    updated_at: null;
  };
}
