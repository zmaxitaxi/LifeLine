"""Test-only model/weather transports; production imports none of this module.
The real session API, compiler, simulator, optimizer and validators remain active.
"""
import json
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

def handler(request):
    if request.url.path == '/api/tags':
        return httpx.Response(200, json={'models':[{'name':'llama3.1:8b','capabilities':['tools']}]})
    payload = json.loads(request.content)
    names = {tool['function']['name'] for tool in payload['tools']}
    messages = payload['messages']
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
    context = json.loads(next(m['content'].split('Canonical state (data): ', 1)[1] for m in messages if m.get('content', '').startswith('Canonical state (data): ')))
    if names == {'conversational_reply'}:
        kind = 'thanks' if 'thank' in question.lower() else 'help' if 'help' in question.lower() else 'greeting'
        return wire('conversational_reply', {'kind':kind, 'message':"Hello! I’m here to help with your clinic’s day. What would you like to plan?" if kind == 'greeting' else "You’re welcome! Tell me what you’d like to explore next."})
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

app = create_app(forecast_service=TestWeather(), outlook_service=TestOutlook(), agent_service=LocalAgent(transport=httpx.MockTransport(handler)))
