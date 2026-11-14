"""Genuine native local conversation and source-grounded operational synthesis."""
import argparse
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import subprocess
import sys
from time import monotonic
from zoneinfo import ZoneInfo
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
from fastapi.testclient import TestClient
from app.main import create_app
from app.local_agent import LocalAgent
from app.weather_forecast import ForecastService


class CountedWeather:
    def __init__(self):
        self.service=ForecastService();self.calls=0
    async def get(self,location):
        self.calls+=1
        return await self.service.get(location)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    model=LocalAgent();weather=CountedWeather();native=[];decide=model.decide
    async def recorded(messages,**kwargs):
        started=monotonic();call=await decide(messages,**kwargs)
        native.append({'call':call,'seconds':monotonic()-started});print(json.dumps({'native':call}),flush=True);return call
    model.decide=recorded
    body={'selected_clinic_id':'illustrative-conversation-check','clinic_name':'Illustrative local verification',
        'location':{'latitude':-.0917,'longitude':34.768},'timezone':'Africa/Nairobi',
        'planning_date':(datetime.now(ZoneInfo('Africa/Nairobi')).date()+timedelta(days=1)).isoformat(),
        'midnight_battery_kwh':6.,'clinic':{'scenario':'normal','battery_capacity_kwh':8.,'initial_battery_kwh':6.,
        'reserve_kwh':1.,'pv_capacity_kw':1.5,'max_discharge_kw':.4,
        'equipment':[{'id':'evening','name':'Illustrative essential evening equipment','category':'critical','power_kw':1.,'required_hours':[19,20]}]}}
    evidence={'started_at':datetime.now(timezone.utc).isoformat(),'implementation_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        'backend_uncommitted_changes':subprocess.run(['git','diff','--quiet','HEAD','--','backend/app','scripts/check_conversation_agent.py'],cwd=ROOT).returncode!=0,
        'scope':'Real local inference. Social turns require no weather or state mutation. Operational turn fetches live Open-Meteo and invokes the real simulator/recovery planner before local-model synthesis.', 'turns':[]}
    with TestClient(create_app(forecast_service=weather,agent_service=model)) as client:
        assert client.get('/api/agent/status').json()['available']
        state=client.post('/api/planning/sessions',json=body).json();base=f"/api/planning/sessions/{state['id']}"
        for question in ('Hello','Hello, how are you?','Thanks','What can you help me with?','Can you tell me what this app does?','Will we have enough electricity tomorrow? Please compare several recovery options.'):
            native.clear();before=state;count=weather.calls;started=monotonic()
            r=client.post(base+'/agent',json={'expected_revision':state['revision'],'question':question});data=r.json();state=data.get('state',state)
            social=question in ('Hello','Hello, how are you?','Thanks','What can you help me with?','Can you tell me what this app does?')
            passed=(r.status_code==200 and data.get('mode')=='local_tool_agent' and
                (state==before and weather.calls==count and data.get('tool_calls')==['conversational_reply'] if social else
                 state.get('plan_status')=='current' and state['computed_plan'].get('recovery') and
                 any(call['call']['name']=='compose_planning_reply' and call['call']['arguments'].get('message')==data.get('message') and
                     len({key for key in call['call']['arguments'].get('fact_references',[]) if key.startswith('option_')})>=3 for call in native)))
            entry={'question':question,'seconds':monotonic()-started,'weather_calls':weather.calls-count,'native_calls':list(native),'passed':bool(passed),'response':data}
            evidence['turns'].append(entry)
            print(json.dumps({key:entry[key] for key in ('question','seconds','weather_calls','passed')}),flush=True)
        if state.get('computed_plan',{}).get('recovery'):
            recovery=state['computed_plan']['recovery']
            outputs=[option for option in recovery['options'] if option['kind']=='output']
            selected=max(outputs,key=lambda option:option['config']['max_discharge_kw'])
            selection=client.post(base+'/recovery-selection',json={'expected_revision':state['revision'],
                'input_revision':state['input_revision'],'generation':state['computed_plan']['generation'],'option_id':selected['id']})
            assert selection.status_code==200,selection.text
            state=selection.json();before=state;count=weather.calls;native.clear();started=monotonic()
            question='Explain the exact selected plan against the existing baseline without recalculating.'
            r=client.post(base+'/agent',json={'expected_revision':state['revision'],'question':question});data=r.json();state=data.get('state',state)
            passed=(r.status_code==200 and data.get('mode')=='local_tool_agent' and state==before and weather.calls==count and
                data.get('tool_calls')==['explain_current_plan'] and f"{selected['config']['max_discharge_kw']:g} kW" in data.get('message','') and
                any(call['call']['name']=='compose_planning_reply' and call['call']['arguments'].get('message')==data.get('message') for call in native))
            entry={'question':question,'seconds':monotonic()-started,'weather_calls':weather.calls-count,'native_calls':list(native),
                'selected_option_id':selected['id'],'passed':bool(passed),'response':data}
            evidence['turns'].append(entry)
            print(json.dumps({key:entry[key] for key in ('question','seconds','weather_calls','selected_option_id','passed')}),flush=True)
        evidence['passed']=all(turn['passed'] for turn in evidence['turns'])
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(evidence,indent=2)+'\n')
    if not evidence['passed']:raise SystemExit('Native conversation verification failed; inspect evidence.')

if __name__=='__main__':main()
