# LifeLine: two-minute Haiku demo

Use these prompts verbatim with the example clinic below. They were exercised
through the real browser with actual `claude-haiku-5-5`, synthetic demo weather,
the existing simulator/MILP, explicit confirmations and saved state. This is a
rehearsed path, not a guarantee that an API or generated reply cannot fail.

## Before the timer

1. Open `http://127.0.0.1:8020/`. Check the header says **Anthropic Claude API ·
   claude-haiku-5-5**, with the **sample weather, not a live forecast** label.
   The assistant needs internet even though sample weather does not.
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

## Verification scope

The genuine desktop rehearsal covers fresh setup, complete vaccination drafting,
draft reload, explicit confirmation, repeat-confirm idempotency, one shared
refrigerator, revision/cancellation, cloudy recovery, comparison selection,
read-only explanation, reviewed solar changes, reload and backend-restart
persistence. It also checks meaningful rendering, no framework overlay, no page
errors and screenshots at the important steps. Browser plugin was unavailable;
the repository's Playwright installation was used at 1280 × 1000.

The complete five-prompt workflow passed in **30.1 seconds** of automated browser
time, excluding narration. The separate three-prompt presentation passed in
**21.0 seconds**. Its observed replies took **5.2s / 6.4s / 6.8s** for vaccination,
cloudy recovery and solar settings. A read-only laundry-slot follow-up passed and
matched the actual 10:00–11:00 and 11:00–12:00 allocations in that saved result.
Both saved clinics and their conversations survived a real backend restart.
These are observations, not latency or arbitrary-language guarantees. The
regression suites pass **525 backend tests and 56 browser tests**.

A repeated short run exposed a source-validation bug: “essential demand met but
flexible work unfinished” was incorrectly treated as claiming all work was met.
The fix checks both clauses against the exact option, supplies its actual reserve
target and correctly identifies battery metrics and parenthetical original
capacity. Regression tests still reject false all-work coverage and mismatched
minimum/reserve figures. Earlier failed evidence is retained locally.

Reproduce against a separate persistent demo server on port 8038, never a second
worker sharing the presentation's state file:

```bash
node scripts/rehearse_haiku_demo.mjs
node scripts/rehearse_haiku_demo.mjs --core
# Restart that isolated backend with the SAME test state file, then:
node scripts/rehearse_haiku_demo.mjs --restore
```

Use `LIFELINE_REHEARSAL_OUTPUT` to keep a separate output folder for each run and
reuse the same folder for `--restore`. The runner makes actual billed Haiku
requests and creates an isolated example through the UI. Detailed state,
conversation and screenshots stay in the OS temporary directory, not the repo.
