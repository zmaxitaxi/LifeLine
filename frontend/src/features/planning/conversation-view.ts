import type { AgentPresentation, ComputedPlan, PlanningMessage, PlanningState } from "../../../../contracts/planning";
import { failureLabel } from "./agent-feedback";
export interface ChatMessage {
  id:string;createdAt:string;role:"user"|"assistant"|"notice";text:string;tools?:string[];
  presentation?:AgentPresentation|null;plan?:ComputedPlan;date?:string;sessionId?:string;
  retryQuestion?:string;selectionId?:string;optionIds?:string[];showSchedule?:boolean;
}
export function resultAttachment(presentation:AgentPresentation|null|undefined,state:PlanningState):Partial<ChatMessage> {
  const result=state.computed_plan;
  if(!presentation || presentation.kind === "conversation" || state.plan_status !== "current" || !result || result.input_revision !== state.input_revision || presentation.input_revision !== result.input_revision || presentation.generation !== result.generation || (!presentation.show_schedule && !presentation.option_ids.length))return {};
  const validIds=new Set(result.recovery ? [result.recovery.existing.id,...result.recovery.options.map(option=>option.id)] : []);
  const ids=[...new Set(presentation.option_ids.filter(id=>validIds.has(id)))];
  if(!presentation.show_schedule && !ids.length)return {};
  return {plan:result,date:state.planning_date,sessionId:state.id,selectionId:ids.length === 1 ? ids[0] : undefined,optionIds:ids.length > 1 ? ids : [],showSchedule:presentation.show_schedule};
}
export function restoreMessages(messages:PlanningMessage[],state:PlanningState):ChatMessage[] {
  let question:string|undefined;
  return messages.map(message=>{
    if(message.role === "user")question=message.content;
    const failed=message.mode === "local_agent_unavailable";
    return {id:message.id,createdAt:message.created_at,role:failed ? "notice" : message.role,text:failed ? failureLabel(message.failure) : message.content,presentation:message.presentation,...(failed ? {retryQuestion:!message.failure || message.failure.retryable ? question : undefined} : resultAttachment(message.presentation,state))};
  });
}
