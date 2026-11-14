"""Legacy rollout retains actual inputs/text and marks unknown timestamps."""
from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient
from app.main import create_app
from app.planning_migration import migrate_legacy_session
from app.planning_persistence import LocalPlanningPersistence
from app.planning_state import PlanningStore
from test_weather_forecast import service_for
from test_planning_state import create, propose, confirm


def test_legacy_import_retains_confirmed_plan_without_inventing_current_measurement(tmp_path):
    service, _ = service_for()
    with TestClient(create_app(forecast_service=service)) as client:
        state = confirm(client, propose(client, create(client)))
    legacy = {key: value for key, value in state.items() if key not in (
        'energy_settings', 'current_battery_reading', 'energy_proposals', 'active_energy_proposal_id')}
    at = datetime(2026, 11, 14, 1, 0, tzinfo=timezone.utc)
    transcript = [{'role': 'user', 'text': 'Explain this selected plan.'},
        {'role': 'assistant', 'text': 'The forecast calculation is available for review.'},
        {'role': 'notice', 'text': 'Activity confirmed.'}]
    payload = migrate_legacy_session(legacy, transcript, recorded_at=at)
    path = tmp_path / 'restored.json'
    LocalPlanningPersistence(path).save(payload)
    restored = PlanningStore(path)
    current = restored.read(state['id'])
    assert current.id == state['id'] and current.current_battery_reading is None
    assert current.confirmed_activities[0].id == state['confirmed_activities'][0]['id']
    assert current.computed_plan.model_dump(mode='json') == state['computed_plan']
    assert current.energy_settings.initial_battery_kwh == 2.
    messages = restored.conversation(state['id']).messages
    assert len(messages) == 2 and all(message.imported for message in messages)
    assert all(message.created_at == at for message in messages)
    assert all(message.mode is None for message in messages)
    assert messages[1].content == transcript[1]['text']
    assert payload['conversations'] == migrate_legacy_session(legacy, transcript, recorded_at=at)['conversations']


def test_invalid_legacy_battery_config_is_rejected_instead_of_clamped():
    service, _ = service_for()
    with TestClient(create_app(forecast_service=service)) as client:
        state = create(client)
    state['clinic']['initial_battery_kwh'] = 999.
    with pytest.raises(ValueError):
        migrate_legacy_session(state)
