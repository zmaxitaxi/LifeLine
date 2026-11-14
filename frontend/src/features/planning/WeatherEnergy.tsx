import { useState } from "react";
import type { ComputedPlan } from "../../../../contracts/planning";
import type { RecoveryOption } from "../../../../contracts/recovery";
import { num } from "@/lib/clinic";

/** Read-only evidence from the same verified scenario shown in Battery & Energy. */
export function WeatherEnergy({ day, planningDate, computed, selected }: {
  day: string; planningDate: string; computed: ComputedPlan | null; selected?: RecoveryOption;
}) {
  const [hour, setHour] = useState(12);
  const current = computed?.simulation.baseline;
  const proposed = selected && selected.kind !== "existing" ? selected.plan : undefined;
  if (day !== planningDate || !current) return <div className="weather-energy" aria-live="polite">
    <h3>{day} · Energy outlook</h3><p>No clinic energy calculation for this date.</p>
    <p className="panel-footnote">Weather conditions alone don’t tell us how much power the equipment will have.</p>
  </div>;
  const row = current.hourly[hour];
  const next = proposed?.hourly[hour];
  return <div className="weather-energy" aria-live="polite" data-testid="weather-energy">
    <h3>{day} · Solar energy</h3>
    <p className="panel-footnote">Forecast-based simulation · {computed.simulation.timezone}</p>
    <div className="weather-hours" role="group" aria-label="Weather energy hour">
      {current.hourly.map(item => <button type="button" key={item.hour} aria-pressed={hour === item.hour} onClick={() => setHour(item.hour)}>{String(item.hour).padStart(2, "0")}:00</button>)}
    </div>
    <p><strong>{String(hour).padStart(2, "0")}:00–{String(hour + 1).padStart(2, "0")}:00</strong></p>
    <dl className="weather-energy-values">
      <div><dt>Solar available</dt><dd data-testid="weather-solar">{num(row.pv_kwh)} kWh{next ? ` → ${num(next.pv_kwh)} kWh selected` : ""}</dd></div>
      <div><dt>Essential equipment needs</dt><dd>{num(row.critical_requested_kwh)} kWh{next && Math.abs(next.critical_requested_kwh - row.critical_requested_kwh) > 1e-6 ? ` → ${num(next.critical_requested_kwh)} kWh selected` : ""}</dd></div>
      <div><dt>Battery</dt><dd>{row.charge_input_kwh > 1e-6 ? `Charging · ${num(row.charge_input_kwh)} kWh in` : row.discharge_output_kwh > 1e-6 ? `Supplying equipment · ${num(row.discharge_output_kwh)} kWh out` : "No charge or discharge"}</dd></div>
    </dl>
    {row.critical_unserved_kwh > 1e-6 ? <p className="panel-attention">Essential power shortage: {num(row.critical_unserved_kwh)} kWh{next ? ` → ${num(next.critical_unserved_kwh)} kWh selected` : ""}.</p> : null}
    <p className="panel-footnote">Current schedule{next ? " → selected plan" : ""}. Solar depends on the forecast and panel size; the battery may cover a shortfall.</p>
  </div>;
}
