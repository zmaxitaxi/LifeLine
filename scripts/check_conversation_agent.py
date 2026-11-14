"""Real unforced local model journeys; actual weather/model work only when chosen."""
import argparse
from copy import deepcopy
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


def fixture_body(identity='conversation'):
    return {'selected_clinic_id':'illustrative-'+identity,'clinic_name':'Illustrative native verification',
        'location':{'latitude':-.0917,'longitude':34.768},'timezone':'Africa/Nairobi',
        'planning_date':(datetime.now(ZoneInfo('Africa/Nairobi')).date()+timedelta(days=1)).isoformat(),
        'midnight_battery_kwh':6.,'clinic':{'scenario':'normal','battery_capacity_kwh':8.,'initial_battery_kwh':6.,
        'reserve_kwh':1.,'pv_capacity_kw':1.5,'max_discharge_kw':.4,
        'equipment':[{'id':'evening','name':'Illustrative essential evening equipment','category':'critical','power_kw':1.,'required_hours':[19,20]}]}}


def summary(state):
    result={key:deepcopy(value) for key,value in state.items() if key not in ('computed_plan','forecast_reference')}
    if state.get('forecast_reference'):
        result['forecast_reference']=state['forecast_reference']
    if state.get('computed_plan'):
        plan=state['computed_plan'];simulation=plan['simulation']
        result['computed_plan']={key:plan[key] for key in ('input_revision','generation','sunshine_factor','computed_at')}
        result['computed_plan']['simulation']={key:simulation[key] for key in ('effective_config','equipment','comparison','status','input_provenance')}
        result['computed_plan']['simulation']['metrics']={name:simulation[name]['metrics'] for name in ('baseline','heuristic','optimized')}
        if plan.get('recovery'):
            recovery=plan['recovery']
            result['computed_plan']['recovery']={'recommended_option_id':recovery['recommended_option_id'],
                'options':[{key:option[key] for key in ('id','kind','label','config','metrics','infrastructure_changes','work_changes')} for option in recovery['options']]}
    return result


def authored(data,native):
    return any((turn['turn']['type']=='message' and turn['turn']['content']==data.get('message')) or
        (turn['turn']['type']=='tool_call' and turn['turn']['call']['name']=='respond_to_user' and
         turn['turn']['call']['arguments'].get('message')==data.get('message')) for turn in native)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--sections',default='conversation,energy,activity');parser.add_argument('--weather',choices=['live','synthetic-demo'],default='live');args=parser.parse_args()
    sections=set(args.sections.split(','));model=LocalAgent();weather=CountedWeather();native=[];session_turn=model.session_turn
    if args.weather=='synthetic-demo':
        from app.demo_weather import DemoWeatherService
        weather.service=DemoWeatherService()
    async def recorded(messages,**kwargs):
        started=monotonic();turn=await session_turn(messages,**kwargs)
        native.append({'turn':turn,'seconds':monotonic()-started,'offered_tools':[tool['name'] for tool in kwargs['toolset']],
            'prior_rejections':[message['content'] for message in messages if message['role']=='user' and message['content'].startswith('That attempt was rejected:')][-2:]})
        print(json.dumps({'native':turn}),flush=True);return turn
    model.session_turn=recorded
    evidence={'started_at':datetime.now(timezone.utc).isoformat(),'implementation_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        'backend_uncommitted_changes':subprocess.run(['git','diff','--quiet','HEAD','--','backend/app','scripts/check_conversation_agent.py'],cwd=ROOT).returncode!=0,
        'scope':('SYNTHETIC DEMO WEATHER; actual local Llama native choices and real existing physics. Not live forecast validation.' if args.weather=='synthetic-demo' else 'Genuine local native content/tool choices. Weather is actual Open-Meteo; all numerical state comes from the existing model. Compact snapshots retain computed metrics, tested alternatives and forecast provenance.'),'turns':[]}
    with TestClient(create_app(forecast_service=weather,agent_service=model)) as client:
        assert client.get('/api/agent/status').json()['available']
        def create(identity,body=None):
            response=client.post('/api/planning/sessions',json=body or fixture_body(identity));assert response.status_code==200,response.text
            return response.json()
        def ask(state,question,check):
            before=deepcopy(state);count=weather.calls;native.clear();started=monotonic()
            response=client.post(f"/api/planning/sessions/{state['id']}/agent",json={'expected_revision':state['revision'],'question':question})
            data=response.json();current=data.get('state',state)
            if response.status_code!=200:
                latest=client.get(f"/api/planning/sessions/{state['id']}")
                if latest.status_code==200: current=latest.json()
            good=response.status_code==200 and data.get('mode')=='local_tool_agent' and authored(data,native) and (len(question)<=20 or data.get('message','').strip().casefold()!=question.strip().casefold())
            try: good=bool(good and check(current,before,data,weather.calls-count))
            except (KeyError,TypeError,IndexError): good=False
            entry={'question':question,'seconds':monotonic()-started,'weather_calls':weather.calls-count,
                'http_status':response.status_code,'native_turns':deepcopy(native),'passed':good,
                'response':{key:value for key,value in data.items() if key!='state'},'state':summary(current)}
            evidence['turns'].append(entry)
            print(json.dumps({key:entry[key] for key in ('question','seconds','weather_calls','passed')}),flush=True)
            return current
        no_change=lambda current,before,data,calls:current==before and calls==0 and data['presentation']['kind']=='conversation' and not data['presentation']['option_ids'] and not data['presentation']['show_schedule']
        if 'conversation' in sections or 'primary' in sections:
            state=create('conversation')
            for question in ('Hello, how are things?','What can you help me do here?',
                'Could more battery storage help? I am just discussing an unevaluated idea, not asking for a calculation yet.') if 'conversation' in sections else ():
                state=ask(state,question,no_change)
            state=ask(state,'Can our clinic safely operate tomorrow given the weather forecast? Please compare only relevant modeled alternatives.',
                lambda current,before,data,calls:current['plan_status']=='current' and bool(current['computed_plan'].get('recovery')) and calls>=1 and len(data['presentation']['option_ids'])<len(current['computed_plan']['recovery']['options']))
            if state.get('computed_plan') and state['computed_plan'].get('recovery') and ('conversation' in sections or 'selected' in sections):
                option=max((o for o in state['computed_plan']['recovery']['options'] if o['kind']=='output'),key=lambda item:item['config']['max_discharge_kw'])
                response=client.post(f"/api/planning/sessions/{state['id']}/recovery-selection",json={'expected_revision':state['revision'],
                    'input_revision':state['input_revision'],'generation':state['computed_plan']['generation'],'option_id':option['id']})
                assert response.status_code==200,response.text;state=response.json()
                state=ask(state,'Please explain my exact selected plan against the existing baseline without recalculating or refreshing weather.',
                    lambda current,before,data,calls:current==before and calls==0 and 'recompute_clinic_plan' not in data['tool_calls'] and current['selected_recovery_intervention_id']==option['id'] and f"{option['config']['max_discharge_kw']:g} kW" in data['message'])
        if 'energy' in sections:
            state=create('energy')
            state=ask(state,'For review, set our battery capacity to 12 kWh. The current reading is 20%, and for tomorrow assume a 50% starting charge at midnight. Do not apply the draft yet.',
                lambda current,before,data,calls:calls==0 and current['energy_settings']==before['energy_settings'] and len(current['energy_proposals'])==1 and current['energy_proposals'][0]['proposed_energy_settings']['battery_capacity_kwh']==12. and current['energy_proposals'][0]['proposed_energy_settings']['initial_battery_kwh']==6. and abs(current['energy_proposals'][0]['current_battery_reading']['energy_kwh']-2.4)<1e-8)
            active=state['active_energy_proposal_id']
            state=ask(state,'Actually use a 40% starting battery charge in that same draft. Leave the current reading alone.',
                lambda current,before,data,calls:calls==0 and current['active_energy_proposal_id']==active and len(current['energy_proposals'])==1 and current['energy_settings']==before['energy_settings'] and abs(current['energy_proposals'][0]['proposed_energy_settings']['initial_battery_kwh']-4.8)<1e-8 and current['energy_proposals'][0]['current_battery_reading']==before['energy_proposals'][0]['current_battery_reading'])
        if 'activity' in sections:
            body=fixture_body('activity');body['clinic']['equipment']=[{'id':'fridge','name':'Vaccine refrigerator','category':'critical','power_kw':.1,'required_hours':list(range(24))},
                {'id':'pump','name':'Water pump','category':'flexible','max_power_kw':.5,'required_energy_kwh':1.,'allowed_hours':list(range(8,17)),
                 'baseline_allocations':[{'hour':8,'requested_kwh':.5},{'hour':9,'requested_kwh':.5}],'divisible':True}]
            state=create('activity',body)
            state=ask(state,'Please stage a vaccination campaign for tomorrow from 9 AM to 3 PM. It only uses the existing fridge and needs no additional equipment.',
                lambda current,before,data,calls:calls==0 and len(current['proposals'])==1 and current['proposals'][0]['details']['start_hour']==9 and current['proposals'][0]['details']['end_hour']==15 and current['proposals'][0]['details']['equipment_ids']==['fridge'] and not current['proposals'][0]['missing_fields'] and not current['confirmed_activities'])
            active=state['active_proposal_id']
            state=ask(state,'Actually make that activity start at 10 AM in the same draft.',
                lambda current,before,data,calls:calls==0 and current['active_proposal_id']==active and len(current['proposals'])==1 and current['proposals'][0]['details']['start_hour']==10)
            if active and not state['proposals'][0]['missing_fields']:
                request={'expected_revision':state['revision'],'idempotency_key':'native-journey-operator-confirm'}
                response=client.post(f"/api/planning/sessions/{state['id']}/proposals/{active}/confirm",json=request)
                assert response.status_code==200,response.text;state=response.json()
                repeated=client.post(f"/api/planning/sessions/{state['id']}/proposals/{active}/confirm",json=request).json()
                evidence['idempotent_confirmation']=state==repeated and len(state['confirmed_activities'])==1
                demand=state['computed_plan']['simulation']['optimized']['metrics']['critical_requested_kwh'] if state.get('computed_plan') else None
                state=ask(state,'What if forecast sunshine is 50% lower? Calculate with the confirmed campaign included and show the relevant comparison.',
                    lambda current,before,data,calls:current['plan_status']=='current' and current['sunshine_factor']==.5 and len(current['confirmed_activities'])==1 and current['computed_plan']['simulation']['optimized']['metrics']['critical_requested_kwh']==demand and len(current['computed_plan']['simulation']['equipment'])==2)
                aid=state['confirmed_activities'][0]['id']
                reviewed=client.post(f"/api/planning/sessions/{state['id']}/proposals",json={'expected_revision':state['revision'],
                    'target_activity_id':aid,'details':{'equipment_ids':['fridge','pump'],'equipment_constraints':[{'equipment_id':'pump','required_duration_hours':3}]}})
                assert reviewed.status_code==200,reviewed.text;state=reviewed.json()
                pid=state['active_proposal_id']
                reviewed=client.post(f"/api/planning/sessions/{state['id']}/proposals/{pid}/confirm",json={'expected_revision':state['revision'],'idempotency_key':'manual-runtime-review'})
                assert reviewed.status_code==200,reviewed.text;state=reviewed.json()
                evidence['manual_runtime_review']=summary(state)
                state=ask(state,'How long must the Water pump run now? Please answer from the confirmed requirement, without recalculating.',
                    lambda current,before,data,calls:current==before and calls==0 and 'recompute_clinic_plan' not in data['tool_calls'] and any(word in data['message'].lower() for word in ('3 hours','three hours')))
        evidence['passed']=all(item['passed'] for item in evidence['turns']) and evidence.get('idempotent_confirmation',True)
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(evidence,indent=2)+'\n')
    if not evidence['passed']:raise SystemExit('A genuine native journey failed; inspect the recorded state and model turns.')

if __name__=='__main__':main()
