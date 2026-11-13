"""Real llama3.1:8b native calls + one fresh Open-Meteo snapshot + real physics."""
import argparse
import asyncio
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import subprocess
from time import monotonic
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
from fastapi.testclient import TestClient
from app.main import create_app
from app.local_agent import LocalAgent
from app.agent_tools import SnapshotService
from app.forecast_models import ForecastLocation
from app.weather_forecast import ForecastService


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    forecast=asyncio.run(ForecastService().get(ForecastLocation(latitude=-.0917,longitude=34.768)))
    model=LocalAgent();original=model.decide;calls=[]
    async def recorded(messages,**kwargs):
        started=monotonic();call=await original(messages,**kwargs)
        calls.append({'call':call,'seconds':monotonic()-started});print(json.dumps({'native_call':call}),flush=True);return call
    model.decide=recorded
    body={'selected_clinic_id':'illustrative-reviewed-clinic','clinic_name':'Illustrative activity check',
        'location':forecast.requested_location.model_dump(),'planning_date':forecast.days[1].date.isoformat(),
        'timezone':forecast.timezone,'midnight_battery_kwh':2.,'clinic':{'scenario':'normal','battery_capacity_kwh':4.,
        'initial_battery_kwh':2.,'reserve_kwh':.5,'pv_capacity_kw':1.,'max_charge_kw':2.,'max_discharge_kw':2.,
        'equipment':[{'id':'fridge','name':'Vaccine refrigerator','category':'critical','power_kw':.1,'required_hours':list(range(24))}]}}
    evidence={'started_at':datetime.now(timezone.utc).isoformat(),
        'implementation_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        'backend_uncommitted_changes':subprocess.run(['git','diff','--quiet','HEAD','--','backend/app','scripts/check_activity_agent.py'],cwd=ROOT).returncode!=0,
        'scope':'Real native local inference with live Open-Meteo snapshot; illustrative operator-entered appliance, not a clinical assessment.',
        'forecast':forecast.model_dump(mode='json'),'inputs':body,'turns':[]}
    with TestClient(create_app(forecast_service=SnapshotService(forecast),agent_service=model)) as client:
        assert client.get('/api/agent/status').json()['available'],'Local llama3.1:8b is unavailable.'
        state=client.post('/api/planning/sessions',json=body).json();session=state['id'];base=f'/api/planning/sessions/{session}'
        for question in ('We have a vaccination campaign tomorrow.','It starts at 9 AM.','Actually, make that 10 AM.','It ends at 3 PM and uses the existing Vaccine refrigerator.','Confirm.'):
            calls.clear();started=monotonic()
            r=client.post(base+'/agent',json={'expected_revision':state['revision'],'question':question});data=r.json()
            state=data.get('state',state)
            entry={'question':question,'http_status':r.status_code,'seconds':monotonic()-started,'native_calls':list(calls),'response':data}
            evidence['turns'].append(entry)
            print(json.dumps({'question':question,'status':r.status_code,'tools':data.get('tool_calls'),'message':data.get('message')}),flush=True)
        ready=(len(state['proposals'])==1 and state['proposals'][0]['details']['start_hour']==10 and not state['proposals'][0]['missing_fields'] and not state['confirmed_activities'])
        if ready:
            proposal=state['active_proposal_id']
            confirmation={'expected_revision':state['revision'],'idempotency_key':'real-native-review-001'}
            r=client.post(base+f'/proposals/{proposal}/confirm',json=confirmation);state=r.json()
            evidence['confirmation']=state
            duplicate=client.post(base+f'/proposals/{proposal}/confirm',json=confirmation).json()
            evidence['idempotent']=duplicate==state
            calls.clear()
            r=client.post(base+'/agent',json={'expected_revision':state['revision'],'question':'What if tomorrow is cloudier, with 50% less sunshine? Include recovery options.'})
            data=r.json();state=data.get('state',state)
            evidence['weather_followup']={'native_calls':list(calls),'response':data}
            print(json.dumps({'question':'weather after confirmation','status':r.status_code,'tools':data.get('tool_calls'),'message':data.get('message')}),flush=True)
        evidence['passed']=bool(ready and evidence.get('idempotent') and len(state['confirmed_activities'])==1 and state['plan_status']=='current' and state['sunshine_factor']==.5 and
            state['computed_plan']['recovery'] and abs(state['computed_plan']['simulation']['optimized']['metrics']['critical_requested_kwh']-2.4)<1e-6)
        evidence['grounding_diagnostics']=client.app.state.planning.agent_diagnostics.get(session,[])
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(evidence,indent=2,allow_nan=False)+'\n')
    if not evidence['passed']:raise SystemExit('Real native activity check failed; inspect evidence.')

if __name__=='__main__':main()
