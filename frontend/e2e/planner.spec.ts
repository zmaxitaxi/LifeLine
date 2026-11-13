import { test, expect } from "@playwright/test";
import { tmpdir } from "node:os";
import { join } from "node:path";
import {
  assistant,
  overview,
  open,
  seed,
  weatherFailure,
  proposal,
  apiBase,
  read,
  readyDraft,
  confirm,
} from "./support/planning";
test.beforeEach(() => weatherFailure(false));
test.afterEach(() => weatherFailure(false));

test("exactly two primary destinations preserve the conversation and unsent input", async ({
  page,
  request,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  page.on("console", (m) => {
    if (m.type() === "error") errors.push(m.text());
  });
  await open(page, await seed(request));
  await expect(page).toHaveTitle(/LifeLine/);
  const navigation = page.getByRole("navigation", {
    name: "Primary navigation",
    exact: true,
  });
  await expect(navigation.getByRole("link")).toHaveCount(2);
  await expect(assistant(page)).toHaveAttribute("aria-current", "page");
  await expect(page.getByTestId("battery-playback")).toHaveCount(0);
  await expect(page.locator(".chat-weather")).not.toContainText(
    /Open-Meteo|cached forecast|updated/,
  );
  await expect(
    page.getByText("No current verified energy plan.", { exact: true }),
  ).toHaveCount(0);
  await expect(
    page
      .locator('.chat-suggestions[aria-label="Suggested questions"]')
      .getByRole("button", { name: "Calculate plan", exact: true }),
  ).toBeVisible();
  await page
    .getByRole("textbox", { name: "Message LifeLine", exact: true })
    .fill("We need to plan tomorrow’s clinic work");
  await overview(page).click();
  await expect(overview(page)).toHaveAttribute("aria-current", "page");
  await expect(
    page.getByRole("heading", { name: "Clinic Overview", exact: true }),
  ).toBeVisible();
  for (const name of [
    "Activities & Equipment",
    "Weather",
    "Battery & Energy",
    "Solutions",
  ])
    await expect(
      page.getByRole("heading", { name, exact: true }),
    ).toBeVisible();
  await assistant(page).click();
  await expect(assistant(page)).toHaveAttribute("aria-current", "page");
  await expect(
    page.getByRole("textbox", { name: "Message LifeLine", exact: true }),
  ).toHaveValue("We need to plan tomorrow’s clinic work");
  await expect(page.locator("vite-error-overlay")).toHaveCount(0);
  expect(errors).toEqual([]);
  await page.screenshot({
    path: join(tmpdir(), "lifeline-two-page-assistant.png"),
  });
});

test("manual creation and editing use the same revisioned activity state as chat", async ({
  page,
  request,
}) => {
  const initial = await seed(request);
  await open(page, initial);
  await overview(page).click();
  await expect(overview(page)).toHaveAttribute("aria-current", "page");
  await page
    .getByRole("button", { name: "Add activity manually", exact: true })
    .click();
  const card = proposal(page);
  await card
    .getByLabel("Activity name", { exact: true })
    .fill("Morning vaccination clinic");
  await card.getByLabel("Start hour (0–23)", { exact: true }).fill("9");
  await card.getByLabel("Finish hour (1–24)", { exact: true }).fill("15");
  await card
    .getByRole("checkbox", { name: "Vaccine refrigerator", exact: true })
    .check();
  await card.getByRole("checkbox", { name: /I reviewed this list/ }).check();
  await card
    .getByRole("button", { name: "Save draft for review", exact: true })
    .click();
  await expect(
    card.getByRole("button", { name: "Confirm", exact: true }),
  ).toBeEnabled();
  expect((await read(request, initial.id)).confirmed_activities).toHaveLength(
    0,
  );
  await confirm(page);
  await expect(page.getByTestId("confirmed-activity")).toContainText(
    "Morning vaccination clinic",
  );
  await page
    .getByRole("button", { name: "Edit activity", exact: true })
    .click();
  await proposal(page)
    .getByLabel("Start hour (0–23)", { exact: true })
    .fill("10");
  await proposal(page)
    .getByRole("button", { name: "Save draft for review", exact: true })
    .click();
  const before = await read(request, initial.id);
  expect(before.confirmed_activities[0].details.start_hour).toBe(9);
  await confirm(page);
  const after = await read(request, initial.id);
  expect(after.confirmed_activities).toHaveLength(1);
  expect(after.confirmed_activities[0].details.start_hour).toBe(10);
  expect(after.confirmed_activities[0].version).toBe(2);
  await assistant(page).click();
  await expect(assistant(page)).toHaveAttribute("aria-current", "page");
  await expect(
    page.getByTestId("current-plan-summary").filter({ visible: true }),
  ).toBeVisible();
  await page
    .getByRole("textbox", { name: "Message LifeLine", exact: true })
    .fill("Calculate the energy plan.");
  const sent = page.waitForRequest((r) => /\/agent$/.test(r.url()));
  await page.getByRole("button", { name: "Send message", exact: true }).click();
  expect((await sent).postDataJSON()).toEqual({
    expected_revision: after.revision,
    question: "Calculate the energy plan.",
  });
});

test("a revision conflict refreshes for review and never silently replays confirmation", async ({
  page,
  request,
}) => {
  const state = await seed(request);
  await open(page, state);
  await readyDraft(page);
  const current = await read(request, state.id);
  const external = await request.patch(
    `${apiBase}/${state.id}/proposals/${current.active_proposal_id}`,
    {
      data: {
        expected_revision: current.revision,
        details: { start_hour: 10 },
      },
    },
  );
  expect(external.ok()).toBe(true);
  await confirm(page);
  await expect(page.getByRole("alert")).toContainText(
    "shared plan changed elsewhere",
  );
  expect((await read(request, state.id)).confirmed_activities).toHaveLength(0);
  await expect(proposal(page)).toContainText("10:00–15:00");
  await confirm(page);
  expect((await read(request, state.id)).confirmed_activities).toHaveLength(1);
});

test("mobile and keyboard navigation keep controls readable and usable", async ({
  page,
  request,
}) => {
  await page.setViewportSize({ width: 375, height: 812 });
  await open(page, await seed(request));
  await overview(page).focus();
  await page.keyboard.press("Enter");
  await expect(
    page.getByRole("heading", { name: "Clinic Overview", exact: true }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Add activity manually", exact: true })
    .focus();
  await page.keyboard.press("Enter");
  await expect(
    proposal(page).getByLabel("Activity name", { exact: true }),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  const button = await proposal(page)
    .getByRole("button", { name: "Save draft for review", exact: true })
    .boundingBox();
  expect(button!.height).toBeGreaterThanOrEqual(44);
  await assistant(page).focus();
  await page.keyboard.press("Enter");
  await expect(
    page.getByRole("textbox", { name: "Message LifeLine", exact: true }),
  ).toBeVisible();
});

test("an expired server session requires an explicit new-session action", async ({
  page,
}) => {
  let creations = 0;
  page.on("request", (req) => {
    if (req.url().endsWith("/api/planning/sessions") && req.method() === "POST")
      creations++;
  });
  await page.addInitScript(() =>
    localStorage.setItem("lifeline.planning-session.v1", "expired-session"),
  );
  await page.goto("/");
  await expect(page.getByRole("alert")).toContainText(
    "previous local planning session is no longer available",
  );
  expect(creations).toBe(0);
  await page
    .getByRole("button", { name: "Start a new session", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Plan your clinic’s day.", exact: true }),
  ).toBeVisible();
  expect(creations).toBe(1);
});

test("manual operating hours reject half hours without truncating or submitting them", async ({
  page,
  request,
}) => {
  const state = await seed(request);
  await open(page, state);
  await overview(page).click();
  await expect(overview(page)).toHaveAttribute("aria-current", "page");
  await page
    .getByRole("button", { name: "Add activity manually", exact: true })
    .click();
  const card = proposal(page);
  await card
    .getByLabel("Activity name", { exact: true })
    .fill("Morning activity");
  const start = card.getByLabel("Start hour (0–23)", { exact: true });
  await start.fill("9.5");
  await card.getByLabel("Finish hour (1–24)", { exact: true }).fill("15");
  await card
    .getByRole("checkbox", { name: "Vaccine refrigerator", exact: true })
    .check();
  await card.getByRole("checkbox", { name: /I reviewed this list/ }).check();
  let patches = 0;
  page.on("request", (req) => {
    if (req.method() === "PATCH") patches++;
  });
  await card
    .getByRole("button", { name: "Save draft for review", exact: true })
    .click();
  expect(
    await start.evaluate((el: HTMLInputElement) => el.validity.stepMismatch),
  ).toBe(true);
  expect(patches).toBe(0);
  expect(
    (await read(request, state.id)).proposals[0].details.start_hour,
  ).toBeNull();
});
