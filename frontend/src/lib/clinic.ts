import type {
  Equipment,
  EffectiveConfig,
  ScenarioSummary,
  SimulationRequest,
  ScenarioId,
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
  const response = await fetch(`/api/${path}`, {
    method: body === undefined ? "GET" : "POST",
    headers: body === undefined ? {} : { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
    signal,
  });
  const json = await response.json();
  if (!response.ok) {
    const error = json.error;
    throw new Error(
      error
        ? `${error.message} ${error.details.map((d: { loc: (string | number)[]; message: string }) => `${d.loc.join(".")}: ${d.message}`).join(" ")}`
        : "The service could not complete this request.",
    );
  }
  return json;
}
