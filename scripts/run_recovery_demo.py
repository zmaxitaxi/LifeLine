"""Recalculate the input-only reliability demonstration through the public API."""
import argparse
import json
from pathlib import Path
import httpx


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--api-url',default='http://127.0.0.1:8000')
    parser.add_argument('--live',action='store_true',help='Replace historical weather with actual forecast radiation; results will vary.')
    parser.add_argument('--sunshine-factor',type=float,default=1.)
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    with httpx.Client(base_url=args.api_url,timeout=90.) as client:
        response=client.get('/api/demos/recovery');response.raise_for_status()
        demo=response.json()
        body=demo['request']|{'sunshine_factor':args.sunshine_factor}
        if args.live:
            body['weather_mode']='live_forecast'
        response=client.post('/api/recovery/plan',json=body);response.raise_for_status()
        result=response.json()
    print(demo['name'])
    print(f"{result['weather_mode']} | {result['planning_date']} | {result['timezone']}")
    if result['forecast']:
        print(f"Open-Meteo retrieved {result['forecast']['retrieved_at']} ({result['forecast']['cache_status']})")
    print('Option | Essential unserved kWh | Min battery kWh | Original flexible unfinished kWh')
    for option in [result['existing']]+result['options']:
        m=option['metrics']
        print(f"{option['id']} | {m['essential_unserved_kwh']:.3f} | {m['minimum_battery_kwh']:.3f} | {m['flexible_unfinished_kwh']:.3f}")
    print(result['summary'])
    print(result['next_action'])
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps({'request':body,'recovery':result},indent=2,allow_nan=False)+'\n')


if __name__=='__main__':main()
