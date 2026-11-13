import { execFileSync } from "node:child_process";
import { resolve } from "node:path";
import { test, expect, type Page } from "@playwright/test";

async function available(page: Page) {
  await page.route("**/api/agent/status", (route) =>
    route.fulfill({
      json: {
        available: true,
        mode: "local_tool_agent",
        model: "llama3.1:8b",
        provider: "Ollama on localhost",
        cloud_ai: false,
        note: "Synthetic browser-test provider",
      },
    }),
  );
}
async function mockAgent(
  page: Page,
  tool = "plan_forecast",
  args: object = { day: "tomorrow" },
  failure?: number,
) {
  await page.route("**/api/agent/ask", (route) => {
    const result = JSON.parse(
      execFileSync(
        resolve("../.venv/bin/python"),
        ["backend/tests/agent_browser_fixture.py"],
        {
          cwd: resolve(".."),
          input: JSON.stringify({
            body: route.request().postDataJSON(),
            tool,
            arguments: args,
            failure,
          }),
          encoding: "utf8",
        },
      ),
    );
    return route.fulfill({ status: result.status, json: result.body });
  });
}
async function panel(page: Page) {
  await available(page);
  await page.goto("/");
  await page
    .locator("#clinic-question")
    .fill(
      "We expect cloudy weather tomorrow. Will we have enough electricity?",
    );
  await page.getByRole("button", { name: "Make a plan", exact: true }).click();
  const panel = page.locator("#live-forecast");
  await expect(
    panel.getByLabel("Planning assistant", { exact: true }),
  ).toHaveValue("local");
  await panel
    .getByRole("checkbox", {
      name: "Confirm midnight battery assumption",
      exact: true,
    })
    .check();
  return panel;
}

test("local AI selection returns a computed forecast schedule and visible safeguards", async ({
  page,
}) => {
  await mockAgent(page);
  const p = await panel(page);
  await p
    .getByRole("button", {
      name: "Calculate forecast-backed plan",
      exact: true,
    })
    .click();
  await expect(p.getByTestId("agent-answer")).toContainText(
    "Local AI tool selection: llama3.1:8b",
  );
  await expect(p.getByTestId("forecast-plan-result")).toBeVisible();
  await expect(p.getByTestId("agent-answer")).toContainText(
    "plan_forecast (completed)",
  );
  await expect(p).toContainText("Synthetic example clinic");
  await expect(p).toContainText("not a safety or availability guarantee");
  await expect(p).not.toContainText("INVENTED ANSWER");
});

test("local provider failure uses the explicitly labeled computed fallback", async ({
  page,
}) => {
  await mockAgent(page, "plan_forecast", {}, 500);
  const p = await panel(page);
  await p
    .locator("#forecast-question")
    .fill("Can our clinic safely operate tomorrow given the weather forecast?");
  await p
    .getByRole("button", {
      name: "Calculate forecast-backed plan",
      exact: true,
    })
    .click();
  await expect(p.getByTestId("agent-answer")).toContainText(
    "Guided fallback active",
  );
  await expect(p.getByTestId("forecast-plan-result")).toBeVisible();
});

test("fixed requirement is a hypothetical consecutive demand check, not a silent inventory change", async ({
  page,
}) => {
  await mockAgent(page, "evaluate_fixed_requirement", {
    name: "Sterilizer",
    power_kw: 1,
    duration_hours: 2,
    earliest_start: 8,
    deadline: 12,
  });
  const p = await panel(page);
  await p
    .locator("#forecast-question")
    .fill(
      "Run an additional 1 kW sterilizer for 2 hours from 08:00 before noon.",
    );
  await p
    .getByRole("button", {
      name: "Calculate forecast-backed plan",
      exact: true,
    })
    .click();
  await expect(p.getByTestId("agent-answer")).toContainText(
    "Additional requirement · hypothetical",
  );
  await expect(p.getByTestId("agent-answer")).toContainText(
    "has not changed the clinic inventory",
  );
  await expect(p.getByTestId("forecast-plan-result")).toBeVisible();
  await p
    .getByRole("button", {
      name: "Add fixed requirement to inventory",
      exact: true,
    })
    .click();
  await expect(p.getByTestId("forecast-plan-result")).toHaveCount(0);
  await expect(
    p.getByRole("checkbox", {
      name: "Confirm midnight battery assumption",
      exact: true,
    }),
  ).not.toBeChecked();
  await page
    .getByRole("button", { name: "Detailed mode", exact: true })
    .click();
  await expect(page.locator("#equipment")).toContainText(
    "Sterilizer (fixed hourly energy check)",
  );
});

test("mobile local AI capacity search renders computed samples with internal table scrolling", async ({
  page,
}) => {
  await page.setViewportSize({ width: 375, height: 812 });
  await mockAgent(page, "explore_battery_capacity", {
    day: "tomorrow",
    sunshine_factor: 0.5,
    target: "all_work",
  });
  const p = await panel(page);
  await p
    .locator("#forecast-question")
    .fill(
      "How much additional battery capacity would we need with 50% less sunlight?",
    );
  await p
    .getByRole("button", {
      name: "Calculate forecast-backed plan",
      exact: true,
    })
    .click();
  await expect(p.getByTestId("agent-capacity")).toBeVisible();
  await expect(
    p.getByRole("table", { name: "Computed battery capacity search" }),
  ).toContainText("200.000");
  await expect(p).toContainText(
    "Increasing storage alone did not meet this target",
  );
  await page.waitForTimeout(300);
  expect(
    await page.evaluate(() => document.documentElement.scrollWidth),
  ).toBeLessThanOrEqual(375);
});

test("competing-window example calculates an actual unequal-work comparison", async ({
  page,
}) => {
  await page.goto("/");
  await page
    .getByRole("button", { name: "Detailed mode", exact: true })
    .click();
  const response = page.waitForResponse(
    (r) => r.url().endsWith("/api/simulate") && r.status() === 200,
  );
  await page
    .getByRole("button", { name: "Load competing-window example", exact: true })
    .click();
  const d = await (await response).json();
  expect(d.optimized.metrics.flexible_deferred_kwh).toBe(0);
  expect(d.heuristic.metrics.flexible_deferred_kwh).toBeGreaterThan(0.3);
  expect(d.comparison.same_flexible_work_completed).toBe(false);
  await expect(
    page.getByText("Plan calculated from current inputs.", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByLabel("Weather for this plan", { exact: true }),
  ).toHaveValue("kisumu-2025-01-14");
});
