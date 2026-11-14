"""Recompute API examples with explicitly SYNTHETIC test weather, never live data.

Documentation generator only; requires development dependencies. Runtime routes
never load these examples or the test transport used to produce them.
"""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'backend'), str(ROOT / 'backend' / 'tests')]
from fastapi.testclient import TestClient
from app.main import create_app
from app.planning_models import PlanningState
from test_weather_forecast import service_for


def main():
    directory = ROOT / 'contracts' / 'examples'
    def write(name, value):
        (directory / name).write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')
    def post(client, path, body):
        response = client.post(path, json=body)
        response.raise_for_status()
        value = response.json()
        PlanningState.model_validate_json(response.text)
        return value
    create = json.loads((directory / 'planning.create.request.json').read_text())
    proposal = json.loads((directory / 'planning.propose.request.json').read_text())
    service, _ = service_for()  # fixed test transport, no external weather request
    base = '/api/planning/sessions'
    with TestClient(create_app(forecast_service=service)) as client:
        state = post(client, base, create)
        write('planning.create.response.json', state)
        proposal['expected_revision'] = state['revision']
        write('planning.propose.request.json', proposal)
        state = post(client, f"{base}/{state['id']}/proposals", proposal)
        write('planning.draft.response.json', state)
        confirm = {'expected_revision': state['revision'], 'idempotency_key': 'example-operator-click-001'}
        write('planning.confirm.request.json', confirm)
        state = post(client, f"{base}/{state['id']}/proposals/{state['active_proposal_id']}/confirm", confirm)
        write('planning.confirm.response.json', state)
        energy = {'expected_revision': state['revision'], 'settings': {'battery_capacity_kwh': 8.}}
        write('planning.energy-propose.request.json', energy)
        state = post(client, f"{base}/{state['id']}/energy-proposals", energy)
        write('planning.energy-draft.response.json', state)
        confirm = {'expected_revision': state['revision'], 'idempotency_key': 'example-energy-click-001'}
        write('planning.energy-confirm.request.json', confirm)
        state = post(client, f"{base}/{state['id']}/energy-proposals/{state['active_energy_proposal_id']}/confirm", confirm)
        write('planning.energy-confirm.response.json', state)
    print('Exported planning examples: real simulator/MILP, explicitly SYNTHETIC test weather; not live evidence.')


if __name__ == '__main__':
    main()
