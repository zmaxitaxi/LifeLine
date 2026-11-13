import { test, expect } from "@playwright/test";
import { tmpdir } from "node:os";
import { join } from "node:path";
import {
  calculate,
  initial,
  open,
  seed,
  weatherFailure,
  readyDraft,
  confirm,
  read,
  overview,
  proposal,
} from "./support/planning";
test.beforeEach(() => weatherFailure(false));
test.afterEach(() => weatherFailure(false));

test("hourly battery values and percentages match backend outputs for different capacities", async ({
  page,
  request,
}) => {
  const state = await calculate(request, await seed(request));
  await open(page, state);
  await page.getByRole("button", { name: "Explore plan", exact: true }).click();
  const battery = state.computed_plan!.recovery!.options.find(
    (o) => o.kind === "battery",
  )!;
  await page
    .getByRole("combobox", { name: "Calculated recovery option", exact: true })
    .selectOption(battery.id);
  await expect(
    page.getByRole("textbox", { name: "Message LifeLine", exact: true }),
  ).toBeHidden();
  await page.getByRole("button", { name: "Compare", exact: true }).click();
  const slider = page.getByRole("slider", {
    name: "Simulation time",
    exact: true,
  });
  await slider.focus();
  await slider.press("Home");
  for (let hour = 0; hour <= 24; hour++) {
    if (hour) await slider.press("ArrowRight");
    await expect(
      page.getByLabel("Selected simulation time", { exact: true }),
    ).toHaveText(`${String(hour).padStart(2, "0")}:00`);
    for (const [id, plan, config] of [
      [
        "existing-battery",
        state.computed_plan!.simulation.baseline,
        state.computed_plan!.simulation.effective_config,
      ],
      ["optimized-battery", battery.plan, battery.config],
    ] as const) {
      const element = page.getByTestId(id);
      const energy =
        hour === 24
          ? plan.hourly[23].soc_end_kwh
          : plan.hourly[hour].soc_start_kwh;
      expect(Number(await element.getAttribute("data-energy-kwh"))).toBeCloseTo(
        energy,
        8,
      );
      expect(Number(await element.getAttribute("data-percentage"))).toBeCloseTo(
        (energy / config.battery_capacity_kwh) * 100,
        8,
      );
      expect(
        await element
          .locator(".battery-warning")
          .filter({ hasText: "Below reserve" })
          .count(),
      ).toBe(energy < config.reserve_kwh - 1e-6 ? 1 : 0);
    }
  }
  await slider.press("Home");
  expect(
    await page.getByTestId("existing-battery").getAttribute("data-energy-kwh"),
  ).toBe(
    await page.getByTestId("optimized-battery").getAttribute("data-energy-kwh"),
  );
  expect(battery.config.battery_capacity_kwh).toBeGreaterThan(
    state.computed_plan!.simulation.effective_config.battery_capacity_kwh,
  );
  await page
    .getByRole("button", { name: "Play battery playback", exact: true })
    .click();
  await expect(
    page.getByLabel("Selected simulation time", { exact: true }),
  ).not.toHaveText("00:00");
  await page
    .getByRole("button", { name: "Pause battery playback", exact: true })
    .click();
  const paused = await slider.getAttribute("aria-valuenow");
  await page.waitForTimeout(350);
  await expect(slider).toHaveAttribute("aria-valuenow", paused!);
  await page
    .getByRole("button", { name: "Calculate plan", exact: true })
    .click();
  await expect(page.getByTestId("battery-playback")).toHaveCount(0);
  await expect(page.getByTestId("battery-playback")).toBeVisible();
  await expect(
    page.getByLabel("Selected simulation time", { exact: true }),
  ).toHaveText("00:00");
});

test("failed confirmation calculation saves the activity and clears every stale result", async ({
  page,
  request,
}) => {
  const state = await calculate(request, await seed(request));
  await open(page, state);
  await readyDraft(page);
  const before = await read(request, state.id);
  expect(before.computed_plan).not.toBeNull();
  weatherFailure(true);
  await page.route("**/proposals/*/confirm", async (route) => {
    await new Promise((resolve) => setTimeout(resolve, 700));
    await route.continue();
  });
  const response = page.waitForResponse((r) => /\/confirm$/.test(r.url()));
  await proposal(page)
    .getByRole("button", { name: "Confirm", exact: true })
    .click();
  await expect(page.getByTestId("current-plan-summary")).toHaveCount(0);
  await expect(page.getByTestId("battery-playback")).toHaveCount(0);
  await response;
  await expect(page.getByRole("alert")).toContainText("No current energy plan");
  const failed = await read(request, state.id);
  expect(failed.confirmed_activities).toHaveLength(1);
  expect(failed.computed_plan).toBeNull();
  await overview(page).click();
  await expect(overview(page)).toHaveAttribute("aria-current", "page");
  await expect(page.getByTestId("confirmed-activity")).toContainText(
    "vaccination campaign",
  );
  await expect(page.getByTestId("battery-playback")).toHaveCount(0);
  weatherFailure(false);
  await page
    .getByRole("button", { name: "Retry energy calculation", exact: true })
    .click();
  await expect(page.getByTestId("battery-playback")).toBeVisible();
});

test("weather errors are explicit while draft editing remains available", async ({
  page,
  request,
}) => {
  const state = await seed(request);
  weatherFailure(true);
  await open(page, state);
  await overview(page).click();
  await expect(overview(page)).toHaveAttribute("aria-current", "page");
  await expect(page.getByRole("alert")).toContainText(
    "Live weather is unavailable",
  );
  await expect(page.getByTestId("battery-playback")).toHaveCount(0);
  await page
    .getByRole("button", { name: "Add activity manually", exact: true })
    .click();
  await expect(
    proposal(page).getByLabel("Activity name", { exact: true }),
  ).toBeEditable();
  weatherFailure(false);
  await page
    .getByRole("button", { name: "Retry weather", exact: true })
    .click();
  await expect(
    page.getByRole("button", {
      name: "Hourly solar generation estimates",
      exact: true,
    }),
  ).toBeVisible();
});

test("empty starting energy reveals essential shortages independently of reserve and respects reduced motion", async ({
  page,
  request,
}) => {
  const state = await calculate(
    request,
    await seed(request, { midnight_battery_kwh: 0 }),
  );
  expect(
    state.computed_plan!.simulation.baseline.metrics.critical_unserved_kwh,
  ).toBeGreaterThan(0);
  await page.emulateMedia({ reducedMotion: "reduce" });
  await open(page, state);
  await expect(
    page.getByTestId("current-plan-summary").filter({ visible: true }),
  ).toContainText("not enough electricity for all essential equipment");
  await overview(page).click();
  await expect(overview(page)).toHaveAttribute("aria-current", "page");
  await page.getByRole("button", { name: "Compare", exact: true }).click();
  await expect(page.getByTestId("existing-battery")).toContainText(
    "Essential equipment is short",
  );
  const transitions = await page
    .locator(".battery-fill")
    .evaluateAll((els) =>
      els.map((el) => getComputedStyle(el).transitionDuration),
    );
  expect(transitions.every((value) => value === "0s")).toBe(true);
});

test("mobile overview shows a compact comparison and keyboard-accessible timeline", async ({
  page,
  request,
}) => {
  await page.setViewportSize({ width: 375, height: 812 });
  await open(page, await calculate(request, await seed(request)));
  await overview(page).click();
  await expect(overview(page)).toHaveAttribute("aria-current", "page");
  await page.getByRole("button", { name: "Compare", exact: true }).focus();
  await page.keyboard.press("Space");
  const slider = page.getByRole("slider", {
    name: "Simulation time",
    exact: true,
  });
  await slider.focus();
  await slider.press("End");
  await expect(
    page.getByLabel("Selected simulation time", { exact: true }),
  ).toHaveText("24:00");
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  const image = await page
    .getByTestId("existing-battery")
    .locator('svg[role="img"]')
    .boundingBox();
  expect(image!.height).toBeLessThanOrEqual(120);
  await page.getByTestId("battery-playback").evaluate((el) => {
    const root = el.closest(".overview-page")!;
    root.scrollTop +=
      el.getBoundingClientRect().top - root.getBoundingClientRect().top - 12;
  });
  await page.screenshot({
    path: join(tmpdir(), "lifeline-two-page-overview-mobile.png"),
  });
});

test("a result with an old input revision is never rendered as the current plan", async ({
  page,
  request,
}) => {
  const state = await calculate(request, await seed(request));
  const mismatched = structuredClone(state);
  mismatched.input_revision = state.computed_plan!.input_revision + 1;
  await page.route(`**/api/planning/sessions/${state.id}`, (route) =>
    route.fulfill({ json: mismatched }),
  );
  await open(page, state);
  await overview(page).click();
  await expect(overview(page)).toHaveAttribute("aria-current", "page");
  await expect(page.getByTestId("battery-playback")).toHaveCount(0);
  await expect(page.getByTestId("current-plan-summary")).toHaveCount(0);
  await expect(
    page.getByRole("region", { name: "Battery & Energy", exact: true }),
  ).toContainText("No current verified battery forecast");
});

test("assistant recommendations use the recommended scenario’s completed work, not the original plan", async ({
  page,
  request,
}) => {
  const base = initial();
  const state = await calculate(
    request,
    await seed(request, { clinic: { ...base.clinic, pv_capacity_kw: 0.15 } }),
  );
  const recovery = state.computed_plan!.recovery!;
  const recommended = recovery.options.find(
    (option) => option.id === recovery.recommended_option_id,
  )!;
  expect(recommended.kind).toBe("solar");
  expect(recommended.plan.metrics.flexible_served_kwh).toBeGreaterThan(
    state.computed_plan!.simulation.optimized.metrics.flexible_served_kwh,
  );
  await open(page, state);
  const summary = page
    .getByTestId("current-plan-summary")
    .filter({ visible: true });
  await expect(summary).toContainText(
    `Lowest stored energy: ${recommended.plan.metrics.min_soc_kwh.toFixed(3)} kWh`,
  );
  const pump = recommended.plan.flexible_tasks.find(
    (task) => task.task_id === "pump",
  )!;
  await expect(summary.locator(".assistant-plan-actions")).toContainText(
    `${pump.served_kwh.toFixed(3)} kWh modeled`,
  );
});
