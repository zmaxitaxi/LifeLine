"""Regenerate OpenAPI and a real API example for frontend development.

Requires backend/requirements-dev.txt. These artifacts are documentation only;
the live endpoints always calculate from the model and never read the example.
"""

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
from fastapi.testclient import TestClient
from app.main import create_app


def main():
    with TestClient(create_app()) as client:
        schema = client.get('/openapi.json')
        schema.raise_for_status()
        example = client.post('/api/simulate', json={'scenario': 'scheduling'})
        example.raise_for_status()
    output = ROOT / 'contracts'
    (output / 'examples').mkdir(exist_ok=True)
    (output / 'openapi.json').write_text(json.dumps(schema.json(), indent=2, allow_nan=False)+'\n')
    (output / 'examples/scheduling.response.json').write_text(json.dumps(example.json(), indent=2, allow_nan=False)+'\n')
    print('Exported contracts/openapi.json and contracts/examples/scheduling.response.json (computed example only).')


if __name__ == '__main__':
    main()
