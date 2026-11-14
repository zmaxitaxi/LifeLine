"""Test-only model/weather transports; production imports none of this module.
The real session API, compiler, simulator, optimizer and validators remain active.
"""
import json
import asyncio
import os
import re
from pathlib import Path
from datetime import datetime
import sys
ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / 'backend'), str(ROOT / 'backend/tests')]
import httpx
from app.main import create_app
from app.local_agent import LocalAgent
from app.weather_forecast import ForecastError
from test_weather_forecast import service_for, NOW
from test_weather_outlook import service_for as outlook_for
from app import planning_agent

class FixtureDateTime(datetime):
    @classmethod
    def now(cls, tz=None):
        return NOW.astimezone(tz) if tz else NOW.replace(tzinfo=None)
planning_agent.datetime = FixtureDateTime
weather, _ = service_for()
outlook, _ = outlook_for()
def failed():
    flag = os.environ.get('LIFELINE_TEST_WEATHER_FAILURE_FILE')
    return bool(flag and Path(flag).exists())
class TestWeather:
    async def get(self, location):
        if failed(): raise ForecastError('FORECAST_UNAVAILABLE', 'Injected browser-test weather outage')
        return await weather.get(location)
class TestOutlook:
    async def get(self, location):
        if failed(): raise ForecastError('FORECAST_UNAVAILABLE', 'Injected browser-test weather outage')
        return await outlook.get(location)

def wire(name, arguments):
    return httpx.Response(200, json={'message':{'role':'assistant','content':'UNVERIFIED RAW MODEL TEXT', 'tool_calls':[{'function':{'name':name,'arguments':arguments}}]}})

def authored(message):
    return httpx.Response(200,json={'message':{'role':'assistant','content':message}})


def natural_session(payload):
    """Synthetic native choices; every state change and numerical fact stays real."""
    messages=payload['messages']
    question=next(m['content'] for m in reversed(messages) if m.get('role')=='user' and not m['content'].startswith(('Canonical clinic data:','That attempt was rejected:')))
    context=json.loads(next(m['content'].split('Canonical clinic data: ',1)[1] for m in messages if m.get('content','').startswith('Canonical clinic data: ')))
    result=next(((m.get('tool_name'),json.loads(m['content'])) for m in reversed(messages) if m.get('role')=='tool' and '"facts"' in m.get('content','')),None)
    if result and messages[-1]['role']=='tool':
        action,data=result;facts=data['facts'];ids=[];refs=[];schedule=False;kind='conversation'
        if action=='inspect_planning_state' and question.lower() in ('what are the confirmed activities?','which activities are confirmed?'):
            names=[a['details']['name'] for a in context.get('confirmed_activities',[])];message='The confirmed activities are '+', '.join(names)+'.' if names else 'There are no confirmed activities yet.'
        elif data.get('active_energy_proposal') and action in ('propose_energy_settings','update_energy_settings_draft'):
            message='The power settings are ready for review. They stay proposed until you explicitly confirm.';kind='energy_review'
        elif data.get('active_draft') and action not in ('recompute_clinic_plan','explain_current_plan'):
            draft=data['active_draft'];kind='activity_review';message='Your activity remains a draft. '+(facts.get('missing_detail','Please review and confirm its requirements.'))
        elif data['plan_status']=='current':
            kind='explanation' if action=='explain_current_plan' else 'calculation';refs=['essential_summary','scope']
            base=facts['essential_summary'];message=f"Here is my review for clinic staff. The existing baseline leaves {base['remaining_unserved_essential_energy']} of essential energy unserved in the model."
            if 'selected_option' in facts:
                option=facts['selected_option'];ids=[option['exact_selected_option_id']];refs.append('selected_option')
                message+=f" The selected {option['kind']} comparison leaves {option['remaining_unserved_essential_energy']} unserved."
                for change in option['hypothetical_changes']:message+=f" The selected hypothetical change is {change['before']} to {change['after']}."
            else:
                options=[(key,value) for key,value in facts.items() if key.startswith('option_') and '_case_' not in key and isinstance(value,dict)]
                chosen=options[:3] if 'compare' in question.lower() else options[:1]
                for key,option in chosen:
                    refs.append(key);ids.append(option['option_id']);message+=f" The {option['kind']} comparison leaves {option['remaining_unserved_essential_energy']} of essential energy unserved."
                schedule=not ('compare' in question.lower())
            if 'unconfirmed_notice' in facts:refs.append('unconfirmed_notice');message+=' '+facts['unconfirmed_notice']
            message+=' Please review these modeled results; they are not a clinical guarantee.'
        elif data['plan_status']=='failed':
            message='The calculation could not finish. Your confirmed requirements are saved; retry when weather is available.'
        else:
            names=[a['details']['name'] for a in context.get('confirmed_activities',[])];message='The confirmed activities are '+', '.join(names)+'.' if names else 'There are no confirmed activities yet.'
        return wire('respond_to_user',{'message':message,'fact_references':refs,'presentation':{'kind':kind,'option_ids':ids,'show_schedule':schedule}})
    lower=question.strip().lower()
    if lower in ('hello','hi','hello!'):
        return authored('Hello! I’m here to help with your clinic’s day. What would you like to plan?')
    if 'thank' in lower:return authored('You’re welcome! What would you like to look at next?')
    if 'brainstorm' in lower or 'what can you help' in lower:
        return authored('We could explore equipment times or more solar as ideas. I can calculate a comparison when you want; these ideas have not been evaluated yet.')
    if lower in ('what are the confirmed activities?','which activities are confirmed?'):return wire('inspect_planning_state',{})
    if 'starting charge' in lower or 'current reading' in lower or 'battery capacity' in lower:
        values={}
        for field,pattern in [('battery_capacity_kwh',r'battery capacity[^\d]*(\d+(?:\.\d+)?)\s*kWh'),('initial_battery_pct',r'starting charge[^\d]*(\d+(?:\.\d+)?)%'),('current_battery_pct',r'current reading[^\d]*(\d+(?:\.\d+)?)%')]:
            match=re.search(pattern,question,re.I)
            if match:values[field]=float(match[1])
        pending=context.get('active_energy_proposal_id') or context.get('reply_context',{}).get('active_energy_proposal')
        return wire('update_energy_settings_draft' if pending else 'propose_energy_settings',values)
    if 'explain' in lower and 'plan' in lower:return wire('explain_current_plan',{})
    if 'vaccination campaign' in lower and 'change' not in lower:return wire('propose_activity',{'name':'vaccination campaign','start_hour':9,'end_hour':15})
    if '10 AM' in question:return wire('update_activity_draft',{'start_hour':10})
    if 'refrigerator' in lower:
        device=next(e for e in context.get('baseline_equipment_inventory',context.get('equipment_inventory',[])) if 'refrigerator' in e['name'].lower());return wire('update_activity_draft',{'equipment_ids':[device['id']]})
    return wire('recompute_clinic_plan',{'include_recovery':True})


def handler(request):
    if request.url.path == '/api/tags':
        return httpx.Response(200, json={'models':[{'name':'llama3.1:8b','capabilities':['tools']}]})
    payload = json.loads(request.content)
    names = {tool['function']['name'] for tool in payload['tools']}
    messages = payload['messages']
    if 'respond_to_user' in names:return natural_session(payload)
    if names == {'compose_planning_reply'}:
        source = next(json.loads(m['content']) for m in messages if m.get('role') == 'user' and m.get('content','').startswith('{') and 'verified_facts' in m['content'])
        required = source['required_references']
        options = source['recovery_options'][:3]
        selected = list(dict.fromkeys(required + options + (['battery_summary'] if 'battery_summary' in source['verified_facts'] else [])))
        # Controlled model-wire fixture. All facts still come from real backend tools.
        sentences = ['Here is my review for clinic staff.']
        for key in selected:
            item = source['verified_facts'][key]
            if isinstance(item, str):
                sentences.append(item)
            elif key == 'essential_summary':
                sentences.append(f"The existing baseline leaves {item['remaining_unserved_essential_energy']} of essential energy unserved. Flexible work unfinished is {item['flexible_unfinished']}.")
            elif key == 'selected_option':
                sentences.append(f"The selected {item['kind']} comparison leaves {item['remaining_unserved_essential_energy']} of essential energy unserved.")
                for change in item['hypothetical_changes']:
                    sentences.append(f"The selected hypothetical change is {change['field']}: {change['before']} to {change['after']}.")
            elif key.startswith('option_'):
                sentences.append(f"Tested option: {item['kind']} leaves {item['remaining_unserved_essential_energy']} of essential energy unserved.")
            elif key == 'battery_summary':
                sentences.append(f"The lowest stored battery energy is {item['lowest_stored_energy']}, against the {item['reserve_target']} reserve target.")
        return wire('compose_planning_reply', {'message':' '.join(sentences), 'fact_references':selected})
    question = next((m['content'].split('Current operator request: ', 1)[1] for m in reversed(messages) if m.get('content', '').startswith('Current operator request: ')), '')
    if names == {'conversational_reply'}:
        kind = 'thanks' if 'thank' in question.lower() else 'help' if 'help' in question.lower() else 'greeting'
        return wire('conversational_reply', {'kind':kind, 'message':"Hello! I’m here to help with your clinic’s day. What would you like to plan?" if kind == 'greeting' else "You’re welcome! Tell me what you’d like to explore next."})
    context = json.loads(next(m['content'].split('Canonical state (data): ', 1)[1] for m in messages if m.get('content', '').startswith('Canonical state (data): ')))
    details = {}
    if names == {'explain_current_plan'}:
        return wire('explain_current_plan', {})
    if 'equipment-planning activity' in question or ('Campaign light' in question and '200 W' in question):
        match = re.search(r'called [“\"]([^”\"]+)', question)
        name = match[1] if match else 'Campaign light'
        rating = re.search(r'(\d+(?:\.\d+)?) W', question)
        hours = re.search(r'from (\d{2}):00 to (\d{2}):00', question)
        device = {'id':'new-campaign-light','name':name}
        flexible = 'I designate it flexible' in question
        if rating: device['max_power_kw' if flexible else 'power_kw'] = float(rating[1]) / 1000
        if 'critical' in question: device['category'] = 'critical'
        if flexible: device['category'] = 'flexible'
        if hours: device['allowed_hours' if flexible else 'required_hours'] = list(range(int(hours[1]),int(hours[2])))
        runtime = re.search(r'rated power for (\d+) whole hours', question)
        if runtime: device['required_duration_hours'] = int(runtime[1])
        if 'I confirm its work can be paused' in question: device['divisible'] = True
        details = {'name':name,'additional_equipment':[device], 'equipment_ids':[device['id']]}
        if hours: details |= {'start_hour':int(hours[1]),'end_hour':int(hours[2])}
        return wire('propose_activity', details)
    if 'vaccination campaign' in question.lower() and 'change' not in question.lower():
        name = 'propose_activity'; details = {'name':'vaccination campaign','start_hour':9,'end_hour':15}
    elif '10 AM' in question:
        if context.get('active_proposal_id'):
            name = 'update_activity_draft'; details = {'start_hour':10}
        else:
            name = 'propose_activity_revision'; details = {'start_hour':10,'target_activity_id':context['confirmed_activities'][-1]['id']}
    elif 'refrigerator' in question.lower():
        name = 'update_activity_draft'; refrigerator = next(e for e in context['equipment_inventory'] if 'refrigerator' in e['name'].lower())
        details = {'equipment_ids':[refrigerator['id']]}
    elif question.strip().lower() in ('confirm.','confirm'):
        name = 'review_activity_proposal'
    else:
        name = 'recompute_clinic_plan'
    return wire(name, details or ({'include_recovery':True} if name == 'recompute_clinic_plan' else {}))

async def async_handler(request):
    if request.url.path == '/api/chat' and b'Observe streamed progress' in request.content:
        await asyncio.sleep(.4)  # Test-only provider latency, never a real inference benchmark.
    return handler(request)

app = create_app(forecast_service=TestWeather(), outlook_service=TestOutlook(), agent_service=LocalAgent(transport=httpx.MockTransport(async_handler)))
