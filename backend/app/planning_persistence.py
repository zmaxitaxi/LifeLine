"""Atomic private local snapshots for the single-process desktop prototype."""
import json
import os
from pathlib import Path
import tempfile


class LocalPlanningPersistence:
    def __init__(self, path):
        self.path = Path(path) if path is not None else None

    def load(self):
        if self.path is None or not self.path.exists():
            return None
        try:
            value = json.loads(self.path.read_text(encoding='utf-8'))
            if not isinstance(value, dict) or value.get('schema_version') != 1:
                raise ValueError('Unsupported planning snapshot version')
            return value
        except (ValueError, OSError) as exc:
            # Never silently erase confirmed operator inputs on a corrupt file.
            raise RuntimeError('Local planning state cannot be read. Preserve the state file and restore a valid snapshot before starting.') from exc

    def save(self, value):
        if self.path is None:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=self.path.parent,
                    prefix='.planning-', suffix='.tmp', delete=False) as handle:
                temporary = Path(handle.name)
                os.chmod(temporary, 0o600)
                json.dump(value, handle, ensure_ascii=False, allow_nan=False, separators=(',', ':'))
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, self.path)
            # Commit the rename as well as its contents where supported.
            descriptor = os.open(self.path.parent, os.O_RDONLY)
            try:
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
