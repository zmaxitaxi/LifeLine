"""Sequential real-Llama pipeline benchmark; synthetic demo weather, real physics.

Instrumentation lives outside application behavior so the same runner measures
unmodified baseline and optimized implementations. No requests target the UI.
"""
import argparse
import asyncio
from contextlib import ExitStack
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import subprocess
import sys
from time import monotonic
from unittest.mock import patch
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
import httpx
from fastapi.testclient import TestClient
from app.main import create_app
from app.local_agent import LocalAgent
from app.claude_agent import ClaudeAgent
from app.agent_provider import load_local_settings
from app.demo_weather import DemoWeatherService
import app.planning_state as planning_state
import app.recovery_planner as recovery_planner
import app.comparison as comparison
import app.planning_routes as planning_routes
import fastapi.routing


class Instrumentation:
    def __init__(self): self.events=[]
    def add(self,phase,seconds,**extra): self.events.append(dict(phase=phase,seconds=seconds,**extra))
    def sync(self,phase,function):
        def measured(*args,**kwargs):
            started=monotonic()
            try:return function(*args,**kwargs)
            finally:self.add(phase,monotonic()-started)
        return measured
    def asynchronous(self,phase,function):
        async def measured(*args,**kwargs):
            started=monotonic()
            try:return await function(*args,**kwargs)
            finally:self.add(phase,monotonic()-started)
        return measured


class OllamaTransport(httpx.AsyncBaseTransport):
    def __init__(self,metrics): self.metrics=metrics;self.calls=[]
    async def handle_async_request(self,request):
        started=monotonic()
        try:
            async with httpx.AsyncClient(trust_env=False,timeout=httpx.Timeout(45.,connect=2.)) as client:
                response=await client.request(request.method,str(request.url),content=request.content,headers=request.headers)
        except BaseException as exc:
            if request.url.path=='/api/chat':
                elapsed=monotonic()-started
                self.calls.append({'seconds':elapsed,'error':type(exc).__name__,'request_bytes':len(request.content)})
                self.metrics.add('model_http',elapsed)
            raise
        elapsed=monotonic()-started
        if request.url.path=='/api/chat':
            body=json.loads(request.content);data=response.json()
            native=data.get('message',{})
            call={'seconds':elapsed,'request_bytes':len(request.content),
                'message_chars':sum(len(json.dumps(m,separators=(',',':'))) for m in body['messages']),
                'tool_schema_chars':len(json.dumps(body.get('tools',[]),separators=(',',':'))),
                'options':body['options'],'native_message':native,
                'prior_rejections':[m['content'] for m in body['messages'] if m['role']=='user' and m['content'].startswith('That attempt was rejected:')],
                'ollama':{key:data.get(key) for key in ('total_duration','load_duration','prompt_eval_count','prompt_eval_duration','eval_count','eval_duration','done_reason')}}
            self.calls.append(call);self.metrics.add('model_http',elapsed)
        else:self.metrics.add('model_status_http',elapsed)
        return httpx.Response(response.status_code,headers={k:v for k,v in response.headers.items() if k.lower() not in ('content-encoding','content-length','transfer-encoding')},content=response.content,request=request)


class ClaudeTransport(httpx.AsyncBaseTransport):
    def __init__(self,metrics): self.metrics=metrics;self.calls=[]
    async def handle_async_request(self,request):
        started=monotonic()
        try:
            async with httpx.AsyncClient(trust_env=False,timeout=httpx.Timeout(35.,connect=5.)) as client:
                response=await client.request(request.method,str(request.url),content=request.content,headers=request.headers)
        except BaseException as exc:
            if request.url.path=='/v1/messages':
                elapsed=monotonic()-started
                self.calls.append({'seconds':elapsed,'error':type(exc).__name__})
                self.metrics.add('model_http',elapsed)
            raise
        elapsed=monotonic()-started
        if request.url.path=='/v1/messages':
            body=json.loads(request.content);data=response.json()
            # Never record headers, keys or private thinking blocks.
            public=[b for b in data.get('content',[]) if b.get('type') in ('text','tool_use')]
            self.calls.append({'seconds':elapsed,'request_bytes':len(request.content),
                'message_chars':len(json.dumps(body['messages'])),
                'tool_schema_chars':len(json.dumps(body.get('tools',[]))),
                'native_message':public,'usage':data.get('usage'),
                'correction':[b.get('text') for m in body['messages'] for b in m.get('content',[]) if b.get('type')=='text' and b.get('text','').startswith('That attempt was rejected:')],
                'stop_reason':data.get('stop_reason'),'http_status':response.status_code})
            self.metrics.add('model_http',elapsed)
        else:self.metrics.add('model_status_http',elapsed)
        return httpx.Response(response.status_code,headers={k:v for k,v in response.headers.items() if k.lower() not in ('content-encoding','content-length','transfer-encoding')},content=response.content,request=request)


def clinic_body():
    return {'selected_clinic_id':'pipeline-benchmark','clinic_name':'Illustrative benchmark clinic',
        'location':{'latitude':-.0917,'longitude':34.768},'timezone':'Africa/Nairobi',
        'planning_date':(datetime.now(ZoneInfo('Africa/Nairobi')).date()+timedelta(days=1)).isoformat(),
        'midnight_battery_kwh':6.,'clinic':{'scenario':'normal','battery_capacity_kwh':8.,'initial_battery_kwh':6.,
        'reserve_kwh':1.,'pv_capacity_kw':1.5,'max_discharge_kw':.4,
        'equipment':[{'id':'evening','name':'Illustrative essential evening equipment','category':'critical','power_kw':1.,'required_hours':[19,20]}]}}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--cases',default='conversation,assessment,vaccination,recovery,followup,history')
    parser.add_argument('--provider',choices=('local','claude'),default='local')
    args=parser.parse_args();metrics=Instrumentation()
    load_local_settings()
    transport=ClaudeTransport(metrics) if args.provider=='claude' else OllamaTransport(metrics)
    agent=ClaudeAgent(transport=transport) if args.provider=='claude' else LocalAgent(transport=transport)
    weather=DemoWeatherService()
    weather.get=metrics.asynchronous('weather',weather.get)
    report={'implementation_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        'started_at':datetime.now(timezone.utc).isoformat(),'model':agent.model,'provider':args.provider,
        'basis':'SYNTHETIC DEMO WEATHER; actual selected AI provider; existing real simulator/MILP. Illustrative explicit fixture, no UI requests.',
        'first_visible_basis':'Current session endpoint is not streaming; first visible assistant content equals completed HTTP response time.',
        'cases':[]}
    def save():args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(report,indent=2)+'\n')
    with ExitStack() as stack:
        stack.enter_context(patch.object(planning_state,'forecast_case',metrics.sync('forecast_case_including_milp',planning_state.forecast_case)))
        stack.enter_context(patch.object(recovery_planner,'forecast_case',metrics.sync('recovery_forecast_case_including_milp',recovery_planner.forecast_case)))
        stack.enter_context(patch.object(comparison,'optimize',metrics.sync('milp',comparison.optimize)))
        stack.enter_context(patch.object(fastapi.routing,'serialize_response',metrics.asynchronous('response_serialization',fastapi.routing.serialize_response)))
        stack.enter_context(patch.object(planning_routes,'ask_session_agent',metrics.asynchronous('agent_total',planning_routes.ask_session_agent)))
        stack.enter_context(patch.object(planning_state.PlanningStore,'record_turn',metrics.asynchronous('conversation_persistence',planning_state.PlanningStore.record_turn)))
        with TestClient(create_app(forecast_service=weather,agent_service=agent)) as client:
            for name in args.cases.split(','):
                response=client.post('/api/planning/sessions',json=clinic_body());response.raise_for_status();state=response.json()
                if name=='followup':
                    state=client.post(f"/api/planning/sessions/{state['id']}/recompute",json={'expected_revision':state['revision'],'include_recovery':True}).json()
                    plan=state['computed_plan'];option=max((o for o in plan['recovery']['options'] if o['kind']=='output'),key=lambda o:o['config']['max_discharge_kw'])
                    state=client.post(f"/api/planning/sessions/{state['id']}/recovery-selection",json={'expected_revision':state['revision'],'input_revision':state['input_revision'],'generation':plan['generation'],'option_id':option['id']}).json()
                if name=='history':
                    # Explicit benchmark history fixture, not asserted to be real prior inference.
                    from app.planning_models import SessionAgentResponse
                    for q,a in [('What does this app do?','We can discuss clinic activities and evaluate modeled electricity requirements.'),
                        ('Does an event automatically use electricity?','An activity alone does not add electrical demand.'),
                        ('Our existing equipment is already configured.','The configured equipment remains the current source of device facts.'),
                        ('I am considering a vaccination campaign.','What day and local operating window are you considering?')]:
                        asyncio.run(client.app.state.planning.record_turn(state['id'],q,SessionAgentResponse(needs_clarification=False,message=a,state=client.app.state.planning.read(state['id']),mode='local_tool_agent',model=agent.model)))
                question={'conversation':'Hello',
                    'assessment':'Can our clinic safely operate tomorrow given the weather forecast?',
                    'vaccination':'What if I wanted to plan a vaccination clinic today at 10 AM?',
                    'recovery':'What changes could resolve our modeled essential electricity shortfall? Please compare tested recovery alternatives.',
                    'followup':'Please explain my exact selected plan against the existing baseline without recalculating or refreshing weather.',
                    'history':'Actually, I mean tomorrow at 10 AM. What else do you need to plan that vaccination campaign?'}[name]
                metrics.events.clear();transport.calls.clear();before=deepcopy(state);started=monotonic()
                response=client.post(f"/api/planning/sessions/{state['id']}/agent",json={'expected_revision':state['revision'],'question':question})
                total=monotonic()-started;data=response.json();current=data.get('state',before)
                text=data.get('message','');success=response.status_code==200 and data.get('mode') in ('local_tool_agent','cloud_tool_agent')
                if name=='conversation':correct=success and current==before and not data.get('tool_calls')
                elif name=='assessment':correct=success and current['plan_status']=='current' and 'recompute_clinic_plan' in data.get('tool_calls',[])
                elif name=='vaccination':correct=success and current==before and (('today' in text.lower() and 'tomorrow' in text.lower()) or (datetime.now(ZoneInfo('Africa/Nairobi')).date().isoformat() in text and before['planning_date'] in text)) and 'power rating' not in text.lower()
                elif name=='recovery':correct=success and current.get('computed_plan') is not None and current['computed_plan'].get('recovery') is not None
                elif name=='followup':correct=success and current==before and 'recompute_clinic_plan' not in data.get('tool_calls',[])
                else:correct=success and any(word in text.lower() for word in ('end','finish','duration','how long','window')) and any(word in text.lower() for word in ('equipment','device','appliance')) and 'power rating' not in text.lower() and 'midnight' not in text.lower()
                phases={phase:sum(e['seconds'] for e in metrics.events if e['phase']==phase) for phase in {e['phase'] for e in metrics.events}}
                item={'name':name,'question':question,'total_seconds':total,'first_visible_seconds':total,
                    'model_calls':deepcopy(transport.calls),'phases_seconds':phases,'events':deepcopy(metrics.events),
                    'http_status':response.status_code,'correctness_check':correct,'response':{k:v for k,v in data.items() if k!='state'},
                    'state_summary':{'revision_before':before['revision'],'revision_after':current['revision'],'plan_status':current['plan_status'],'plan_error':current.get('plan_error'),'proposal_count':len(current['proposals'])}}
                report['cases'].append(item);save()
                print(json.dumps({'case':name,'seconds':total,'calls':len(transport.calls),'correct':correct,'message':text}),flush=True)
    report['completed_at']=datetime.now(timezone.utc).isoformat();save()

if __name__=='__main__':main()
