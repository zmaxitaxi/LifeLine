import type { Equipment, SimulationRequest, SimulationResponse, EffectiveConfig } from './api';
import type { ForecastLocation, SolarForecast } from './forecast';
import type { RecoveryResponse } from './recovery';
export interface EquipmentConstraint { equipment_id: string; required_hours?: number[] | null; allowed_hours?: number[] | null; /** Minimum TOTAL DAILY device runtime; shared requirements aggregate by max with baseline, not addition. */ required_duration_hours?: number|null }
export interface ProposedEquipment { id: string; name: string; category?: 'critical'|'flexible'|null; power_kw?: number|null; required_hours?: number[]|null; max_power_kw?: number|null; required_energy_kwh?: number|null; required_duration_hours?: number|null; allowed_hours?: number[]|null; divisible?: true|null }
export interface ActivityDraft { name?: string|null; planning_date?: string|null; start_hour?: number|null; end_hour?: number|null; deadline_hour?: number|null; duration_hours?: number|null; equipment_ids?: string[]|null; equipment_constraints?: EquipmentConstraint[]; additional_equipment?: ProposedEquipment[] }
export interface Activity { id: string; version: number; status: 'confirmed'; details: ActivityDraft }
export interface ActivityProposal { id: string; status: 'draft'|'confirmed'|'rejected'; target_activity_id: string|null; base_activity_version: number|null; details: ActivityDraft; missing_fields: string[]; confirmed_activity_id: string|null }
export interface ComputedPlan { weather_mode: 'live'|'demo'; input_revision: number; generation: number; computed_at: string; sunshine_factor: number; simulation: SimulationResponse; recovery: RecoveryResponse|null }
export interface BatteryReading { energy_kwh: number; measured_at: string }
export interface EnergySettingsPatch { battery_capacity_kwh?: number; initial_battery_kwh?: number; reserve_kwh?: number; pv_capacity_kw?: number; charge_efficiency?: number; discharge_efficiency?: number; max_charge_kw?: number; max_discharge_kw?: number }
export interface EnergySettingsProposal { id: string; status: 'draft'|'confirmed'|'rejected'; base_input_revision: number; settings: EnergySettingsPatch; proposed_energy_settings: EffectiveConfig; current_battery_reading: BatteryReading|null; updates_current_battery_reading: boolean }
export interface PlanningState { id: string; revision: number; input_revision: number; selected_clinic_id: string; clinic_name: string; location: ForecastLocation; planning_date: string; timezone: string|null; clinic: SimulationRequest; equipment_inventory: Equipment[]; energy_settings: EffectiveConfig; current_battery_reading: BatteryReading|null; energy_proposals: EnergySettingsProposal[]; active_energy_proposal_id: string|null; confirmed_activities: Activity[]; proposals: ActivityProposal[]; active_proposal_id: string|null; forecast_reference: SolarForecast|null; computed_plan: ComputedPlan|null; plan_status: 'not_computed'|'pending'|'current'|'failed'; plan_error: string|null; selected_recovery_intervention_id: string|null; sunshine_factor: number }
export interface CreatePlanningSession { selected_clinic_id: string; clinic_name: string; location: ForecastLocation; planning_date: string; clinic: SimulationRequest; midnight_battery_kwh: number; current_battery_reading?: BatteryReading|null; timezone?: string|null }
export interface RevisionRequest { expected_revision: number }
export interface CreateActivityProposal extends RevisionRequest { details: ActivityDraft; target_activity_id?: string|null }
export interface UpdateActivityProposal extends RevisionRequest { details: ActivityDraft }
export interface ConfirmActivityProposal extends RevisionRequest { idempotency_key: string }
export type RejectActivityProposal = RevisionRequest;
export interface RecomputePlanningState extends RevisionRequest { sunshine_factor?: number|null; include_recovery?: boolean }
export interface SelectRecoveryIntervention extends RevisionRequest { input_revision: number; generation: number; option_id: string }
export interface SessionAgentRequest extends RevisionRequest { question: string }
export interface CreateEnergySettingsProposal extends RevisionRequest { settings?: EnergySettingsPatch; current_battery_reading?: BatteryReading|null }
export type UpdateEnergySettingsProposal = CreateEnergySettingsProposal;
export interface AgentPresentation { kind: 'conversation'|'activity_review'|'energy_review'|'calculation'|'explanation'; input_revision: number|null; generation: number|null; option_ids: string[]; show_schedule: boolean }
export interface PlanningMessage { id: string; role: 'user'|'assistant'; content: string; created_at: string; presentation: AgentPresentation|null; mode: 'local_tool_agent'|'local_agent_unavailable'|null; imported: boolean; failure?:AgentFailure|null }
export interface PlanningConversation { session_id: string; messages: PlanningMessage[] }
export interface AgentFailure { code: 'MODEL_TIMEOUT'|'MODEL_BUSY'|'MODEL_UNAVAILABLE'|'MODEL_INVALID_OUTPUT'|'MODEL_VALIDATION_FAILED'|'WEATHER_UNAVAILABLE'|'DATE_MISMATCH'; retryable: boolean; suggested_action:'retry'|'wait_model'|'review_date'|'review_inputs'; selected_date:string|null; requested_date:string|null }
export interface AgentTimings { total_seconds:number;first_progress_seconds:number|null;stages_seconds:Record<string,number>;model_calls:number|null;model_metrics:Record<string,number>[] }
export type SessionAgentEvent = {type:'progress';stage:'request'|'model'|'weather'|'simulation'|'serialization'|'persistence';status:'running'|'completed'|'failed';elapsed_seconds:number} | {type:'result';response:SessionAgentResponse} | {type:'error';error:{code:string;message:string}};
export interface SessionAgentResponse { mode: 'local_tool_agent'|'local_agent_unavailable'; model: string|null; message: string; needs_clarification: boolean; clarification_fields: string[]; tool_calls: string[]; presentation: AgentPresentation; message_id: string|null; user_message_id: string|null; state: PlanningState; failure:AgentFailure|null; timings:AgentTimings|null }
export interface PlanningError { error: { code: 'REVISION_CONFLICT'|'PROPOSAL_INCOMPLETE'|'INVALID_ACTIVITY'|'PROPOSAL_CLOSED'|'IDEMPOTENCY_CONFLICT'|'STALE_RESULT'|'NOT_FOUND'|'INVALID_REQUEST'|'UNSUPPORTED_FORECAST_DAY'|string; message: string; details: {loc:(string|number)[]; message:string; type:string}[] } }
