import { test, expect } from "@playwright/test";
import { tmpdir } from "node:os";
import { join } from "node:path";
import {
  open,
  seed,
  weatherFailure,
  readyDraft,
  confirm,
  read,
  say,
  proposal,
  overview,
  assistant,
  apiBase,
} from "./support/planning";
test.beforeEach(() => weatherFailure(false));
test.afterEach(() => weatherFailure(false));

test("activity conversation produces a structured proposal and explicit confirmation updates both pages", async ({
  page,
  request,
}) => {
  await page.setViewportSize({ width: 1280, height: 900 });
  const initial = await seed(request);
  await open(page, initial);
  await say(page, "We have a vaccination campaign tomorrow from 9 AM to 3 PM.");
  await expect(proposal(page)).toContainText("vaccination campaign");
  await expect(proposal(page)).toContainText("2026-11-14");
  await expect(proposal(page)).toContainText("09:00–15:00");
  await expect(
    proposal(page).getByRole("button", { name: "Confirm", exact: true }),
  ).toBeDisabled();
  expect((await read(request, initial.id)).confirmed_activities).toHaveLength(
    0,
  );
  await say(page, "Use the Vaccine refrigerator.");
  await expect(proposal(page)).toContainText("100 W");
  await proposal(page).evaluate((el) => {
    const root = el.closest(".chat-transcript")!;
    root.scrollTop +=
      el.getBoundingClientRect().top - root.getBoundingClientRect().top - 12;
  });
  await page.screenshot({
    path: join(tmpdir(), "lifeline-two-page-proposal.png"),
  });
  await say(page, "Confirm.");
  expect((await read(request, initial.id)).confirmed_activities).toHaveLength(
    0,
  );
  await confirm(page);
  const state = await read(request, initial.id);
  expect(state.confirmed_activities).toHaveLength(1);
  expect(
    state.computed_plan!.simulation.optimized.metrics.critical_requested_kwh,
  ).toBeCloseTo(2.4, 8);
  expect(state.equipment_inventory).toHaveLength(2);
  await expect(proposal(page)).toHaveCount(0);
  await expect(
    page.getByTestId("current-plan-summary").filter({ visible: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Explore plan", exact: true }).click();
  await expect(overview(page)).toHaveAttribute("aria-current", "page");
  await expect(page.getByTestId("confirmed-activity")).toContainText(
    "vaccination campaign",
  );
  await assistant(page).click();
  await expect(assistant(page)).toHaveAttribute("aria-current", "page");
  await expect(
    page
      .locator(".assistant-text")
      .filter({ hasText: "We have a vaccination campaign tomorrow" }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Reported tool activity", exact: true })
    .first()
    .click();
  await expect(page.locator(".chat-transcript")).toContainText(
    "Requested: Propose a clinic activity",
  );
  await expect(
    page.getByText("INVENTED MODEL PROSE MUST NOT RENDER", { exact: false }),
  ).toHaveCount(0);
});

test("a correction updates the same draft and cancel never adopts its requirements", async ({
  page,
  request,
}) => {
  const state = await seed(request);
  await open(page, state);
  await readyDraft(page);
  const before = await read(request, state.id);
  const id = before.active_proposal_id;
  await say(page, "Actually start at 10 AM.");
  const corrected = await read(request, state.id);
  expect(corrected.active_proposal_id).toBe(id);
  expect(corrected.proposals).toHaveLength(1);
  expect(corrected.proposals[0].details.start_hour).toBe(10);
  await proposal(page)
    .getByRole("button", { name: "Cancel", exact: true })
    .click();
  await expect(proposal(page)).toHaveCount(0);
  const rejected = await read(request, state.id);
  expect(rejected.confirmed_activities).toHaveLength(0);
  expect(rejected.proposals[0].status).toBe("rejected");
  expect(rejected.input_revision).toBe(before.input_revision);
});

test("missing added-equipment specifications can be filled manually without changing known ratings", async ({
  page,
  request,
}) => {
  const state = await seed(request);
  const created = await request.post(`${apiBase}/${state.id}/proposals`, {
    data: {
      expected_revision: state.revision,
      details: {
        name: "Evening clinic",
        planning_date: state.planning_date,
        start_hour: 10,
        end_hour: 15,
        equipment_ids: ["new-light"],
        additional_equipment: [
          {
            id: "new-light",
            name: "Campaign light",
            category: "critical",
            required_hours: [10, 11],
          },
        ],
      },
    },
  });
  expect(created.ok(), await created.text()).toBe(true);
  await open(page, await created.json());
  await expect(proposal(page)).toContainText("power rating from the label");
  await proposal(page)
    .getByLabel("Power rating on the label (W)", { exact: true })
    .fill("200");
  await proposal(page)
    .getByRole("button", { name: "Save draft for review", exact: true })
    .click();
  await expect(
    proposal(page).getByRole("button", { name: "Confirm", exact: true }),
  ).toBeEnabled();
  await confirm(page);
  const after = await read(request, state.id);
  expect(after.equipment_inventory.find((e) => e.id === "fridge")).toEqual(
    state.equipment_inventory.find((e) => e.id === "fridge"),
  );
  expect(
    after.computed_plan!.simulation.optimized.metrics.critical_requested_kwh,
  ).toBeCloseTo(2.8, 8);
});

test("local-model failure leaves deterministic calculation and manual activity review available", async ({
  page,
  request,
}) => {
  const state = await seed(request);
  await page.route("**/api/planning/sessions/*/agent", (route) =>
    route.fulfill({
      json: {
        mode: "local_agent_unavailable",
        model: null,
        message:
          "The local model is unavailable. Use the manual activity editor or retry.",
        needs_clarification: true,
        clarification_fields: [],
        tool_calls: [],
        state,
      },
    }),
  );
  await open(page, state);
  await say(page, "Calculate the energy plan.");
  await expect(page.locator(".assistant-text").last()).toContainText(
    "local model is unavailable",
  );
  await page
    .getByRole("button", { name: "Calculate plan", exact: true })
    .click();
  await expect(
    page.getByTestId("current-plan-summary").filter({ visible: true }),
  ).toBeVisible();
  expect((await read(request, state.id)).computed_plan).not.toBeNull();
});
