/** Transport adapter for Main Chat's contracts/planning.ts. No client planner. */
import type {
  ActivityDraft,
  EnergySettingsPatch,
  BatteryReading,
  PlanningConversation,
  CreatePlanningSession,
  PlanningState,
  SessionAgentResponse,
} from "../../../../contracts/planning";
export class PlanningApiError extends Error {
  constructor(
    public code: string,
    message: string,
    public status: number,
  ) {
    super(message);
  }
}
async function request<T>(
  path: string,
  method = "GET",
  body?: unknown,
  signal?: AbortSignal,
  timeoutMs=90000,
): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`/api/planning/sessions${path}`, {
      method,
      headers: body === undefined ? {} : { "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
      signal: signal
        ? AbortSignal.any([signal, AbortSignal.timeout(timeoutMs)])
        : AbortSignal.timeout(timeoutMs),
    });
  } catch (error) {
    if (signal?.aborted) throw error;
    throw new PlanningApiError(
      "CONNECTION_UNAVAILABLE",
      "LifeLine could not finish the request. Check the local server, then retry. Your last confirmed server state will be reloaded when available.",
      0,
    );
  }
  let data;
  try {
    data = await response.json();
  } catch {
    throw new PlanningApiError(
      "UNREADABLE_RESPONSE",
      "The local server returned an unreadable response. Reload the shared state before retrying.",
      response.status,
    );
  }
  if (!response.ok)
    throw new PlanningApiError(
      data.error?.code ?? "REQUEST_FAILED",
      data.error?.message ?? "The request could not be completed.",
      response.status,
    );
  return data as T;
}
const sessionPath = (id: string) => `/${encodeURIComponent(id)}`;
const proposalPath = (id: string, proposal: string) =>
  `${sessionPath(id)}/proposals/${encodeURIComponent(proposal)}`;
export const planningApi = {
  create: (body: CreatePlanningSession, signal?: AbortSignal) =>
    request<PlanningState>("", "POST", body, signal),
  read: (id: string, signal?: AbortSignal) =>
    request<PlanningState>(sessionPath(id), "GET", undefined, signal),
  propose: (
    state: PlanningState,
    details: ActivityDraft,
    target_activity_id?: string,
  ) =>
    request<PlanningState>(`${sessionPath(state.id)}/proposals`, "POST", {
      expected_revision: state.revision,
      details,
      ...(target_activity_id ? { target_activity_id } : {}),
    }),
  edit: (state: PlanningState, proposal: string, details: ActivityDraft) =>
    request<PlanningState>(proposalPath(state.id, proposal), "PATCH", {
      expected_revision: state.revision,
      details,
    }),
  confirm: (state: PlanningState, proposal: string, idempotency_key: string) =>
    request<PlanningState>(
      `${proposalPath(state.id, proposal)}/confirm`,
      "POST",
      { expected_revision: state.revision, idempotency_key },
    ),
  reject: (state: PlanningState, proposal: string) =>
    request<PlanningState>(
      `${proposalPath(state.id, proposal)}/reject`,
      "POST",
      { expected_revision: state.revision },
    ),
  conversation: (id:string, signal?:AbortSignal) => request<PlanningConversation>(`${sessionPath(id)}/conversation`,"GET",undefined,signal),
  proposeEnergy: (state:PlanningState, settings:EnergySettingsPatch, reading?:BatteryReading|null) => request<PlanningState>(`${sessionPath(state.id)}/energy-proposals`,"POST",{expected_revision:state.revision,settings,...(reading !== undefined ? {current_battery_reading:reading} : {})}),
  editEnergy: (state:PlanningState, id:string, settings:EnergySettingsPatch, reading?:BatteryReading|null) => request<PlanningState>(`${sessionPath(state.id)}/energy-proposals/${encodeURIComponent(id)}`,"PATCH",{expected_revision:state.revision,settings,...(reading !== undefined ? {current_battery_reading:reading} : {})}),
  confirmEnergy: (state:PlanningState,id:string,key:string) => request<PlanningState>(`${sessionPath(state.id)}/energy-proposals/${encodeURIComponent(id)}/confirm`,"POST",{expected_revision:state.revision,idempotency_key:key}),
  rejectEnergy: (state:PlanningState,id:string) => request<PlanningState>(`${sessionPath(state.id)}/energy-proposals/${encodeURIComponent(id)}/reject`,"POST",{expected_revision:state.revision}),
  recompute: (state: PlanningState, sunshine_factor = state.sunshine_factor) =>
    request<PlanningState>(`${sessionPath(state.id)}/recompute`, "POST", {
      expected_revision: state.revision,
      sunshine_factor,
      include_recovery: true,
    }),
  selectRecovery: (state: PlanningState, option_id: string) => {
    if (!state.computed_plan)
      throw new Error(
        "Calculate the current plan before selecting a recovery comparison.",
      );
    return request<PlanningState>(
      `${sessionPath(state.id)}/recovery-selection`,
      "POST",
      {
        expected_revision: state.revision,
        input_revision: state.input_revision,
        generation: state.computed_plan.generation,
        option_id,
      },
    );
  },
  ask: (state: PlanningState, question: string, signal?: AbortSignal) =>
    request<SessionAgentResponse>(
      `${sessionPath(state.id)}/agent`,
      "POST",
      { expected_revision: state.revision, question },
      signal,
      120000,
    ),
};
export function currentPlan(
  state: PlanningState | null,
  invalidating: boolean,
) {
  return state?.plan_status === "current" &&
    !invalidating &&
    state.computed_plan?.input_revision === state.input_revision
    ? state.computed_plan
    : null;
}
