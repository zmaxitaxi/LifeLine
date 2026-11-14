"""Explicit provider selection; no silent provider changes on failure."""
import os
from pathlib import Path
from .local_agent import LocalAgent
from .claude_agent import ClaudeAgent


def load_local_settings(path=None):
    path=Path(path or os.environ.get('LIFELINE_ENV_FILE') or Path(__file__).resolve().parents[2]/'.env.local')
    if not path.is_file():
        return
    allowed={'ANTHROPIC_API_KEY','LIFELINE_AI_PROVIDER','LIFELINE_CLAUDE_MODEL','LIFELINE_LOCAL_MODEL'}
    for line in path.read_text().splitlines():
        key,separator,value=line.strip().partition('=')
        if separator and key in allowed:
            value=value.strip()
            if len(value)>=2 and value[0]==value[-1] and value[0] in ('"',"'"):
                value=value[1:-1]
            if value:
                os.environ.setdefault(key,value)


def configured_agent(provider=None):
    selected=provider or os.environ.get('LIFELINE_AI_PROVIDER','claude')
    if selected=='claude':
        return ClaudeAgent()
    if selected=='local':
        return LocalAgent()
    raise ValueError('LIFELINE_AI_PROVIDER must be local or claude')
