import { test, expect } from "@playwright/test";
async function ready(page: import("@playwright/test").Page) {
  await expect(
    page.getByText("Plan calculated from current inputs.", { exact: true }),
  ).toBeVisible();
  await expect(page.getByTestId("capacity-outcome")).toBeVisible();
}
test("configure unfamiliar equipment, compare schedules, remove equipment and test weather", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/");
  await ready(page);
  await expect(page.getByTestId("battery-preserved")).toContainText("2.211");
  await expect(page.locator('[data-slot="slider-track"]')).toBeVisible();
  await expect(page.getByRole("button", { name: "Configure clinic", exact: true })).not.toBeVisible();
  await expect(page.locator(".recommendation-row")).toHaveCount(2);
  const detailed = page.getByRole("button", { name: /Detailed analysis/ });
  await expect(detailed).toHaveAttribute("aria-expanded", "false");
  await expect(
    page.getByLabel("Charge limit (kW)", { exact: true }),
  ).not.toBeVisible();
  await expect(
    page.getByText("Sunshine-first matches the optimizer’s key metrics here.", {
      exact: true,
    }),
  ).toBeVisible();
  await detailed.focus();
  await page.keyboard.press("Enter");
  await expect(
    page.getByText("Sunshine-first matches LifeLine’s key metrics here.", {
      exact: false,
    }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Add equipment", exact: true })
    .click();
  const row = page.locator(".equipment-editor").filter({
    has: page.locator(".equipment-toggle strong", { hasText: "New equipment" }),
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
  const allowedHour = page.getByRole("checkbox", {
    name: "Custom field pump hour 8",
    exact: true,
  });
  await expect(allowedHour).toBeChecked();
  await allowedHour.focus();
  await page.keyboard.press("Space");
  await expect(allowedHour).not.toBeChecked();
  await ready(page);
  await expect(
    page.locator(".task-group").filter({
      has: page.getByRole("heading", {
        name: "Custom field pump",
        exact: true,
      }),
    }),
  ).toContainText("1.082");
  await page
    .getByRole("button", { name: "Remove Custom field pump", exact: true })
    .click();
  await ready(page);
  await expect(page.locator(".task-group")).toHaveCount(2);
  const update = page.waitForResponse(
    (r) =>
      r.url().endsWith("/api/simulate") &&
      r.request().postDataJSON()?.cloud_factors?.[0] === 0.25,
  );
  await page
    .getByRole("button", { name: "Test 25% sunshine", exact: true })
    .click();
  const response = await (await update).json();
  expect(response.optimized.metrics.total_solar_kwh).toBeLessThan(3);
  await ready(page);
  await expect(
    page.getByText("Work completion differs", { exact: true }),
  ).toBeVisible();
  await expect(page.locator(".hero-result")).toContainText(
    "This is not a same-work improvement.",
  );
  expect(errors).toEqual([]);
});
test("capacity explorer distinguishes power limits from battery capacity", async ({
  page,
}) => {
  await page.goto("/");
  await ready(page);
  await page
    .getByLabel("Quick-start example", { exact: true })
    .selectOption("high_demand");
  await ready(page);
  await expect(page.locator(".assessment")).toContainText(
    "Critical energy shortage",
  );
  await expect(page.locator(".hero-result")).toContainText(
    "Critical energy still unserved",
  );
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
test("historical dataset, validation, reset and no stale scenario result", async ({
  page,
}) => {
  await page.goto("/");
  await ready(page);
  await page
    .getByLabel("Representative weather", { exact: true })
    .selectOption("kisumu-2025-01-14");
  await ready(page);
  await expect(page.locator(".sources")).toContainText(
    "NASA POWER historical satellite-derived irradiance",
  );
  await page.getByLabel("Battery capacity (kWh)", { exact: true }).fill("1");
  await expect(page.getByRole("alert")).toContainText("initial_battery_kwh");
  await page
    .getByRole("button", { name: "Reset selected quick start", exact: true })
    .click();
  await ready(page);
  await expect(
    page.getByLabel("Battery capacity (kWh)", { exact: true }),
  ).toHaveValue("8");
  await page
    .getByLabel("Quick-start example", { exact: true })
    .selectOption("storm");
  await page
    .getByLabel("Quick-start example", { exact: true })
    .selectOption("normal");
  await ready(page);
  await expect(
    page.getByLabel("Current charge (kWh)", { exact: true }),
  ).toHaveValue("14");
  await expect(page.locator(".assessment")).toContainText(
    "Within modeled limits",
  );
});
test("mobile layout stays within viewport and keyboard controls work", async ({
  page,
}) => {
  await page.setViewportSize({ width: 375, height: 812 });
  await page.goto("/");
  await ready(page);
  await expect(page.getByTestId("battery-preserved")).toBeInViewport();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  const configure = page.getByRole("button", {
    name: "Configure clinic",
    exact: true,
  });
  await configure.focus();
  await page.keyboard.press("Enter");
  await expect(configure).toHaveAttribute("aria-expanded", "true");
  const sunshine = page.getByRole("slider", { name: "Available sunshine", exact: true });
  await sunshine.focus();
  await page.keyboard.press("ArrowLeft");
  await expect(sunshine).toHaveAttribute("aria-valuenow", "95");
  await ready(page);
  await page
    .getByRole("button", { name: "Test 25% sunshine", exact: true })
    .focus();
  await page.keyboard.press("Enter");
  await ready(page);
  await expect(
    page.getByLabel("Available sunshine", { exact: true }),
  ).toHaveValue("25");
});
test("backend failure shows retry and does not create healthy results", async ({
  page,
}) => {
  await page.route("**/api/scenarios", (route) =>
    route.fulfill({
      status: 503,
      contentType: "application/json",
      body: JSON.stringify({
        error: {
          code: "SOLVER_UNAVAILABLE",
          message: "Unavailable for test",
          details: [],
        },
      }),
    }),
  );
  await page.goto("/");
  await expect(page.getByRole("alert")).toContainText(
    "Cannot reach the local API",
  );
  await expect(page.getByTestId("battery-preserved")).toHaveCount(0);
  await page.unroute("**/api/scenarios");
  await page.getByRole("button", { name: "Retry", exact: true }).click();
  await ready(page);
});

test("offline bundled assets and historical weather need no external requests", async ({
  page,
}) => {
  await page.route("**/*", (route) =>
    new URL(route.request().url()).hostname === "127.0.0.1"
      ? route.continue()
      : route.abort(),
  );
  await page.goto("/");
  await ready(page);
  await page
    .getByLabel("Representative weather", { exact: true })
    .selectOption("kisumu-2025-01-14");
  await ready(page);
  await expect(page.locator(".sources")).toContainText("NASA POWER historical");
  await expect(page.getByRole("alert")).toHaveCount(0);
});

test("production build is served with the API from one local server", async ({
  page,
}) => {
  await page.goto("http://127.0.0.1:8000/");
  await ready(page);
  await expect(page.getByTestId("battery-preserved")).toContainText("2.211");
});
