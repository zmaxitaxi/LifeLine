"""Explicit offline import of a legacy session; never manufactures measurements."""
import json
from datetime import datetime, timezone
from uuid import uuid5, NAMESPACE_URL
from .planning_models import PlanningState, PlanningMessage
from .models import SimulationRequest
from .scenarios import load_catalog


def migrate_legacy_session(value, transcript=None, *, recorded_at=None):
    catalog = load_catalog()
    data = dict(value)
    config = catalog.resolve(SimulationRequest.model_validate_json(json.dumps(data['clinic'])))
    data.setdefault('energy_settings', config.model_dump(mode='json'))
    data.setdefault('current_battery_reading', None)
    data.setdefault('energy_proposals', [])
    data.setdefault('active_energy_proposal_id', None)
    state = PlanningState.model_validate_json(json.dumps(data))
    now = recorded_at or datetime.now(timezone.utc)
    entries = transcript.get('messages', []) if isinstance(transcript, dict) else transcript or []
    messages = []
    seen = set()
    for index, entry in enumerate(entries):
        if entry.get('role') not in ('user', 'assistant'):
            continue  # UI receipts/notices must never become model-authored prose.
        text = entry.get('content') or entry.get('text')
        if not isinstance(text, str) or not text.strip():
            continue
        identifier = entry.get('id') or str(uuid5(NAMESPACE_URL,
            f"lifeline:{state.id}:legacy:{index}:{entry['role']}:{text}"))
        if identifier in seen:
            continue
        seen.add(identifier)
        values = dict(id=identifier, role=entry['role'], content=text,
            created_at=entry.get('created_at') or now.isoformat(), imported=True,
            mode=entry.get('mode') if entry.get('mode') in ('local_tool_agent', 'local_agent_unavailable') else None)
        messages.append(PlanningMessage.model_validate_json(json.dumps(values)))
    plan = state.computed_plan
    payload = {'schema_version': 1, 'states': {state.id: state.model_dump(mode='json')},
        'receipts': [], 'generations': {state.id: plan.generation if plan else 0},
        'history': {state.id: [m.content for m in messages if m.role == 'user'][-8:]},
        'last_edited_fields': {}, 'conversations': {state.id: [m.model_dump(mode='json') for m in messages][-80:]},
        'migration': {'recorded_at': now.isoformat(), 'legacy_session_id': state.id,
            'historical_timestamps': 'Original where supplied; otherwise recorded at import, marked imported.',
            'legacy_receipts': 'Unavailable in the legacy GET response; confirmed proposal states still prevent double confirmation.'}}
    return payload
