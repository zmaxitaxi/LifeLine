# Local assistant response pipeline

LifeLine uses actual local `llama3.1:8b` inference. For the offline demonstration,
start with `LIFELINE_WEATHER_MODE=demo`: weather is explicitly synthetic; the
existing photovoltaic model, battery simulator, scheduling heuristic and MILP
still calculate all energy results. This mode needs no weather network access
or paid model API key. It does not demonstrate live forecast availability.

## Public progress and completed responses

`POST /api/planning/sessions/{id}/agent` remains available with its existing
request and response behavior. Responses add nullable `failure` and `timings`
fields. Existing callers can continue using this endpoint.

`POST /api/planning/sessions/{id}/agent/stream` accepts the same request and
returns server-sent events. Each event is JSON in a `data:` line:

- `progress`: a fixed public phase (`request`, `model`, `weather`, `simulation`,
  `serialization`, `persistence`), status and elapsed seconds.
- `result`: one completed, validated `SessionAgentResponse`, including canonical
  state. Only this event supplies an assistant answer or proposed changes.
- `error`: an actionable public error code and message; no partial answer is
  adopted. An unexpected exception exposes no provider text or internal prompt.

Public phase updates are activity indicators. They are neither model reasoning
nor proof that the final answer is ready. The application does not display raw
model text before the source, numerical and confirmation checks have passed.
No automatic replay follows an interrupted stream: reload current state and
inspect any pending proposals before explicitly retrying.

A stale request revision returns HTTP 409 before starting inference. A conflict
after streaming starts is an error event. Existing explicit operator
confirmation, revision checks and canonical conversation persistence still apply.

## Timing interpretation

`timings.total_seconds` measures the backend request through conversation
persistence. `first_progress_seconds` is the server's first public event,
not first token or final answer latency. Browser rendering and transport can add
time. `stages_seconds` contains measured phases only; nested phase totals are
not additive. Unmeasured model counts remain null rather than claiming zero.

Provider diagnostics allow only finite nonnegative numerical timing/token/size
fields. Prompts, provider content and private reasoning are excluded. Actual
model prompt evaluation, generation and loading durations are recorded in
nanoseconds; HTTP and phase wall times are seconds. A reproducible genuine-model
benchmark separates these from numerical solver runtime and serialization.

Structured failures distinguish model timeout, busy/unavailable providers,
invalid or rejected output, unavailable weather and a date mismatch. A date
mismatch must explain the requested and selected clinic-local dates; blindly
retrying or silently moving confirmed activities is inappropriate.

## Verification and limits

Backend regressions cover final-event ordering, stale requests, sanitized
unexpected failures and conflicts without partial result/history adoption.
These transport tests use controlled model fixtures; genuine inference evidence
is recorded separately and may still expose failures or variable latency.

Parts costs remain `not_estimated`, with amount, currency and source null until
verified prices or a local quote are supplied. Additional-resource comparisons
are modeled options, not installation specifications or clinical assurances.
