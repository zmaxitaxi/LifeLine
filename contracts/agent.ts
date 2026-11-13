import type { ForecastPlanResponse } from "./forecast";

export interface AgentStatus {
  mode: "local_tool_agent" | "deterministic_guided_fallback";
  available: boolean;
  model: string | null;
  provider: string;
  cloud_ai: false;
  note: string;
}
export interface AgentResponse {
  mode: AgentStatus["mode"];
  model: string | null;
  message: string;
  needs_clarification: boolean;
  clarification_field: string | null;
  tool_calls: {
    name: string;
    status: "completed" | "rejected" | "unavailable";
  }[];
  result: ForecastPlanResponse | null;
  fallback_reason: string | null;
  input_basis: "synthetic_example" | "operator_entered_unverified";
  selected_sunshine_factor: number;
  requirement: {
    name: string;
    start_hour: number;
    end_hour: number;
    candidates_evaluated: number;
    essential_requirements_fully_supplied: boolean;
    original: ForecastPlanResponse;
    proposed: ForecastPlanResponse;
    explanation: string;
  } | null;
  capacity: {
    target: "essential" | "all_work";
    sunshine_factor: number;
    current_capacity_kwh: number;
    tested_capacity_kwh: number | null;
    additional_capacity_kwh: number | null;
    resolution_kwh: number;
    search_limit_kwh: number;
    samples: {
      battery_capacity_kwh: number;
      essential_unmet_kwh: number;
      flexible_deferred_kwh: number;
      minimum_battery_kwh: number;
      reserve_breached: boolean;
      meets_target: boolean;
    }[];
    explanation: string;
    assumptions: string[];
  } | null;
}
