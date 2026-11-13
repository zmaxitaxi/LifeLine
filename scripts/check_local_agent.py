"""Opt-in real local-LLM + real forecast + real energy-model verification."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import time
import httpx


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--api-url',default='http://127.0.0.1:8000')
    parser.add_argument('--midnight-battery-kwh',type=float,required=True)
    parser.add_argument('--output',type=Path)
    parser.add_argument('--recorded-forecast',type=Path,help='Explicit offline verification only: replay a dated actual forecast from an evidence JSON. Never a runtime fallback.')
    args=parser.parse_args()
    cases=[
        ('We expect cloudy weather tomorrow. Will we have enough electricity?','plan_forecast'),
        ('We need to sterilize equipment before noon. Can we do that without compromising essential services?','clarification'),
        ('Run an additional 1 kW sterilizer for 2 hours from 08:00 before noon.','evaluate_fixed_requirement'),
        ('What happens if we receive 50% less sunlight?','plan_forecast'),
        ('How much additional battery capacity would we need to meet all our requirements?','explore_battery_capacity'),
    ]
    base={'latitude':-.0917,'longitude':34.768,'clinic':{'scenario':'scheduling'},'day':'tomorrow',
        'midnight_battery_kwh':args.midnight_battery_kwh,'inputs_confirmed':True,'input_basis':'synthetic_example'}
    evidence={'retrieved_at':datetime.now(timezone.utc).isoformat(),'inputs':base,'cases':[],
        'weather_mode':'recorded_forecast_replay' if args.recorded_forecast else 'live_forecast',
        'scope':'Real installed local model; illustrative clinic only. Small integration sample, not a general model-quality or clinical validation study.'}
    if args.recorded_forecast:
        import sys
        sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
        from fastapi.testclient import TestClient
        from app.forecast_models import SolarForecast
        from app.agent_tools import SnapshotService
        from app.main import create_app
        snapshot=SolarForecast.model_validate_json(json.dumps(json.loads(args.recorded_forecast.read_text())['forecast']))
        snapshot=snapshot.model_copy(update={'cache_status':'stale','warnings':snapshot.warnings+[
            'EXPLICIT RECORDED FORECAST REPLAY for integration verification only; not a current live forecast or runtime fallback. Original retrieval time retained.']})
        client_context=TestClient(create_app(forecast_service=SnapshotService(snapshot)))
    else:
        client_context=httpx.Client(timeout=90.)
    with client_context as client:
        status=client.get(args.api_url+'/api/agent/status');status.raise_for_status()
        assert status.json()['available'],'Start Ollama and install the configured local model first.'
        evidence['agent']=status.json()
        for question,expected in cases:
            started=time.monotonic()
            response=client.post(args.api_url+'/api/agent/ask',json=base|{'question':question});response.raise_for_status()
            result=response.json()
            assert result['mode']=='local_tool_agent',result['fallback_reason']
            if expected=='clarification':
                assert result['needs_clarification'] and result['result'] is None
            else:
                assert any(t['name']==expected and t['status']=='completed' for t in result['tool_calls'])
            case={'question':question,'seconds':round(time.monotonic()-started,3),'mode':result['mode'],
                'model':result['model'],'tool_calls':result['tool_calls'],'message':result['message'],
                'needs_clarification':result['needs_clarification']}
            if result['result']:
                plan=result['result'];base_plan=plan['plan']
                case.update(planning_date=plan['planning_date'],forecast_source=plan['forecast']['source'],
                    forecast_retrieved_at=plan['forecast']['retrieved_at'],timezone=plan['forecast']['timezone'],
                    metrics={k:base_plan[k]['metrics'] for k in ('baseline','heuristic','optimized')},
                    comparison=base_plan['comparison'],uncertainty=[{'factor':x['sunshine_factor'],'metrics':x['plan']['optimized']['metrics']} for x in plan['uncertainty_cases']])
                for comparison in [base_plan]+[x['plan'] for x in plan['uncertainty_cases']]:
                    c=comparison['effective_config']
                    for name in ('baseline','heuristic','optimized'):
                        for row in comparison[name]['hourly']:
                            assert abs(row['pv_kwh']+row['discharge_output_kwh']-row['critical_served_kwh']-row['flexible_served_kwh']-row['charge_input_kwh']-row['curtailed_kwh'])<1e-6
                            assert abs(row['soc_end_kwh']-row['soc_start_kwh']-row['charge_input_kwh']*c['charge_efficiency']+row['discharge_output_kwh']/c['discharge_efficiency'])<1e-6
                            assert 0<=row['soc_end_kwh']<=c['battery_capacity_kwh']+1e-6
                            assert min(row['charge_input_kwh'],row['discharge_output_kwh'])<1e-6
            if result['requirement']:
                case['requirement']={k:v for k,v in result['requirement'].items() if k not in ('original','proposed')}
            if result['capacity']:
                case['capacity']=result['capacity']
            evidence['cases'].append(case)
            print(json.dumps({'question':question,'seconds':case['seconds'],'mode':result['mode'],'message':result['message']}),flush=True)
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(evidence,indent=2,allow_nan=False)+'\n')


if __name__=='__main__':
    main()
