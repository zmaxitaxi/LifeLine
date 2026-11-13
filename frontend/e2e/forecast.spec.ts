import { execFileSync } from "node:child_process";
import { resolve } from "node:path";
import { test, expect, type Page } from "@playwright/test";

/** Test fixtures contain injected radiation; every plan is computed by Python. */
function fixture(path: string, body?: unknown) {
  return JSON.parse(
    execFileSync(
      resolve("../.venv/bin/python"),
      ["backend/tests/forecast_browser_fixture.py"],
      {
        cwd: resolve(".."),
        input: JSON.stringify({
          path,
          body,
          method: body === undefined ? "GET" : "POST",
        }),
        encoding: "utf8",
      },
    ),
  );
}
async function openWeather(page: Page) {
  await page.goto("/");
  await page
    .getByRole("button", {
      name: "Live weather forecast and tomorrow’s plan",
      exact: true,
    })
    .click();
  const panel = page.locator("#live-forecast");
  await expect(
    panel.getByLabel("Clinic latitude", { exact: true }),
  ).toHaveValue("-0.0917");
  return panel;
}
async function mockPlans(page: Page) {
  await page.route("**/api/planner/ask", async (route) => {
    const response = fixture(
      "/api/planner/ask",
      route.request().postDataJSON(),
    );
    await route.fulfill({ status: response.status, json: response.body });
  });
}

test("forecast tool flow computes a schedule, uncertainty and honest shortage warning", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await mockPlans(page);
  const panel = await openWeather(page);
  await panel
    .getByRole("checkbox", {
      name: "Confirm midnight battery assumption",
      exact: true,
    })
    .check();
  await panel
    .getByRole("button", {
      name: "Calculate forecast-backed plan",
      exact: true,
    })
    .click();
  await expect(panel.getByTestId("forecast-plan-result")).toBeVisible();
  await expect(panel.getByTestId("forecast-provenance").first()).toContainText(
    "Africa/Nairobi",
  );
  await expect(panel.getByTestId("forecast-provenance").first()).toContainText(
    "2026-11-14",
  );
  await expect(
    panel.getByRole("table", { name: "Forecast uncertainty comparison" }),
  ).toContainText("50% lower sunshine");
  await expect(panel).toContainText("not an LLM agent");
  await panel
    .getByLabel("Assumed battery energy at local midnight (kWh)", {
      exact: true,
    })
    .fill("0");
  await expect(panel.getByTestId("forecast-plan-result")).toHaveCount(0);
  await panel
    .getByRole("checkbox", {
      name: "Confirm midnight battery assumption",
      exact: true,
    })
    .check();
  await panel
    .getByRole("button", {
      name: "Calculate forecast-backed plan",
      exact: true,
    })
    .click();
  await expect(panel.getByTestId("forecast-plan-result")).toContainText(
    "cannot supply all essential equipment",
  );
  expect(errors).toEqual([]);
});

test("forecast failures and invalid coordinates never display invented results", async ({
  page,
}) => {
  await page.route("**/api/forecast?**", (route) =>
    route.fulfill({
      status: 503,
      json: {
        error: {
          code: "FORECAST_UNAVAILABLE",
          message: "Weather provider unavailable for this test.",
          details: [],
        },
      },
    }),
  );
  const panel = await openWeather(page);
  await panel
    .getByRole("button", {
      name: "Fetch today and tomorrow’s forecast",
      exact: true,
    })
    .click();
  await expect(panel.getByRole("alert")).toContainText(
    "Weather provider unavailable",
  );
  await expect(panel.getByTestId("forecast-plan-result")).toHaveCount(0);
  await expect(panel).toContainText(
    "Historical NASA and synthetic examples remain available",
  );
  await panel.getByLabel("Clinic latitude", { exact: true }).fill("91");
  await panel
    .getByRole("button", {
      name: "Fetch today and tomorrow’s forecast",
      exact: true,
    })
    .click();
  await expect(panel.getByRole("alert")).toContainText(
    "latitude from −90 to 90",
  );
});

test("mobile forecast controls work with keyboard and contain wide uncertainty table", async ({
  page,
}) => {
  await page.setViewportSize({ width: 375, height: 812 });
  await mockPlans(page);
  const panel = await openWeather(page);
  const reviewed = panel.getByRole("checkbox", {
    name: "Confirm midnight battery assumption",
    exact: true,
  });
  await reviewed.focus();
  await page.keyboard.press("Space");
  await expect(reviewed).toBeChecked();
  await panel
    .getByRole("button", {
      name: "Calculate forecast-backed plan",
      exact: true,
    })
    .focus();
  await page.keyboard.press("Enter");
  await expect(panel.getByTestId("forecast-plan-result")).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
});

test("the main question opens live planning and returns a computed forecast answer", async ({
  page,
}) => {
  await mockPlans(page);
  await page.goto("/");
  await page
    .getByLabel("Describe your clinic’s situation", { exact: true })
    .fill("Can our clinic safely operate tomorrow given the weather forecast?");
  await page.getByRole("button", { name: "Make a plan", exact: true }).click();
  const panel = page.locator("#live-forecast");
  await expect(panel).toBeVisible();
  await expect(
    panel.getByLabel("Ask about tomorrow’s weather", { exact: true }),
  ).toHaveValue(
    "Can our clinic safely operate tomorrow given the weather forecast?",
  );
  await panel
    .getByRole("checkbox", {
      name: "Confirm midnight battery assumption",
      exact: true,
    })
    .check();
  await panel
    .getByRole("button", {
      name: "Calculate forecast-backed plan",
      exact: true,
    })
    .click();
  await expect(panel.getByTestId("forecast-plan-result")).toBeVisible();
  await expect(
    page.getByRole("log", { name: "Conversation with LifeLine" }),
  ).toContainText("weather source: Open-Meteo Forecast API");
  await page.getByLabel('Describe your clinic’s situation',{exact:true}).fill("What happens if tomorrow's sunshine is 50% lower?");
  await page.getByRole('button',{name:'Make a plan',exact:true}).click();
  await expect(panel.getByLabel('Ask about tomorrow’s weather',{exact:true})).toHaveValue("What happens if tomorrow's sunshine is 50% lower?");
  await panel.getByRole('button',{name:'Calculate forecast-backed plan',exact:true}).click();
  await expect(page.getByRole('log',{name:'Conversation with LifeLine'})).toContainText('For 50% lower sunshine');
});
