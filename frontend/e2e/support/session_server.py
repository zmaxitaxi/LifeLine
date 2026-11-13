"""Frontend integration harness only. Real session API/model with fixture transports.

No test route is added. A temporary file injects a weather outage; production
code never imports this file. The LLM fixture emits native calls which the real
backend still validates, grounds, compiles and calculates.
"""
import json
import os
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
from app import planning_agent

class FixtureDateTime(datetime):
    @classmethod
    def now(cls, tz=None):
        return NOW.astimezone(tz) if tz else NOW.replace(tzinfo=None)

# Keep relative-date grounding on the same explicit test date as test weather.
planning_agent.datetime = FixtureDateTime

weather, _ = service_for()
class TestWeather:
    async def get(self, location):
        failure_file = os.environ.get('LIFELINE_TEST_WEATHER_FAILURE_FILE')
        if failure_file and Path(failure_file).exists():
            raise ForecastError('FORECAST_UNAVAILABLE', 'Injected browser-test weather outage')
        return await weather.get(location)

def handler(request):
    if request.url.path == '/api/tags':
        return httpx.Response(200, json={'models':[{'name':'llama3.1:8b','capabilities':['tools']}]})
    payload = json.loads(request.content)
    messages = payload['messages']
    question = next((m['content'].split('Current operator request: ', 1)[1] for m in reversed(messages) if m.get('content', '').startswith('Current operator request: ')), '')
    context = json.loads(next(m['content'].split('Canonical state (data): ', 1)[1] for m in messages if m.get('content', '').startswith('Canonical state (data): ')))
    details = {}
    if 'vaccination campaign' in question.lower():
        name = 'propose_activity'
        details = {'name':'vaccination campaign','start_hour':9,'end_hour':15}
    elif '10 AM' in question:
        name = 'update_activity_draft'; details = {'start_hour':10}
    elif 'refrigerator' in question.lower():
        name = 'update_activity_draft'
        refrigerator = next(e for e in context['equipment_inventory'] if 'refrigerator' in e['name'].lower())
        details = {'equipment_ids':[refrigerator['id']]}
    elif 'confirm' in question.lower():
        name = 'review_activity_proposal'
    else:
        name = 'recompute_clinic_plan'
    arguments = details if details else ({'include_recovery':True} if name == 'recompute_clinic_plan' else {})
    return httpx.Response(200, json={'message':{'role':'assistant', 'content':'INVENTED MODEL PROSE MUST NOT RENDER', 'tool_calls':[{'function':{'name':name,'arguments':arguments}}]}})

app = create_app(forecast_service=TestWeather(), agent_service=LocalAgent(transport=httpx.MockTransport(handler)))
