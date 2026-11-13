import { test, expect, type Page } from "@playwright/test";

async function home(page: Page) {
  await page.goto("/");
  await expect(
    page.getByLabel("Choose a clinic", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "What does your clinic need?" }),
  ).toBeVisible();
}
async function ready(page: Page) {
  await expect(
    page.getByText("Plan calculated from current inputs.", { exact: true }),
  ).toBeVisible();
}
async function plan(page: Page) {
  const reply = page.waitForResponse(
    (r) => r.url().endsWith("/api/assistant") && r.status() === 200,
  );
  await page
    .getByRole("button", { name: "Plan tomorrow’s electricity", exact: true })
    .click();
  const data = await (await reply).json();
  await ready(page);
  return data;
}
async function say(page: Page, text: string) {
  const reply = page.waitForResponse((r) => r.url().endsWith("/api/assistant"));
  await page.locator("#clinic-question").fill(text);
  await page.getByRole("button", { name: /^(Make a plan|Continue)$/ }).click();
  return (await reply).json();
}

test("first-time clinic worker chooses a clinic, asks, understands, and changes a requirement", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await home(page);
  await expect(
    page.getByRole("button", { name: "Simple mode", exact: true }),
  ).toHaveAttribute("aria-pressed", "true");
  await expect(page.getByTestId("simple-plan")).toHaveCount(0);
  await expect(
    page.getByLabel("Solar capacity (kW)", { exact: true }),
  ).toHaveCount(0);
  await page
    .getByLabel("Choose a clinic", { exact: true })
    .selectOption("normal");
  await expect(
    page.getByRole("heading", {
      name: "Kisumu larger-system example",
      exact: true,
    }),
  ).toBeVisible();
  const first = await say(page, "Will we have enough electricity tomorrow?");
  await ready(page);
  await expect(
    page.getByRole("heading", {
      name: "Essential equipment has enough power in this model",
      exact: true,
    }),
  ).toBeVisible();
  await expect(page.locator(".plan-actions li")).toHaveCount(3);
  await expect(
    page.getByRole("heading", { name: "When to run equipment", exact: true }),
  ).toBeVisible();
  await expect(page.locator(".plan-limitation")).toContainText(
    "live forecast is unavailable",
  );
  await expect(
    page.getByRole("button", {
      name: "Exact measurements and warnings",
      exact: true,
    }),
  ).toHaveAttribute("aria-expanded", "false");
  await page
    .getByRole("button", { name: "Change a requirement", exact: true })
    .click();
  const update = page.waitForResponse(
    (r) =>
      r.url().endsWith("/api/simulate") &&
      r
        .request()
        .postDataJSON()
        ?.equipment?.some(
          (e: { id: string; required_energy_kwh: number }) =>
            e.id === "device_charging" && e.required_energy_kwh === 1.5,
        ),
  );
  await page.getByLabel("Required equipment hours", { exact: true }).fill("5");
  await expect(page.getByTestId("simple-plan")).toHaveCount(0);
  const next = await (await update).json();
  await ready(page);
  expect(next.optimized.metrics.flexible_requested_kwh).toBeGreaterThan(
    first.result.optimized.metrics.flexible_requested_kwh,
  );
  await expect(page.getByTestId("simple-plan")).toBeVisible();
  await page
    .getByRole("button", {
      name: "Exact measurements and warnings",
      exact: true,
    })
    .click();
  await expect(page.locator(".exact-measurements")).toContainText(
    next.optimized.metrics.final_soc_kwh.toLocaleString("en-US", {
      minimumFractionDigits: 3,
      maximumFractionDigits: 3,
    }),
  );
  expect(errors).toEqual([]);
});

test("essential shortage has explicit hours, missing energy, and no healthy claim", async ({
  page,
}) => {
  await home(page);
  await page
    .getByLabel("Choose a clinic", { exact: true })
    .selectOption("high_demand");
  const response = await plan(page);
  expect(response.result.status).toBe("CRITICAL_SHORTAGE");
  await expect(page.locator(".simple-assessment")).toContainText(
    "There isn’t enough power for all essential equipment",
  );
  await expect(page.locator(".plan-limitation")).toContainText("20:00–22:00");
  await expect(page.locator(".plan-limitation")).toContainText("1.320 kWh");
  await expect(page.locator(".plan-actions")).toContainText("output limit");
  await expect(page.locator(".unfinished").first()).toBeVisible();
});

test("sterilization request asks focused questions, then uses real fixed-hour checks", async ({
  page,
}) => {
  await home(page);
  const first = await say(
    page,
    "We need to sterilize equipment before noon. When should we do it?",
  );
  expect(first.result).toBeNull();
  await expect(page.locator(".question-label")).toContainText(
    "rated power in watts",
  );
  await expect(
    page.getByLabel("Solar capacity (kW)", { exact: true }),
  ).toHaveCount(0);
  await expect(page.locator("#clinic-question")).toBeFocused();
  const second = await say(page, "1200 watts");
  expect(second.result).toBeNull();
  await expect(page.locator(".question-label")).toContainText(
    "How many whole hours",
  );
  const third = await say(page, "2 hours");
  expect(third.result).toBeNull();
  await expect(page.locator(".question-label")).toContainText("earliest hour");
  const final = await say(page, "08:00");
  await ready(page);
  const sterilizer = final.result.equipment.at(-1);
  expect(sterilizer.category).toBe("critical");
  expect(sterilizer.required_hours.every((h: number) => h < 12)).toBe(true);
  await expect(
    page.locator(".equipment-plan-row").filter({ hasText: "Sterilizer" }),
  ).toContainText("Essential · fixed hours");
  await expect(page.locator(".cycle-note")).toContainText(
    "does not validate medical appliance cycles",
  );
});

test("cloudier weather preserves equipment and starting battery and reports unfinished work", async ({
  page,
}) => {
  await home(page);
  const before = await plan(page);
  const update = page.waitForResponse((r) =>
    r.url().endsWith("/api/assistant"),
  );
  await page
    .getByRole("button", { name: "Prepare for cloudy weather", exact: true })
    .click();
  const after = await (await update).json();
  await ready(page);
  expect(after.result.effective_config).toEqual(before.result.effective_config);
  expect(after.result.equipment).toEqual(before.result.equipment);
  expect(after.result.optimized.metrics.total_solar_kwh).toBeCloseTo(
    before.result.optimized.metrics.total_solar_kwh / 4,
    6,
  );
  await expect(page.locator(".simple-plan")).toContainText("Unfinished:");
});

test("battery requirement change reveals newly unmet essential needs and clears the old assessment", async ({
  page,
}) => {
  await home(page);
  await plan(page);
  await page
    .getByRole("button", { name: "Change a requirement", exact: true })
    .click();
  const update = page.waitForResponse(
    (r) =>
      r.url().endsWith("/api/simulate") &&
      r.request().postDataJSON()?.initial_battery_kwh === 0,
  );
  await page
    .getByLabel("Starting battery charge (%)", { exact: true })
    .fill("0");
  await expect(page.getByTestId("simple-plan")).toHaveCount(0);
  expect((await (await update).json()).status).toBe("CRITICAL_SHORTAGE");
  await ready(page);
  await expect(page.locator(".simple-assessment")).toContainText(
    "There isn’t enough power",
  );
  await expect(page.locator(".conversation")).toHaveCount(0);
});

test("detailed mode preserves custom equipment, all three schedules, and computed comparisons", async ({
  page,
}) => {
  await home(page);
  await plan(page);
  await page
    .getByRole("button", { name: "Explore detailed results", exact: true })
    .click();
  await expect(page.getByTestId("battery-preserved")).toContainText("2.211");
  await expect(page.getByTestId("capacity-outcome")).toBeVisible();
  await page
    .getByRole("button", { name: "Add equipment", exact: true })
    .click();
  const row = page
    .locator(".equipment-editor")
    .filter({
      has: page.locator(".equipment-toggle strong", {
        hasText: "New equipment",
      }),
    });
  await row.locator(".equipment-toggle").click();
  await row
    .locator("label")
    .filter({ hasText: /^Name$/ })
    .locator("input")
    .fill("Custom field pump");
  await page
    .getByLabel("Power Custom field pump", { exact: true })
    .fill("470.5");
  await page
    .getByLabel("Duration Custom field pump", { exact: true })
    .fill("2.3");
  const hour = page.getByRole("checkbox", {
    name: "Custom field pump hour 8",
    exact: true,
  });
  await hour.focus();
  await page.keyboard.press("Space");
  await expect(hour).not.toBeChecked();
  await ready(page);
  await expect(
    page
      .locator(".task-group")
      .filter({
        has: page.getByRole("heading", {
          name: "Custom field pump",
          exact: true,
        }),
      }),
  ).toContainText("1.082");
  await expect(page.locator(".comparison-card")).toContainText(
    "Sunshine-first",
  );
  await page
    .getByRole("button", { name: "Remove Custom field pump", exact: true })
    .click();
  await ready(page);
  await expect(page.locator(".task-group")).toHaveCount(2);
});

test("capacity alternatives distinguish output limits from stored battery capacity", async ({
  page,
}) => {
  await home(page);
  await page
    .getByLabel("Choose a clinic", { exact: true })
    .selectOption("high_demand");
  await plan(page);
  await page
    .getByRole("button", { name: "Explore detailed results", exact: true })
    .click();
  await expect(page.getByTestId("capacity-outcome")).toBeVisible();
  await page.getByLabel("Proposed battery (kWh)", { exact: true }).fill("40");
  await expect(page.locator(".explorer-result strong").first()).toContainText(
    "1.320 → 1.320",
  );
  await page
    .getByLabel("Proposed output limit (kW)", { exact: true })
    .fill("6");
  await expect(page.locator(".explorer-result strong").first()).toContainText(
    "1.320 → 0.000",
  );
});

test("historical source is explicit, invalid requirements hide stale results, and reset works", async ({
  page,
}) => {
  await home(page);
  await plan(page);
  await page
    .getByLabel("Weather for this plan", { exact: true })
    .selectOption("kisumu-2025-01-14");
  await ready(page);
  await expect(page.locator(".weather-context")).toContainText("NASA POWER");
  await expect(page.locator(".simple-plan .plan-heading")).toContainText(
    "Historical example",
  );
  await page
    .getByRole("button", { name: "Advanced settings", exact: true })
    .click();
  await page.getByLabel("Battery capacity (kWh)", { exact: true }).fill("1");
  await expect(page.locator(".planning-state")).toContainText(
    "Please correct the requirements",
  );
  await expect(
    page.getByRole("button", { name: "Recalculate plan", exact: true }),
  ).toBeDisabled();
  await page
    .getByRole("button", { name: "Reset example", exact: true })
    .click();
  await ready(page);
  await expect(
    page.getByLabel("Battery capacity (kWh)", { exact: true }),
  ).toHaveValue("8");
  await page.getByRole("button", { name: "Simple mode", exact: true }).click();
  await expect(page.locator(".simple-plan .plan-heading")).toContainText(
    "Demonstration day",
  );
});

test("mobile page has no overflow, touch targets and keyboard views work", async ({
  page,
}) => {
  await page.setViewportSize({ width: 375, height: 812 });
  await home(page);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  const targets = page.locator(".planning-action");
  for (const target of await targets.all())
    expect((await target.boundingBox())!.height).toBeGreaterThanOrEqual(44);
  await targets.first().focus();
  await page.keyboard.press("Enter");
  await ready(page);
  await expect(page.getByTestId("simple-plan")).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  const advanced = page.getByRole("button", {
    name: "Advanced settings",
    exact: true,
  });
  await advanced.focus();
  await page.keyboard.press("Enter");
  await expect(advanced).toHaveAttribute("aria-pressed", "true");
  const slider = page.getByRole("slider", {
    name: "Available sunshine",
    exact: true,
  });
  await slider.focus();
  await page.keyboard.press("ArrowLeft");
  await expect(slider).toHaveAttribute("aria-valuenow", "95");
  await ready(page);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
});

test("assistant failure offers deterministic planning without a canned result", async ({
  page,
}) => {
  await page.route("**/api/assistant", (route) =>
    route.fulfill({
      status: 503,
      contentType: "application/json",
      body: JSON.stringify({
        error: {
          code: "SOLVER_UNAVAILABLE",
          message: "Assistant unavailable for test",
          details: [],
        },
      }),
    }),
  );
  await home(page);
  await page
    .getByRole("button", { name: "Plan tomorrow’s electricity", exact: true })
    .click();
  await expect(page.locator(".planner-error")).toContainText(
    "Assistant unavailable for test",
  );
  await expect(page.getByTestId("simple-plan")).toHaveCount(0);
  await page
    .getByRole("button", { name: "Retry with local planner", exact: true })
    .click();
  await ready(page);
  await expect(page.getByTestId("simple-plan")).toBeVisible();
});

test("initial failure can be retried and forecast failure is visibly unavailable", async ({
  page,
}) => {
  await page.route("**/api/scenarios", (route) => route.abort());
  await page.route("**/api/planning-status", (route) => route.abort());
  await page.goto("/");
  await expect(page.locator(".planner-error")).toContainText(
    "clinic examples could not be loaded",
  );
  await expect(page.getByTestId("simple-plan")).toHaveCount(0);
  await page.unroute("**/api/scenarios");
  await page.getByRole("button", { name: "Retry", exact: true }).click();
  await expect(page.locator(".weather-context")).toContainText(
    "Forecast availability could not be checked",
  );
  await plan(page);
});

test("bundled historical weather and local conversation work with external requests blocked", async ({
  page,
}) => {
  await page.route("**/*", (route) =>
    new URL(route.request().url()).hostname === "127.0.0.1"
      ? route.continue()
      : route.abort(),
  );
  await home(page);
  await page
    .getByLabel("Weather for this plan", { exact: true })
    .selectOption("kisumu-2025-01-14");
  const response = await say(page, "Will we have enough electricity tomorrow?");
  await ready(page);
  expect(response.mode).toBe("offline");
  expect(response.result.weather_dataset).toBe("kisumu-2025-01-14");
  await page
    .getByRole("button", { name: "Forecast details", exact: true })
    .click();
  await expect(page.locator(".weather-context")).toContainText(
    "Last forecast update: unavailable",
  );
  await expect(page.locator(".planner-error")).toHaveCount(0);
});

test("built application and API share one local server", async ({ page }) => {
  await page.goto(
    `http://127.0.0.1:${process.env.LIFELINE_API_PORT ?? "8000"}/`,
  );
  await expect(
    page.getByRole("heading", { name: "What does your clinic need?" }),
  ).toBeVisible();
  await plan(page);
  await expect(page.locator(".simple-assessment")).toContainText(
    "enough power in this model",
  );
});
