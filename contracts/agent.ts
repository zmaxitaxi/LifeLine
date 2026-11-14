import type { ForecastPlanResponse } from "./forecast";
import type { SimulationRequest, SimulationResponse } from "./api";

import type { RecoveryResponse } from "./recovery";
export interface FixedRequirementArguments {
  day?: "today" | "tomorrow";
  name: string;
  power_kw: number;
  duration_hours: number;
  earliest_start: number;
  deadline: number;
  sunshine_factor?: number;
}

export interface AgentRequest {
  clinic: SimulationRequest;
  latitude: number;
  longitude: number;
  question: string;
  previous_questions: string[];
  inputs_confirmed: boolean;
  input_basis: "synthetic_example" | "operator_entered_unverified";
  day: "today" | "tomorrow";
  current_battery_pct: number | null;
  starting_battery_pct: number | null;
  starting_charge_confirmed: boolean;
  use_configured_context?: boolean;
  context_sunshine_factor?: number;
  active_requirement?: FixedRequirementArguments | null;
  optional_load_ids?: string[];
  weather_mode?: "live_forecast" | "existing_scenario";
}
export interface AgentActivity {
  type: "activity";
  id: string;
  label: string;
  status: "running" | "completed" | "warning" | "failed";
  elapsed_ms: number;
}
export type AgentStreamEvent =
  | AgentActivity
  | { type: "answer"; response: AgentResponse }
  | { type: "error"; code: string; message: string };

export interface AgentStatus {
  mode: "local_tool_agent" | "cloud_tool_agent" | "deterministic_guided_fallback";
  available: boolean;
  model: string | null;
  provider: string;
  cloud_ai: boolean;
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
  recovery: RecoveryResponse | null;
  fallback_reason: string | null;
  input_basis: "synthetic_example" | "operator_entered_unverified";
  selected_sunshine_factor: number;
  suggested_starting_battery_pct: number | null;
  requirement: {
    name: string;
    start_hour: number;
    end_hour: number;
    candidates_evaluated: number;
    essential_requirements_fully_supplied: boolean;
    original: ForecastPlanResponse;
    proposed: ForecastPlanResponse;
    explanation: string;
    arguments: FixedRequirementArguments | null;
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
