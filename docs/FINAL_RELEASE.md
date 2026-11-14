# Working hackathon demo release

The current demonstration uses **Claude Haiku**, `claude-haiku-5-5`, explicitly
**synthetic sample weather**, and the unchanged real PV/battery simulator,
sunshine-first heuristic and MILP. It does not use Llama or an automatic model
fallback. Claude needs internet and a server-side Anthropic key; the numerical
model and manual configuration remain available without the assistant.

## Delivered workflow

- Configure location and reviewed electrical requirements, with explicit demo
  autofill and saved-clinic resume. Setup starts tomorrow in the clinic timezone
  and displays the date for review. Empty essential requirements are incomplete,
  never a finding of reliable electricity.
- The assistant authors genuine replies and selects native tools. Activity and
  energy settings remain drafts until explicit operator confirmation. Shared
  devices are counted once; event duration does not invent device runtime.
- Overview leads with the current outlook and recommended action/comparison,
  then hourly solar/supplied/missing energy beside the synchronized battery.
  Editable requirements, weather and all other computed alternatives remain
  accessible. Pending requirements are visibly excluded from current results.
- Fixed/sunshine-first/MILP and recovery comparisons preserve physical limits,
  protected requirements and absolute initial stored energy. Exact selected-plan
  explanations reuse their calculation. Parts prices remain not estimated.
- Public SSE phase updates precede a final validated reply. Raw reasoning and
  invalid model text are never streamed. Interrupted streams are not replayed
  automatically. Structured failures persist across reloads; stale replies are
  checked inside the conversation persistence lock.
- Private atomic snapshots preserve canonical clinic work and conversation.
  The original dirty checkout is retained; the durable running checkout is below.

## Verification

| Check | Result / scope |
|---|---|
| Backend | 525 tests pass, Python 3.12; one upstream deprecation warning |
| Frontend | 56/56 Chromium journeys pass, including mobile/keyboard/source/state checks |
| TypeScript / production build | Pass |
| Genuine Haiku API | Seven journey types have successful targeted evidence; the final seven-case batch was 6/7, followed by a passing corrected recovery rerun |
| Genuine browser | Hello 2.272s; clinic assessment 6.685s; first public progress DOM commits 34.8ms / 23.4ms; no page errors or adopted changes |

The genuine browser assessment made three model calls and one numerical tool
call. Its recorded model wall time was 6.521s, versus 0.034s numerical work.
Progress DOM commit is not model first-token time or completed answer latency.
[Browser evidence](evidence/claude-genuine-browser.json),
[full API timings, failures and limits](HAIKU_VALIDATION.md).
After cutover, a separate read-only browser check verified the actual saved
clinic, unchanged canonical inputs and result timestamp, Claude status, hourly
chart values and both editing dialogs, with no POSTs or inference. The first CI
browser failure was a Mac-only screenshot output path; the test now uses
Playwright's portable per-test output directory.
Browser regression weather/model transports are fixtures; those 56 tests do not
measure genuine inference. Earlier failed runs remain evidence, and the previous
local-model evaluation score does not transfer to Claude.

## Calculated scheduling value

The [default sample-weather proof](evidence/demo-weather-scheduling-proof.json)
uses identical weather, equipment, starting energy and limits for every schedule.
All serve **5.34 kWh essential demand** and **2.1 kWh flexible work**.

| Metric | Fixed | Sunshine-first | MILP |
|---|---:|---:|---:|
| Final battery, kWh | 4.584532 | 5.681938 | 5.699534 |
| Minimum battery, kWh | 4.584532 | 4.952953 | 4.952953 |
| Conversion losses, kWh | 0.383497 | 0.232908 | 0.215311 |

MILP preserves **1.115003 kWh** more at midnight than fixed scheduling and
removes its reserve breaches. Sunshine-first is nearly as good. These are modeled
sample-data results, not measured savings at a real clinic.

## Exact local launch

The preserved running source is
`/Users/maxli/Documents/ChatGPT/LifeLine/.worktrees/final-product`.
Use its repository root after building the frontend:

```bash
LIFELINE_AI_PROVIDER=claude \
LIFELINE_CLAUDE_MODEL=claude-haiku-5-5 \
LIFELINE_ENV_FILE=/Users/maxli/Documents/ChatGPT/LifeLine/.env.local \
LIFELINE_WEATHER_MODE=demo \
LIFELINE_STATE_PATH=/Users/maxli/Documents/ChatGPT/LifeLine/.local/final-planning-state.json \
.venv/bin/python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8020
```

Open `http://127.0.0.1:8020/`. Do not start a second worker against the same saved
state file. New clones use [the portable demo commands](../DEMO.md) and
[Claude setup](CLAUDE_DEMO.md).

## Practical limits

API access, network availability and valid generated output cannot be guaranteed.
Strict validation can still require correction or retry; failures preserve saved
inputs. The seven-case batch's recovery failure and subsequent fix are explicitly
recorded. Simulation weather is not a geographic prediction. Live Open-Meteo
remains optional, with the Mac TLS failure documented in [the dated investigation](../WEATHER_NETWORK.md).
Seven-day weather rows are not seven-day electricity plans. Changing a session's
clinic/date requires a deliberate new dated session; the assistant never silently
moves confirmed work. Field calibration, clinical approval, measured impact,
certified hardware sizing and official hackathon submission remain outside these
engineering checks.

## Full demo rehearsal follow-up

The [two-minute presentation](../DEMO_2_MINUTES.md) was exercised with actual Haiku
in a separate persistent clinic. The full flow verified vaccination drafting,
confirmation, revision/cancellation, one shared refrigerator, idempotent receipt,
50%-sunshine recovery, exact selected-plan explanation, reviewed solar settings,
reload and real backend restart. A separate short run uses only the three
presentation prompts. Actual hourly schedule facts now reach Haiku, so it can
explain the simulator's laundry slots instead of claiming no times were supplied.

The repeat uncovered a source guard confusing essential coverage with unfinished
flexible work. It now checks both claims independently against the same option,
includes actual option reserve targets, and distinguishes hardware capacity from
battery metrics. A contradictory minimum-battery direction is rejected. The
physical engine and operator confirmation requirements are unchanged. The final
backend suite has 525 tests; model requests and external services can still fail.
