import { useId, useState } from "react";
import type { EnergySettingsPatch, BatteryReading } from "../../../../contracts/planning";
import type { EffectiveConfig } from "../../../../contracts/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Field, FieldDescription, FieldGroup, FieldLabel } from "@/components/ui/field";
import { NativeSelect, NativeSelectOption } from "@/components/ui/native-select";
import { Disclosure } from "@/components/Disclosure";
import { num } from "@/lib/clinic";

// Form buffers only. The authoritative settings and reading come from the server.
export type EnergyEdit = EnergySettingsPatch;
export type BatteryReadingView = BatteryReading;
export interface EnergyFormValue {settings:EnergyEdit;reading:BatteryReadingView|null|undefined}
const percent = (energy:number,capacity:number) => String(Number((energy/capacity*100).toFixed(3)));
const deviceTime = () => {const now=new Date();return new Date(now.getTime()-now.getTimezoneOffset()*60000).toISOString().slice(0,16);};
export function EnergySettingsEditor({current,date,timezone,reading,revision,busy,onSave,onCancel,allowUnchanged=false}: {
  current:EffectiveConfig;date:string;timezone:string|null;reading:BatteryReadingView|null;revision:number;busy:boolean;allowUnchanged?:boolean;
  onSave:(value:EnergyFormValue,revision:number)=>Promise<void>;onCancel:()=>void;
}) {
  const id=useId();const [baseRevision]=useState(revision);
  const [capacity,setCapacity]=useState(String(current.battery_capacity_kwh));
  const [stored,setStored]=useState(current.initial_battery_kwh);
  const [startPercent,setStartPercent]=useState(percent(current.initial_battery_kwh,current.battery_capacity_kwh));
  const [solar,setSolar]=useState(String(current.pv_capacity_kw));
  const [reserve,setReserve]=useState(String(current.reserve_kwh));
  const [charge,setCharge]=useState(String(current.charge_efficiency*100));
  const [discharge,setDischarge]=useState(String(current.discharge_efficiency*100));
  const [chargeLimit,setChargeLimit]=useState(String(current.max_charge_kw*1000));
  const [outputLimit,setOutputLimit]=useState(String(current.max_discharge_kw*1000));
  const [readingAction,setReadingAction]=useState("keep");const [readingPercent,setReadingPercent]=useState("");const [measuredAt,setMeasuredAt]=useState(deviceTime);
  const [error,setError]=useState("");
  const validCapacity=Number(capacity)>0;
  return <form noValidate onSubmit={async event=>{
    event.preventDefault();setError("");
    const next = {battery_capacity_kwh:Number(capacity),initial_battery_kwh:stored,reserve_kwh:Number(reserve),pv_capacity_kw:Number(solar),charge_efficiency:Number(charge)/100,discharge_efficiency:Number(discharge)/100,max_charge_kw:Number(chargeLimit)/1000,max_discharge_kw:Number(outputLimit)/1000};
    if(!capacity || !startPercent || !solar || !reserve || !charge || !discharge || !chargeLimit || !outputLimit || !Object.values(next).every(Number.isFinite)){setError("Complete the settings with valid numbers before reviewing.");return;}
    if(next.battery_capacity_kwh<=0 || stored<0 || stored>next.battery_capacity_kwh || next.reserve_kwh<0 || next.reserve_kwh>next.battery_capacity_kwh){setError("The battery must be large enough for the starting energy and reserve. Changing its size does not add stored energy.");return;}
    if(next.battery_capacity_kwh>200 || next.pv_capacity_kw<0 || next.pv_capacity_kw>100 || next.max_charge_kw<0 || next.max_charge_kw>100 || next.max_discharge_kw<0 || next.max_discharge_kw>100 || next.charge_efficiency<=0 || next.charge_efficiency>1 || next.discharge_efficiency<=0 || next.discharge_efficiency>1){setError("Check the power settings. Efficiencies must be above 0% and at most 100%; battery size must be at most 200 kWh and power limits at most 100 kW.");return;}
    if(readingAction === "keep" && reading && reading.energy_kwh>next.battery_capacity_kwh){setError("The saved reading exceeds the new battery size. Record a new reading or clear the saved one before reviewing.");return;}
    const settings:EnergyEdit={};for(const key of Object.keys(next) as (keyof EnergyEdit)[])if(Math.abs(next[key]-current[key])>1e-9)settings[key]=next[key];
    let nextReading:BatteryReadingView|null|undefined;
    if(readingAction==="replace"){
      const value=Number(readingPercent),time=new Date(measuredAt);
      if(!readingPercent || !Number.isFinite(value) || value<0 || value>100 || !Number.isFinite(time.getTime()) || time.getTime()>Date.now()+60000){setError("Enter a battery reading from 0 to 100% and the time it was taken. The reading time cannot be in the future.");return;}
      nextReading={energy_kwh:value/100*next.battery_capacity_kwh,measured_at:time.toISOString()};
    }else if(readingAction==="clear")nextReading=null;
    if(!allowUnchanged && !Object.keys(settings).length && nextReading===undefined){setError("Change a setting or record a new reading before reviewing.");return;}
    await onSave({settings,reading:nextReading},baseRevision);
  }}>
    <FieldGroup>
      <Field><FieldLabel htmlFor={`${id}-capacity`}>Battery size (kWh)</FieldLabel><Input id={`${id}-capacity`} type="number" min="0.001" step="any" value={capacity} disabled={busy} onChange={e=>{setCapacity(e.target.value);if(Number(e.target.value)>0)setStartPercent(percent(stored,Number(e.target.value)));}} autoFocus required /><FieldDescription>Copy the storage capacity from the battery specifications.</FieldDescription></Field>
      <Field><FieldLabel htmlFor={`${id}-start`}>Planning start charge (%)</FieldLabel><Input id={`${id}-start`} type="number" min="0" max="100" step="any" value={startPercent} disabled={busy || !validCapacity} required onChange={e=>{setStartPercent(e.target.value);setStored(Number(e.target.value)/100*Number(capacity));}}/><FieldDescription>Assumed charge at midnight on {date}{timezone ? ` (${timezone})` : ""}. This is not a current measurement. {num(stored)} kWh stored.</FieldDescription></Field>
      <Field><FieldLabel htmlFor={`${id}-solar`}>Solar panel capacity (kW)</FieldLabel><Input id={`${id}-solar`} type="number" min="0" step="any" value={solar} disabled={busy} onChange={e=>setSolar(e.target.value)} required /><FieldDescription>Installed panel capacity, not the electricity available right now.</FieldDescription></Field>
      <Disclosure title="Record a current battery reading" keepMounted>
        {reading ? <p>Last recorded: {num(reading.energy_kwh)} kWh · {new Intl.DateTimeFormat("en",{dateStyle:"medium",timeStyle:"short",timeZone:timezone ?? undefined}).format(new Date(reading.measured_at))}{timezone ? ` (${timezone})` : ""}.</p> : <p>No current reading is recorded.</p>}
        <FieldGroup>
          <Field><FieldLabel htmlFor={`${id}-reading-action`}>Battery reading</FieldLabel><NativeSelect id={`${id}-reading-action`} value={readingAction} disabled={busy} onChange={e=>setReadingAction(e.target.value)}><NativeSelectOption value="keep">{reading ? "Keep the saved reading" : "Do not record a reading"}</NativeSelectOption><NativeSelectOption value="replace">Record a new reading</NativeSelectOption>{reading ? <NativeSelectOption value="clear">Clear the saved reading</NativeSelectOption> : null}</NativeSelect></Field>
          {readingAction==="replace" ? <><Field><FieldLabel htmlFor={`${id}-reading`}>Charge shown on the battery display (%)</FieldLabel><Input id={`${id}-reading`} type="number" min="0" max="100" step="any" required value={readingPercent} disabled={busy} onChange={e=>setReadingPercent(e.target.value)}/><FieldDescription>For the {capacity} kWh battery above. Recording this does not change the planning start charge.</FieldDescription></Field><Field><FieldLabel htmlFor={`${id}-time`}>Time of reading (device time)</FieldLabel><Input id={`${id}-time`} type="datetime-local" value={measuredAt} required disabled={busy} onChange={e=>setMeasuredAt(e.target.value)}/><FieldDescription>Use your device’s time zone: {Intl.DateTimeFormat().resolvedOptions().timeZone}.</FieldDescription></Field></> : null}
        </FieldGroup>
      </Disclosure>
      <Disclosure title="More power settings" keepMounted><FieldGroup>
        {([["reserve","Energy to keep in reserve (kWh)",reserve,setReserve,0,undefined],["charge","Battery charging efficiency (%)",charge,setCharge,0.001,100],["discharge","Battery supply efficiency (%)",discharge,setDischarge,0.001,100],["charge-limit","Maximum battery charging power (W)",chargeLimit,setChargeLimit,0,undefined],["output-limit","Maximum battery output (W)",outputLimit,setOutputLimit,0,undefined]] as const).map(([key,label,value,change,min,max])=><Field key={key}><FieldLabel htmlFor={`${id}-${key}`}>{label}</FieldLabel><Input id={`${id}-${key}`} type="number" step="any" value={value} onChange={e=>change(e.target.value)} min={min} max={max} disabled={busy}/></Field>)}
        <p>Changing battery size preserves the stored energy and reserve amount until you edit them. Check technical specifications with the person responsible for the power system.</p>
      </FieldGroup></Disclosure>
    </FieldGroup>
    {error ? <p role="alert" className="editor-error">{error}</p> : null}
    <p className="proposal-note">Review the changes before confirming. This updates the planning model, not physical equipment.</p>
    <div className="proposal-actions"><Button type="submit" disabled={busy}>{busy ? "Saving…" : "Review power settings"}</Button><Button type="button" variant="ghost" disabled={busy} onClick={onCancel}>Cancel</Button></div>
  </form>;
}
