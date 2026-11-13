import type {
  Equipment,
  EffectiveConfig,
  ScenarioSummary,
  SimulationRequest,
  ScenarioId,
  SimulationResponse,
} from "../../../contracts/api";
export interface EditableEquipment {
  id: string;
  name: string;
  category: "critical" | "flexible";
  power: number;
  duration: number;
  start: number;
  hours: number[];
}
export interface Draft {
  scenario: ScenarioId;
  config: EffectiveConfig;
  equipment: EditableEquipment[];
  clouds: number[];
  weather: number;
  dataset: "synthetic" | "kisumu-2025-01-14";
}
export const clock = (h: number) => `${String(h).padStart(2, "0")}:00`;
export const num = (n: number, d = 3) =>
  n.toLocaleString("en-US", {
    minimumFractionDigits: d,
    maximumFractionDigits: d,
  });
export const clinicNames: Record<ScenarioId, string> = {
  scheduling: "Kisumu demonstration clinic",
  normal: "Kisumu larger-system example",
  storm: "Kisumu cloudy-day example",
  high_demand: "Kisumu high-demand example",
};
export const shortName = (name: string) => name.replace(/\s*\([^)]*\)/g, "");
export function timeRanges(hours: number[]) {
  const sorted = [...new Set(hours)].sort((a, b) => a - b);
  const ranges: string[] = [];
  for (let i = 0; i < sorted.length; i++) {
    const start = sorted[i];
    let end = start + 1;
    while (i + 1 < sorted.length && sorted[i + 1] === end) {
      end++;
      i++;
    }
    ranges.push(`${clock(start)}–${clock(end)}`);
  }
  return ranges.join(", ");
}
export function fromResult(result: SimulationResponse): Draft {
  return fromPreset({
    id: result.scenario,
    name: result.scenario_name,
    description: "",
    data_source: "synthetic",
    expected_status: result.status,
    defaults: result.effective_config,
    equipment: result.equipment,
    cloud_factors: result.cloud_factors,
  });
}
export function validDraft(d: Draft) {
  return (
    Object.values(d.config).every(Number.isFinite) &&
    Number.isFinite(d.weather) &&
    d.weather >= 0 &&
    d.weather <= 100 &&
    d.config.battery_capacity_kwh > 0 &&
    d.config.battery_capacity_kwh <= 200 &&
    d.config.initial_battery_kwh >= 0 &&
    d.config.reserve_kwh >= 0 &&
    d.config.initial_battery_kwh <= d.config.battery_capacity_kwh &&
    d.config.reserve_kwh <= d.config.battery_capacity_kwh &&
    d.config.charge_efficiency > 0 &&
    d.config.charge_efficiency <= 1 &&
    d.config.discharge_efficiency > 0 &&
    d.config.discharge_efficiency <= 1 &&
    [
      d.config.pv_capacity_kw,
      d.config.max_charge_kw,
      d.config.max_discharge_kw,
    ].every((v) => v >= 0 && v <= 100) &&
    d.equipment.every(
      (e) =>
        e.name.trim() &&
        Number.isFinite(e.power) &&
        e.power >= 0 &&
        e.power <= 100 &&
        Number.isFinite(e.duration) &&
        e.duration >= 0 &&
        e.duration <= 24 &&
        (e.category === "critical" || (e.power > 0 && e.hours.length > 0)),
    )
  );
}
export function draftProblem(d: Draft): string | null {
  if (!Object.values(d.config).every(Number.isFinite))
    return "Enter a number for each solar and battery setting.";
  if (d.config.initial_battery_kwh > d.config.battery_capacity_kwh)
    return "Current battery charge cannot exceed the battery’s capacity. Change the charge or capacity.";
  if (d.config.reserve_kwh > d.config.battery_capacity_kwh)
    return "The reserve target cannot exceed the battery’s capacity. Change the reserve or capacity.";
  const equipment = d.equipment.find(
    (e) =>
      !e.name.trim() ||
      !Number.isFinite(e.power) ||
      !Number.isFinite(e.duration) ||
      e.power < 0 ||
      e.power > 100 ||
      e.duration < 0 ||
      e.duration > 24 ||
      (e.category === "flexible" && (e.power <= 0 || !e.hours.length)),
  );
  if (equipment)
    return `Check ${shortName(equipment.name) || "the unnamed equipment"}: enter a name, valid power, and operating hours. Equipment that can move needs a positive power rating and at least one allowed hour.`;
  if (!validDraft(d))
    return "Check the allowed ranges for solar, battery, efficiency, and sunshine settings.";
  return null;
}
export function fromPreset(p: ScenarioSummary): Draft {
  return {
    scenario: p.id,
    config: { ...p.defaults },
    clouds: [...p.cloud_factors],
    weather: 100,
    dataset: "synthetic",
    equipment: p.equipment.map((e) => ({
      id: e.id,
      name: e.name,
      category: e.category,
      power: e.category === "critical" ? e.power_kw : e.max_power_kw,
      duration:
        e.category === "critical"
          ? e.required_hours.length
          : e.required_energy_kwh / e.max_power_kw,
      start:
        e.category === "critical"
          ? (e.required_hours[0] ?? 0)
          : (e.baseline_allocations[0]?.hour ?? 0),
      hours: [
        ...(e.category === "critical" ? e.required_hours : e.allowed_hours),
      ],
    })),
  };
}
export function serializeEquipment(e: EditableEquipment): Equipment {
  if (e.category === "critical")
    return {
      id: e.id,
      name: e.name,
      category: e.category,
      power_kw: e.power,
      required_hours: e.hours,
    };
  let remaining = e.power * e.duration;
  const baseline_allocations = [...e.hours]
    .sort((a, b) => ((a - e.start + 24) % 24) - ((b - e.start + 24) % 24))
    .map((hour) => {
      const requested_kwh = Math.min(e.power, remaining);
      remaining = Math.max(0, remaining - requested_kwh);
      return { hour, requested_kwh };
    })
    .filter((a) => a.requested_kwh > 1e-10)
    .sort((a, b) => a.hour - b.hour);
  return {
    id: e.id,
    name: e.name,
    category: "flexible",
    max_power_kw: e.power,
    required_energy_kwh: e.power * e.duration,
    allowed_hours: e.hours,
    baseline_allocations,
    divisible: true,
  };
}
export function requestFor(d: Draft): SimulationRequest {
  const { additional_critical_kw: _, ...config } = d.config;
  return {
    scenario: d.scenario,
    weather_dataset: d.dataset,
    ...config,
    equipment: d.equipment.map(serializeEquipment),
    cloud_factors: d.clouds.map((c) => (c * d.weather) / 100),
  };
}
export async function api<T>(
  path: string,
  body?: unknown,
  signal?: AbortSignal,
): Promise<T> {
  let response: Response;
  const timeout = AbortSignal.timeout(20000);
  try {
    response = await fetch(`/api/${path}`, {
      method: body === undefined ? "GET" : "POST",
      headers: body === undefined ? {} : { "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
      signal: signal ? AbortSignal.any([signal, timeout]) : timeout,
    });
  } catch (e) {
    if (e instanceof Error && e.name === "AbortError" && signal?.aborted)
      throw e;
    if (timeout.aborted)
      throw new Error(
        "The local planner took too long to respond. Please try again.",
      );
    throw new Error(
      "LifeLine could not reach the local planner. Check that it is running, then try again.",
    );
  }
  let json;
  try {
    json = await response.json();
  } catch {
    throw new Error(
      "The local planner returned an unreadable response. Please try again.",
    );
  }
  if (!response.ok) {
    const error = json.error;
    throw new Error(
      error
        ? `${error.message} ${(error.details ?? []).map((d: { loc: (string | number)[]; message: string }) => `${d.loc.join(".")}: ${d.message}`).join(" ")}`
        : "The service could not complete this request.",
    );
  }
  return json;
}
