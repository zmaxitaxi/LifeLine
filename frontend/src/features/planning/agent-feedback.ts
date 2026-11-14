import type { AgentFailure,SessionAgentEvent } from "../../../../contracts/planning";
/** Public system status, not a replacement for Llama's answer or private reasoning. */
export function progressLabel(event:Extract<SessionAgentEvent,{type:'progress'}>){
 if(event.status==='failed')return 'Checking what prevented the reply…';
 return ({request:'Request received. Preparing the assistant…',model:'The assistant is preparing a reply…',weather:'Checking the weather data…',simulation:'Calculating electricity and comparing schedules…',serialization:'Preparing the verified results…',persistence:'Saving the shared clinic state…'})[event.stage];
}
export function failureLabel(failure?:AgentFailure|null){
 if(!failure)return 'The assistant couldn’t finish this reply. Please retry.';
 switch(failure.code){
  case 'DATE_MISMATCH':return `This clinic is planning ${failure.selected_date??'a different day'}, while your request refers to ${failure.requested_date??'another day'}. Tell LifeLine which day you want to discuss.`;
  case 'WEATHER_UNAVAILABLE':return 'Weather data is unavailable. Your confirmed requirements are saved; retry when the weather source is available.';
  case 'MODEL_BUSY':return 'The assistant is answering another request. Wait a moment, then retry.';
  case 'MODEL_TIMEOUT':return 'The assistant took too long to finish. Your saved clinic details remain available.';
  case 'MODEL_UNAVAILABLE':return 'The assistant is disconnected. Reconnect the model, then retry.';
  default:return 'The assistant could not verify its reply. Review your clinic details or retry.';
 }
}
