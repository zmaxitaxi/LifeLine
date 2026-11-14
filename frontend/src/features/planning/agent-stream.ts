import type { PlanningState,SessionAgentEvent,SessionAgentResponse } from "../../../../contracts/planning";
import { PlanningApiError } from "./planning-api";
/** One request only: losing a stream never silently repeats a state-changing tool. */
export async function askStream(state:PlanningState,question:string,onProgress:(event:Extract<SessionAgentEvent,{type:'progress'}>)=>void,signal?:AbortSignal):Promise<SessionAgentResponse>{
 const response=await fetch(`/api/planning/sessions/${encodeURIComponent(state.id)}/agent/stream`,{method:'POST',headers:{'Content-Type':'application/json',Accept:'text/event-stream'},body:JSON.stringify({expected_revision:state.revision,question}),signal:signal?AbortSignal.any([signal,AbortSignal.timeout(120000)]):AbortSignal.timeout(120000)});
 if(!response.ok){const value=await response.json().catch(()=>({}));throw new PlanningApiError(value.error?.code??'REQUEST_FAILED',value.error?.message??'The reply could not be completed.',response.status);}
 // A proxy may return the complete response as JSON. Do not repeat the POST.
 if(response.headers.get('content-type')?.includes('application/json'))return response.json();
 if(!response.body)throw new PlanningApiError('EMPTY_STREAM','The local response connection was empty. Reload the shared state before retrying.',0);
 const reader=response.body.getReader(),decoder=new TextDecoder();let buffer='',result:SessionAgentResponse|undefined;
 const consume=(frame:string)=>{const data=frame.split('\n').filter(line=>line.startsWith('data:')).map(line=>line.slice(5).trimStart()).join('\n');if(!data)return;const event=JSON.parse(data) as SessionAgentEvent;if(event.type==='progress')onProgress(event);else if(event.type==='result')result=event.response;else if(event.type==='error')throw new PlanningApiError(event.error.code,event.error.message,0);};
 try{while(true){const {value,done}=await reader.read();buffer+=decoder.decode(value,{stream:!done});buffer=buffer.replace(/\r\n/g,'\n');let boundary;while((boundary=buffer.indexOf('\n\n'))>=0){consume(buffer.slice(0,boundary));buffer=buffer.slice(boundary+2);}if(done){if(buffer.trim())consume(buffer);break;}}}
 finally{reader.releaseLock();}
 if(!result)throw new PlanningApiError('INTERRUPTED_STREAM','The connection ended before a verified reply arrived. Your clinic changes may already be saved; reload the shared state before retrying.',0);
 return result;
}
