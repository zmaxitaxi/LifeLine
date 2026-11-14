import type {
  ActivityDraft,
  ActivityProposal,
  PlanningState,
} from "../../../../contracts/planning";
import type { ActivityView } from "./presentation";
import { num, shortName, timeRanges } from "@/lib/clinic";
export function activityView(
  id: string,
  details: ActivityDraft,
  state: PlanningState,
  proposal?: ActivityProposal,
): ActivityView {
  const window =
    details.start_hour !== null &&
    details.start_hour !== undefined &&
    details.end_hour !== null &&
    details.end_hour !== undefined
      ? `${String(details.start_hour).padStart(2, "0")}:00–${String(details.end_hour).padStart(2, "0")}:00`
      : "Operating times needed";
  const addedIds = new Set(
    (details.additional_equipment ?? []).map((e) => e.id),
  );
  const existing = (details.equipment_ids ?? [])
    .filter((id) => !addedIds.has(id))
    .map((equipmentId) => {
      const e = state.equipment_inventory.find((e) => e.id === equipmentId);
      if (!e)
        return {
          id: equipmentId,
          name: equipmentId,
          specifications: ["Equipment reference needs review"],
        };
      return {
        id: e.id,
        name: shortName(e.name),
        specifications:
          e.category === "critical"
            ? [
                `${num(e.power_kw * 1000, 0)} W`,
                `Essential · ${timeRanges(e.required_hours)}`,
              ]
            : [
                `Up to ${num(e.max_power_kw * 1000, 0)} W`,
                `${num(e.required_energy_kwh)} kWh requested`,
                `Available ${timeRanges(e.allowed_hours)}`,
              ],
      };
    });
  const added = (details.additional_equipment ?? []).map((e) => ({
    id: e.id,
    name: e.name,
    specifications: [
      e.category === "critical"
        ? "Additional essential equipment"
        : e.category === "flexible"
          ? "Additional flexible equipment"
          : "Equipment priority needed",
      e.power_kw != null
        ? `${num(e.power_kw * 1000, 0)} W`
        : e.max_power_kw != null
          ? `Up to ${num(e.max_power_kw * 1000, 0)} W`
          : "Power rating needed",
      ...(e.required_duration_hours != null ? [`${e.required_duration_hours} whole hours at the rated power`] : []),
      ...(e.required_energy_kwh != null ? [`${num(e.required_energy_kwh)} kWh requested`] : []),
      ...(e.divisible === true ? ["Work can pause and resume"] : []),
      e.required_hours
        ? timeRanges(e.required_hours)
        : e.allowed_hours
          ? `Available ${timeRanges(e.allowed_hours)}`
          : "Operating hours needed",
    ],
  }));
  const missingLabels: Record<string, string> = {
    name: "Activity name",
    planning_date: "Activity date",
    start_hour: "Start time",
    end_hour: "Finish time",
    equipment_ids: "Review which equipment will be used",
  };
  const additionalLabels: Record<string, string> = {
    power_kw: "power rating from the label (W)",
    max_power_kw: "maximum power rating from the label (W)",
    category: "review whether essential or flexible",
    required_hours: "hours when it must run",
    allowed_hours: "hours when it may run",
    required_energy_kwh: "how many hours this device must run at its rated power, or its known energy requirement",
    required_duration_hours: "how many whole hours this device must run at its rated power",
    divisible: "confirmation that the work can be split and interrupted",
  };
  const missingLabel = (field: string) => {
    const extra = /^additional_equipment\.(\d+)\.(.+)$/.exec(field);
    if (extra)
      return `${details.additional_equipment?.[Number(extra[1])]?.name ?? "Additional equipment"}: ${additionalLabels[extra[2]] ?? extra[2].replaceAll("_", " ")}`;
    return (
      missingLabels[field] ?? field.replaceAll("_", " ").replaceAll(".", " · ")
    );
  };
  return {
    id,
    name: details.name ?? "New clinic activity",
    date: details.planning_date ?? "Date needed",
    operatingWindow: window,
    status: proposal ? "draft" : "confirmed",
    equipment: [...existing, ...added],
    missing: (proposal?.missing_fields ?? []).map(missingLabel),
    affectedRequirements: (details.equipment_constraints ?? []).map((c) => {
      const name = shortName(
        state.equipment_inventory.find((e) => e.id === c.equipment_id)?.name ??
          c.equipment_id,
      );
      if(c.required_duration_hours != null)return `${name}: at least ${c.required_duration_hours} total daily operating hours. Existing larger work requirements remain protected.${c.allowed_hours ? ` Allowed during ${timeRanges(c.allowed_hours)}.` : ""}`;
      return c.required_hours
        ? `${name}: additional required hours ${timeRanges(c.required_hours)}. Existing essential hours stay protected.`
        : `${name}: flexible operation restricted to ${timeRanges(c.allowed_hours ?? [])}.`;
    }),
  };
}
