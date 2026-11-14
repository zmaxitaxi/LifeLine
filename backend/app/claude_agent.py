"""Claude Messages adapter; existing Python tools remain the execution boundary."""
import asyncio
import json
import os
from time import monotonic
import httpx
from .agent_telemetry import measured, record_model
from .local_agent import AgentUnavailable, definitions

API = 'https://api.anthropic.com/v1'


def messages_for_claude(messages):
    system=[]
    converted=[]
    pending=[]
    serial=0
    for item in messages:
        role=item['role']
        if role=='system':
            system.append(item['content'])
            continue
        blocks=[]
        if role=='tool':
            if not pending:
                raise AgentUnavailable('INVALID_AGENT_RESPONSE')
            identifier,name=pending.pop(0)
            if item.get('tool_name')!=name:
                raise AgentUnavailable('INVALID_AGENT_RESPONSE')
            blocks=[{'type':'tool_result','tool_use_id':identifier,'content':item['content']}]
            role='user'
        else:
            if item.get('content'):
                blocks.append({'type':'text','text':item['content']})
            for call in item.get('tool_calls',[]):
                serial+=1
                function=call['function']
                identifier=f'lifeline_tool_{serial}'
                blocks.append({'type':'tool_use','id':identifier,'name':function['name'],'input':function['arguments']})
                pending.append((identifier,function['name']))
        if blocks:
            if converted and converted[-1]['role']==role:
                converted[-1]['content'].extend(blocks)
            else:
                converted.append({'role':role,'content':blocks})
    if pending:
        raise AgentUnavailable('INVALID_AGENT_RESPONSE')
    return '\n\n'.join(system),converted


class ClaudeAgent:
    response_mode='cloud_tool_agent'

    def __init__(self, *, api_key=None, model=None, transport=None):
        self.api_key=api_key if api_key is not None else os.environ.get('ANTHROPIC_API_KEY','')
        self.model=model or os.environ.get('LIFELINE_CLAUDE_MODEL','claude-haiku-5-5')
        self.transport=transport
        self.lock=asyncio.Lock()
        self._status=None
        self._checked=0.

    def headers(self):
        return {'x-api-key':self.api_key,'anthropic-version':'2023-06-01','content-type':'application/json'}

    async def status(self):
        if self._status is not None and monotonic()-self._checked<30:
            return self._status
        ready=False
        if self.api_key:
            try:
                async with httpx.AsyncClient(transport=self.transport,trust_env=False,timeout=5.) as client:
                    result=await client.get(API+'/models/'+self.model,headers=self.headers())
                    ready=result.status_code==200 and isinstance(result.json().get('id'),str)
            except (httpx.HTTPError,ValueError,TypeError):
                pass
        self._checked=monotonic()
        self._status={'available':ready,'mode':'cloud_tool_agent' if ready else 'deterministic_guided_fallback',
            'model':self.model,'provider':'Anthropic Claude API','cloud_ai':True,
            'note':'Claude selects validated tools; Python computes all energy results. Clinic configuration and conversation are sent to Anthropic. No patient information is needed.'}
        return self._status

    async def session_turn(self,messages,*,toolset):
        if not self.api_key:
            raise AgentUnavailable('MODEL_UNAVAILABLE')
        if self.lock.locked():
            raise AgentUnavailable('LOCAL_AGENT_BUSY')
        system,converted=messages_for_claude(messages)
        payload={'model':self.model,'max_tokens':2048,'system':system,'messages':converted,
            'tools':[{'name':t['name'],'description':t.get('description',''),'input_schema':t['parameters']} for t in toolset],
            'tool_choice':{'type':'auto','disable_parallel_tool_use':True}}
        if '-5-5' in self.model:
            payload['output_config']={'effort':'low'}
        metrics={'request_chars':len(json.dumps(payload,separators=(',',':'))),
            'message_chars':len(json.dumps(converted,separators=(',',':'))),
            'tool_schema_chars':len(json.dumps(payload['tools'],separators=(',',':')))}
        async with self.lock:
            started=monotonic()
            try:
                with measured('model'):
                    async with httpx.AsyncClient(transport=self.transport,trust_env=False,timeout=httpx.Timeout(35.,connect=5.)) as client:
                        reply=await client.post(API+'/messages',headers=self.headers(),json=payload)
                        if reply.status_code==429:
                            raise AgentUnavailable('LOCAL_AGENT_BUSY')
                        reply.raise_for_status()
                        data=reply.json()
                usage=data.get('usage',{})
                metrics.update(prompt_eval_count=usage.get('input_tokens'),eval_count=usage.get('output_tokens'))
                if data.get('stop_reason')=='max_tokens':
                    raise AgentUnavailable('MODEL_OUTPUT_TRUNCATED')
                blocks=data['content']
                if not isinstance(blocks,list):
                    raise AgentUnavailable('INVALID_AGENT_RESPONSE')
                calls=[b for b in blocks if b.get('type')=='tool_use']
                text='\n'.join(b['text'] for b in blocks if b.get('type')=='text')
                # Thinking/redacted-thinking blocks never reach application text.
                if len(calls)>1:
                    raise AgentUnavailable('INVALID_AGENT_RESPONSE')
                if calls:
                    call=calls[0]
                    if not isinstance(call.get('name'),str) or not isinstance(call.get('input'),dict):
                        raise AgentUnavailable('INVALID_AGENT_RESPONSE')
                    return {'type':'tool_call','call':{'name':call['name'],'arguments':call['input']},'content':text}
                if not text.strip() or len(text)>6000:
                    raise AgentUnavailable('INVALID_AGENT_RESPONSE')
                return {'type':'message','content':text}
            except httpx.TimeoutException:
                raise AgentUnavailable('MODEL_TIMEOUT') from None
            except httpx.HTTPError:
                raise AgentUnavailable('MODEL_UNAVAILABLE') from None
            except (ValueError,KeyError,TypeError,AttributeError):
                raise AgentUnavailable('INVALID_AGENT_RESPONSE') from None
            finally:
                metrics['http_seconds']=monotonic()-started
                self.last_session_diagnostics=metrics
                record_model(metrics)

    async def decide(self,messages,*,toolset=None):
        turn=await self.session_turn(messages,toolset=toolset if toolset is not None else definitions())
        if turn['type']!='tool_call':
            raise AgentUnavailable('INVALID_AGENT_RESPONSE')
        return turn['call']
