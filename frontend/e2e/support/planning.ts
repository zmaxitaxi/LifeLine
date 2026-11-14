import { expect, type Page, type APIRequestContext } from "@playwright/test";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { rmSync, writeFileSync } from "node:fs";
import type {
  CreatePlanningSession,
  PlanningState,
} from "../../../contracts/planning";
export const apiBase = `http://127.0.0.1:${process.env.LIFELINE_API_PORT ?? "8012"}/api/planning/sessions`;
export const weatherFailureFile = join(
  tmpdir(),
  `lifeline-ui-weather-failure-${process.env.LIFELINE_API_PORT ?? "8012"}`,
);
export function weatherFailure(failed: boolean) {
  if (failed) writeFileSync(weatherFailureFile, "test-only injected outage");
  else rmSync(weatherFailureFile, { force: true });
}
export function initial(
  overrides: Partial<CreatePlanningSession> = {},
): CreatePlanningSession {
  return {
    selected_clinic_id: "reviewed-example",
    clinic_name: "Kisumu test clinic",
    location: { latitude: -0.0917, longitude: 34.768 },
    timezone: "Africa/Nairobi",
    planning_date: "2026-11-14",
    midnight_battery_kwh: 2,
    clinic: {
      scenario: "normal",
      battery_capacity_kwh: 4,
      initial_battery_kwh: 2,
      reserve_kwh: 0.5,
      pv_capacity_kw: 1,
      charge_efficiency: 0.9,
      discharge_efficiency: 0.9,
      max_charge_kw: 2,
      max_discharge_kw: 2,
      equipment: [
        {
          id: "fridge",
          name: "Vaccine refrigerator",
          category: "critical",
          power_kw: 0.1,
          required_hours: Array.from({ length: 24 }, (_, h) => h),
        },
        {
          id: "pump",
          name: "Water pump",
          category: "flexible",
          max_power_kw: 0.5,
          required_energy_kwh: 1,
          allowed_hours: [8, 9, 10, 11, 12, 13, 14, 15, 16],
          baseline_allocations: [
            { hour: 8, requested_kwh: 0.5 },
            { hour: 9, requested_kwh: 0.5 },
          ],
          divisible: true,
        },
      ],
    },
    ...overrides,
  };
}
export async function seed(
  request: APIRequestContext,
  overrides: Partial<CreatePlanningSession> = {},
) {
  const response = await request.post(apiBase, { data: initial(overrides) });
  expect(response.ok(), await response.text()).toBe(true);
  return (await response.json()) as PlanningState;
}
export async function read(request: APIRequestContext, id: string) {
  const response = await request.get(`${apiBase}/${id}`);
  expect(response.ok()).toBe(true);
  return (await response.json()) as PlanningState;
}
export async function calculate(
  request: APIRequestContext,
  state: PlanningState,
) {
  const response = await request.post(`${apiBase}/${state.id}/recompute`, {
    data: { expected_revision: state.revision, include_recovery: true },
  });
  expect(response.ok(), await response.text()).toBe(true);
  const next = (await response.json()) as PlanningState;
  expect(next.plan_status).toBe("current");
  return next;
}
export async function open(page: Page, state: PlanningState) {
  await page.addInitScript(
    (id) => {localStorage.setItem("lifeline.planning-session.v1", id);localStorage.setItem("lifeline.reviewed-session.v1",id);},
    state.id,
  );
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "How can LifeLine help today?", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("textbox", { name: "Message LifeLine", exact: true }),
  ).toBeEditable();
}
export async function say(page: Page, question: string) {
  await page
    .getByRole("textbox", { name: "Message LifeLine", exact: true })
    .fill(question);
  const response = page.waitForResponse(
    (r) => /\/agent$/.test(r.url()) && r.request().method() === "POST",
  );
  await page.getByRole("button", { name: "Send message", exact: true }).click();
  const received = await response;
  expect(received.ok(), await received.text()).toBe(true);
  await expect(
    page.getByRole("textbox", { name: "Message LifeLine", exact: true }),
  ).toBeEditable();
}
export const proposal = (page: Page) =>
  page.locator('[data-testid="activity-proposal"]:visible');
export async function readyDraft(page: Page) {
  await say(page, "We have a vaccination campaign tomorrow from 9 AM to 3 PM.");
  await expect(proposal(page)).toContainText("Still needed");
  await say(page, "Use the Vaccine refrigerator.");
  await expect(
    proposal(page).getByRole("button", { name: "Confirm", exact: true }),
  ).toBeEnabled();
}
export async function confirm(page: Page) {
  const response = page.waitForResponse(
    (r) => /\/confirm$/.test(r.url()) && r.request().method() === "POST",
  );
  await proposal(page)
    .getByRole("button", { name: "Confirm", exact: true })
    .click();
  await response;
  await expect(page.locator("#chat-input")).toBeEditable();
}
export const overview = (page: Page) =>
  page.getByRole("link", { name: "Clinic Overview", exact: true });
export const assistant = (page: Page) =>
  page.getByRole("link", { name: "AI Assistant", exact: true });
