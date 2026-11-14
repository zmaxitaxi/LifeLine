/** Labels for computed fields, not generated assistant answers. */
export function recoveryTitle(kind: string) {
  return (
    (
      {
        existing: "Keep current equipment times",
        scheduling: "Change when equipment runs",
        solar: "Add solar panels",
        battery: "Add battery storage",
        output: "Increase battery output",
        optional: "Postpone agreed work",
      } as Record<string, string>
    )[kind] ?? "Calculated alternative"
  );
}
export function humanHour(hour: number) {
  if (hour === 24) return "midnight";
  if (hour === 0) return "midnight";
  if (hour === 12) return "noon";
  return `${hour % 12 || 12} ${hour < 12 ? "AM" : "PM"}`;
}
