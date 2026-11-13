"""Opt-in live HTTP demonstration; never used as a runtime fallback or CI test."""
import argparse
import json
from pathlib import Path
import httpx


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--api-url',default='http://127.0.0.1:8000')
    parser.add_argument('--latitude',type=float,default=-.0917)
    parser.add_argument('--longitude',type=float,default=34.768)
    parser.add_argument('--midnight-battery-kwh',type=float,required=True)
    parser.add_argument('--scenario',default='scheduling',choices=['scheduling','normal','storm','high_demand'])
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    payload=dict(latitude=args.latitude,longitude=args.longitude,midnight_battery_kwh=args.midnight_battery_kwh,
                 clinic={'scenario':args.scenario},question='Can our clinic safely operate tomorrow given the weather forecast?')
    response=httpx.post(args.api_url+'/api/planner/ask',json=payload,timeout=45.)
    response.raise_for_status()
    value=response.json();result=value['result']
    assert result is not None
    expected=result['forecast']['days'][1]
    assert result['planning_date']==expected['date']
    plans=[(1.,result['plan'])]+[(c['sunshine_factor'],c['plan']) for c in result['uncertainty_cases']]
    for factor,plan in plans:
        config=plan['effective_config']
        assert config['initial_battery_kwh']==args.midnight_battery_kwh
        assert plan['equipment']==result['plan']['equipment']
        for name in ('baseline','heuristic','optimized'):
            rows=plan[name]['hourly'];assert len(rows)==24
            for weather,row in zip(expected['hours'],rows):
                pv=config['pv_capacity_kw']*plan['pv_performance_ratio']*weather['shortwave_radiation_w_m2']/1000*factor
                assert abs(row['pv_kwh']-pv)<1e-6
                assert abs(row['pv_kwh']+row['discharge_output_kwh']-row['critical_served_kwh']-row['flexible_served_kwh']-row['charge_input_kwh']-row['curtailed_kwh'])<1e-6
                assert 0 <= row['soc_end_kwh'] <= config['battery_capacity_kwh']+1e-6
                assert min(row['charge_input_kwh'],row['discharge_output_kwh'])<1e-6
                assert abs(row['soc_end_kwh']-row['soc_start_kwh']-row['charge_input_kwh']*config['charge_efficiency']+row['discharge_output_kwh']/config['discharge_efficiency'])<1e-6
    evidence=dict(mode=value['mode'],tool_calls=value['tool_calls'],forecast=result['forecast'],
                  planning_date=result['planning_date'],midnight_battery_kwh=args.midnight_battery_kwh,
                  inputs=payload['clinic'],cases=[dict(sunshine_factor=f,status=p['status'],
                    effective_config=p['effective_config'],metrics={k:p[k]['metrics'] for k in ('baseline','heuristic','optimized')},
                    comparison=p['comparison']) for f,p in plans],
                  checks='Hourly conversion, conservation, state transition, battery bounds, mutually exclusive battery flows, and identical equipment checked against real HTTP results. This is not field validation.')
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(evidence,indent=2,allow_nan=False)+'\n')
    print(json.dumps(dict(source=result['forecast']['source'],retrieved_at=result['forecast']['retrieved_at'],
        timezone=result['forecast']['timezone'],planning_date=result['planning_date'],mode=value['mode'],
        cases=[dict(factor=f,solar_kwh=p['optimized']['metrics']['total_solar_kwh'],critical_unserved_kwh=p['optimized']['metrics']['critical_unserved_kwh'],
            minimum_battery_kwh=p['optimized']['metrics']['min_soc_kwh'],flexible_deferred_kwh=p['optimized']['metrics']['flexible_deferred_kwh']) for f,p in plans]),indent=2))


if __name__=='__main__':
    main()
