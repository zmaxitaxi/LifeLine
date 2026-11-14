"""Request-scoped measurements and public phase events, never model reasoning."""
from contextvars import ContextVar
from contextlib import contextmanager
from time import perf_counter
import math

ACTIVE_TRACE = ContextVar('lifeline_agent_trace', default=None)
STAGES = {'request', 'model', 'weather', 'simulation', 'serialization', 'persistence'}


class AgentTrace:
    def __init__(self, emit=None):
        self.started = perf_counter()
        self.emit = emit
        self.stages = {}
        self.model_calls = None
        self.model_metrics = []
        self.first_progress = None

    def progress(self, stage, status):
        if stage not in STAGES or status not in ('running', 'completed', 'failed'):
            return
        elapsed = perf_counter()-self.started
        if self.emit:
            if self.first_progress is None:
                self.first_progress = elapsed
            self.emit({'type': 'progress', 'stage': stage, 'status': status, 'elapsed_seconds': elapsed})

    def snapshot(self):
        return dict(total_seconds=perf_counter()-self.started,
            first_progress_seconds=self.first_progress, stages_seconds=dict(self.stages),
            model_calls=self.model_calls, model_metrics=list(self.model_metrics))


@contextmanager
def measured(stage):
    trace = ACTIVE_TRACE.get()
    started = perf_counter()
    if trace:
        trace.progress(stage, 'running')
    try:
        yield
    except BaseException:
        if trace:
            trace.progress(stage, 'failed')
        raise
    else:
        if trace:
            trace.progress(stage, 'completed')
    finally:
        if trace:
            trace.stages[stage] = trace.stages.get(stage, 0.) + perf_counter()-started


def record_model(metrics):
    trace = ACTIVE_TRACE.get()
    if trace:
        trace.model_calls = (trace.model_calls or 0)+1
        trace.model_metrics.append({key: value for key, value in metrics.items()
            if key in ('http_seconds', 'prompt_eval_count', 'eval_count', 'total_duration_ns',
                'load_duration_ns', 'prompt_eval_duration_ns', 'eval_duration_ns',
                'request_chars', 'message_chars', 'tool_schema_chars')
            and type(value) in (int, float) and math.isfinite(value) and value>=0})
