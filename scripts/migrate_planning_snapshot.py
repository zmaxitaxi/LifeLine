"""Validate/export one old session before switching to the persistent release.

Use only while the new server is stopped. The output must be a NEW file;
the source exports stay intact. UI notice messages are not relabeled as Llama.
"""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
from app.planning_migration import migrate_legacy_session
from app.planning_persistence import LocalPlanningPersistence
from app.planning_state import PlanningStore


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state', type=Path, required=True)
    parser.add_argument('--conversation', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Output already exists; choose a new file to preserve existing sessions.')
    state = json.loads(args.state.read_text())
    conversation = json.loads(args.conversation.read_text()) if args.conversation else []
    payload = migrate_legacy_session(state, conversation)
    LocalPlanningPersistence(args.output).save(payload)
    restored = PlanningStore(args.output).read(state['id'])
    print(json.dumps({'session_id': restored.id, 'planning_date': str(restored.planning_date),
        'confirmed_activities': len(restored.confirmed_activities),
        'imported_messages': len(payload['conversations'][restored.id]),
        'current_reading': 'retained' if restored.current_battery_reading else 'not invented',
        'plan_status': restored.plan_status, 'output': str(args.output)}))


if __name__ == '__main__':
    main()
