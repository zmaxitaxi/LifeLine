import type { EffectiveConfig } from "../../../../contracts/api";
import { Button } from "@/components/ui/button";
import { num } from "@/lib/clinic";
import type { BatteryReadingView, EnergyEdit } from "./EnergySettingsEditor";
const names:Record<keyof EnergyEdit,string>={battery_capacity_kwh:"Battery size",initial_battery_kwh:"Planning start energy",reserve_kwh:"Energy to keep in reserve",pv_capacity_kw:"Solar panel capacity",charge_efficiency:"Battery charging efficiency",discharge_efficiency:"Battery supply efficiency",max_charge_kw:"Maximum charging power",max_discharge_kw:"Maximum battery output"};
function value(key:keyof EnergyEdit,config:EffectiveConfig){const n=config[key];return key.endsWith("efficiency") ? `${num(n*100,1)}%` : key.endsWith("_kw") ? `${num(n)} kW` : `${num(n)} kWh`;}
export function EnergySettingsReview({current,proposed,changes,date,timezone,reading,updatesReading,busy,confirmDisabled=false,onConfirm,onEdit,onCancel}: {
  current:EffectiveConfig;proposed:EffectiveConfig;changes:EnergyEdit;date:string;timezone:string|null;
  reading:BatteryReadingView|null;updatesReading:boolean;busy:boolean;confirmDisabled?:boolean;onConfirm:()=>void;onEdit:()=>void;onCancel:()=>void;
}) {
  const capacityChanged=current.battery_capacity_kwh!==proposed.battery_capacity_kwh;
  return <article className="energy-review" data-testid="energy-proposal">
    <p className="proposal-note">Draft · review before confirming</p>
    <table className="plan-outcomes"><caption>Changes to the clinic’s planning settings</caption><thead><tr><th scope="col">Setting</th><th scope="col">Current</th><th scope="col">Proposed</th></tr></thead><tbody>
      {(Object.keys(changes) as (keyof EnergyEdit)[]).map(key=><tr key={key}><th scope="row">{names[key]}</th><td>{value(key,current)}</td><td>{value(key,proposed)}</td></tr>)}
    </tbody></table>
    <p>At midnight on {date}{timezone ? ` (${timezone})` : ""}, the plan assumes <strong>{num(proposed.initial_battery_kwh)} kWh stored ({num(proposed.initial_battery_kwh/proposed.battery_capacity_kwh*100,1)}%)</strong>.</p>
    {capacityChanged && !Object.hasOwn(changes,"initial_battery_kwh") ? <p>The battery size changes; starting stored energy stays at {num(current.initial_battery_kwh)} kWh. A larger battery does not add energy by itself.</p> : null}
    {updatesReading ? <p>{reading ? <>New current reading: <strong>{num(reading.energy_kwh)} kWh</strong> at {new Intl.DateTimeFormat("en",{dateStyle:"medium",timeStyle:"short",timeZone:timezone ?? undefined}).format(new Date(reading.measured_at))}{timezone ? ` (${timezone})` : ""}.</> : "The saved current reading will be cleared."} This is separate from the midnight assumption.</p> : null}
    <p className="proposal-note">Confirming updates the planning model and recalculates electricity. It does not physically change the power system.</p>
    {confirmDisabled ? <p className="editor-error" role="alert">The clinic inputs have changed. Start a new review through Edit details before confirming.</p> : null}
    <div className="proposal-actions"><Button disabled={busy || confirmDisabled} onClick={onConfirm}>{busy ? "Updating…" : "Confirm power settings"}</Button><Button disabled={busy} variant="outline" onClick={onEdit}>Edit details</Button><Button disabled={busy} variant="ghost" onClick={onCancel}>Cancel</Button></div>
  </article>;
}
