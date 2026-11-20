# LifeLine: two-minute Haiku demo

This three-prompt walkthrough was rehearsed in the browser with actual Claude Haiku, labeled sample weather, and the real simulator and optimizer. Allow time for external API replies.

## Before the timer

1. Start the [app in demo mode](../README.md#run-locally). Open the local URL
   from your launch command (port 8000 in the README). Check the **sample
   weather, not a live forecast** label and that the message box is available.
   `/api/agent/status` reports Haiku and its availability.
2. Click **Change clinic** if a clinic is already open. Create a **separate**
   clinic named `LifeLine presentation`; choose **Kisumu**. This preserves your
   other saved clinic. Do not resume a previously edited demo for this script.
3. Click **Continue to electrical setup → Autofill demo setup → Review setup**.
   Check **8 kWh battery, 1500 W solar, 75% midnight charge (= 6 kWh), 4.8 kWh
   reserve**, with the example equipment. Review the assumptions, check the
   acknowledgment and click **Open the example clinic**.
4. Read the displayed planning day. “Tomorrow” means the clinic's **Africa/Nairobi**
   day, which can differ from your California date. Do not substitute “today.”
5. Start on **AI Assistant** with no pending drafts. Keep these three prompts in
   a notes window for copy/paste. Rehearse once before presenting, then create a
   fresh example again: the final step changes its saved solar setting.

## 0:00–0:12 — Explain the problem

Say: “Clinics need electricity after sunset. LifeLine plans flexible equipment
around sunshine while preserving essential equipment requirements. Haiku chooses
tools; a physical energy model computes the results. This demonstration uses
clearly labeled sample weather.”

## 0:12–0:35 — Plan the vaccination campaign

Paste and send:

```text
Please stage a vaccination campaign tomorrow from 10 AM to 3 PM using the existing vaccine refrigerator. Do not change any device operating hours.
```

Wait for the reply. Check the draft shows **10:00–15:00**, the selected planning
date and the existing vaccine refrigerator. Click **Confirm** on its review card.
If the card is not inline, click **Review activity draft · Vaccination campaign**
above the composer, then **Confirm** in the dialog.

Say: “The operator approves changes. The existing refrigerator is counted once;
booking an activity does not invent another appliance or its electricity use.”

## 0:35–0:50 — Show the actionable schedule

Open **Clinic Overview**. Point to the confirmed activity marker and **Plans &
next steps**. Expand **Equipment times in this plan** to show the actual flexible
equipment hours. The current/proposed comparison should show the reserve risk
improving without unfinished flexible work.

Say: “We move flexible work into sunshine rather than cut the work. These
example inputs preserve about **1.115 kWh more battery energy at midnight**,
with the same **2.1 kWh** flexible work. Sunshine-first is nearly as good; we
compare it honestly.”

Those figures belong to the unchanged full-sun sample setup. They are computed
simulation results, not measured clinic savings. Do not reuse them after changing
inputs or applying the cloudy scenario below.

## 0:50–1:15 — Test adverse conditions

Return to **AI Assistant**, then send:

```text
Test tomorrow with 50% less sunshine and compare recovery options for our confirmed clinic requirements.
```

Wait for the complete reply. While it calculates, say: “Scheduling cannot create
missing sunlight. We test whether a different resource is needed and what work
would remain unfinished.”

Expected for this fixture: **essential energy is still served**, but the existing
schedule's lowest battery is about **1.961 kWh**, below the **4.8 kWh** reserve.
Do not call this an observed outage or claim essential equipment lost power.

## 1:15–1:35 — Compare a real computed alternative

Open **Clinic Overview → All calculated plans**. Choose **Add solar panels ·
3.5 kW**. Point to the comparison, battery forecast, benefits and limitations.

Say: “This tested combination of more solar and the proposed equipment schedule
raises the minimum stored energy to about **4.975 kWh**, with all original work
completed. It is hypothetical; selecting a comparison does not install panels
or change the clinic's confirmed settings. Prices require a quote.”

More empty battery capacity does not automatically fix this case. Some tested
alternatives leave flexible work unfinished; the UI reports that explicitly.

## 1:35–2:00 — Review, save and prove persistence

Return to **AI Assistant** and send:

```text
Create a draft to set solar panel capacity to 3.5 kW. Keep all other energy settings and equipment unchanged. Do not confirm it.
```

Open **Review power settings draft** if the review card is not inline. Verify
**only solar changes, 1.5 → 3.5 kW**; battery size and starting energy remain
**8 kWh / 6 kWh**. Click **Confirm power settings**, then reload the page.

Open **Clinic Overview**: the vaccination activity is still present. **Power
setup** shows **3.5 kW** solar. Close it without making another edit.

Say: “Confirmed activity and planning settings are saved and recalculated. This
changes the planning model, not physical equipment. LifeLine supports staff
decisions; it does not establish clinical safety or guarantee electricity.”

The current fixed schedule can still differ from the proposed optimized schedule.
Do not imply that confirming a panel rating automatically operates equipment at
the recommended times.

## If something interrupts the live demonstration

- **Still calculating:** wait for the completed reply; do not send duplicate
  prompts. Talk through the chart or the explicit review boundary while waiting.
- **Reply rejected:** inspect Overview and pending drafts first. The calculation
  or a draft may already be saved. Use **Retry reply** once after checking state;
  do not create the same activity again blindly.
- **API/network unavailable:** use the manual review forms and already computed
  results, identifying them as saved results. Do not present a prerecorded or
  template answer as live Haiku. A strict two-minute slot cannot be guaranteed
  during an external outage.
- **Wrong date, figures or equipment:** stop and create the fresh example above.
  Do not force confirmation, invent missing ratings or claim the old figures
  describe a different setup.

## Extra prompts tested outside the two-minute presentation

Draft revision (review it, then **Cancel** to retain the original 10:00 start):

```text
Create a draft revision of the confirmed vaccination campaign: start at 11 AM tomorrow, keep its 3 PM end and the existing refrigerator. Do not confirm it.
```

After selecting a recovery option, explain it without another calculation:

```text
Please explain my exact selected plan against the existing baseline without recalculating or refreshing weather.
```

Ask for actual computed equipment slots without another calculation:

```text
Using the current optimized schedule, what are the auxiliary laundry's hourly slots? Use the existing calculation; do not recalculate or change equipment.
```

## Rehearse against an isolated server

With the UI built and the server credentials configured, start a separate
instance with a fresh private state file. This rehearsal makes billed Anthropic
API requests and creates an example clinic through the browser.

```bash
rehearsal_state_path="$(mktemp -d)/planning-state.json"
LIFELINE_STATE_PATH="$rehearsal_state_path" \
  LIFELINE_WEATHER_MODE=demo .venv/bin/python -m uvicorn app.main:app \
  --app-dir backend --host 127.0.0.1 --port 8038
```

In another terminal, install Chromium if needed and run the three-prompt path:

```bash
npm --prefix frontend exec -- playwright install chromium
node scripts/rehearse_haiku_demo.mjs --core
```

Omit `--core` for the longer workflow. To test restart recovery, restart the
isolated server with the same `rehearsal_state_path`, then run
`node scripts/rehearse_haiku_demo.mjs --restore`. Reuse the same
`LIFELINE_REHEARSAL_OUTPUT` if set. The default output folder is
`lifeline-haiku-full-rehearsal` under the OS temporary directory.

See [observed rehearsal results](VALIDATION.md#assistant-and-browser-verification)
and [live weather verification](WEATHER.md#verify-and-troubleshoot).
