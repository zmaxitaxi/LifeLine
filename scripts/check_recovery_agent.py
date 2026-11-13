"""Real local-model tool-selection smoke; no canned model or energy answers."""
import argparse
import asyncio
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from time import monotonic

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
from fastapi.testclient import TestClient
from app.main import create_app
from app.local_agent import LocalAgent
from app.agent_tools import SnapshotService
from app.forecast_models import ForecastLocation, SolarForecast
from app.weather_forecast import ForecastService


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--recorded-forecast',type=Path)
    args=parser.parse_args()
    if args.recorded_forecast:
        data=json.loads(args.recorded_forecast.read_text())
        forecast=SolarForecast.model_validate_json(json.dumps(data['forecast']))
        forecast=forecast.model_copy(update={'cache_status':'stale','warnings':forecast.warnings+[
            'EXPLICIT recorded forecast replay for local-model integration verification; not current live weather.']})
    else:
        forecast=asyncio.run(ForecastService().get(ForecastLocation(latitude=-.0917,longitude=34.768)))
    model=LocalAgent()
    original_decide=model.decide
    calls=[]
    async def recorded(messages):
        start=monotonic()
        call=await original_decide(messages)
        calls.append({'call':call,'seconds':monotonic()-start})
        return call
    model.decide=recorded
    # Illustrative operator-defined evening demand exposes an output bottleneck
    # for any forecast; exact calculated shortage is never predetermined.
    base={'latitude':-.0917,'longitude':34.768,'day':'tomorrow','use_configured_context':True,
        'input_basis':'synthetic_example','clinic':{'scenario':'normal','pv_capacity_kw':1.5,
        'battery_capacity_kwh':8.,'initial_battery_kwh':6.,'reserve_kwh':1.,'max_discharge_kw':.4,
        'equipment':[{'id':'evening','name':'Illustrative protected evening requirement','category':'critical',
                      'power_kw':1.,'required_hours':[19,20]},
                     {'id':'charging','name':'Optional device charging','category':'flexible','max_power_kw':.3,
                      'required_energy_kwh':.6,'allowed_hours':list(range(9,18)),
                      'baseline_allocations':[{'hour':16,'requested_kwh':.3},{'hour':17,'requested_kwh':.3}],'divisible':True}]}}
    questions=[
        ('We expect very little sunshine tomorrow. How can we keep our clinic running?',{'generate_recovery_plan','plan_forecast'}),
        ('Would another battery help?',{'generate_recovery_plan','explore_battery_capacity'}),
        ('What about more solar panels?',{'generate_recovery_plan'}),
        ('Can we move flexible equipment to the afternoon within its allowed hours?',{'generate_recovery_plan'}),
        ("What's the smallest modeled change that eliminates the shortage?",{'generate_recovery_plan'}),
        ('What about 50% less sunshine?',{'generate_recovery_plan','plan_forecast'}),
    ]
    evidence={'started_at':datetime.now(timezone.utc).isoformat(),'weather_mode':'recorded_forecast_replay' if args.recorded_forecast else 'live_forecast',
        'scope':'Integration smoke with real local inference and existing numerical tools; not a comprehensive model evaluation or clinic validation.',
        'forecast':forecast.model_dump(mode='json'),'inputs':base,'cases':[]}
    history=[]
    factor=1.
    with TestClient(create_app(forecast_service=SnapshotService(forecast),agent_service=model)) as client:
        evidence['status']=client.get('/api/agent/status').json()
        assert evidence['status']['available'],'Start Ollama with llama3.1:8b first.'
        for question,expected in questions:
            calls.clear()
            started=monotonic()
            response=client.post('/api/agent/ask',json=base|{'question':question,'previous_questions':history[-8:],'context_sunshine_factor':factor})
            result=response.json()
            selected={t['name'] for t in result.get('tool_calls',[]) if t['status']=='completed'}
            passed=(response.status_code==200 and result.get('mode')=='local_tool_agent' and
                not result.get('needs_clarification') and bool(selected&expected))
            entry={'question':question,'seconds':monotonic()-started,'native_model_calls':list(calls),'passed':passed,'http_status':response.status_code,'response':result}
            evidence['cases'].append(entry)
            history.append(question)
            factor=result.get('selected_sunshine_factor',factor)
            print(json.dumps({k:entry[k] for k in ('question','seconds','passed','http_status')}),flush=True)
    evidence['passed']=all(c['passed'] for c in evidence['cases'])
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(evidence,indent=2,allow_nan=False)+'\n')
    if not evidence['passed']:
        raise SystemExit('One or more real-model recovery integration cases failed; inspect evidence.')


if __name__=='__main__':main()
