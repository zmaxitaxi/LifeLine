import { useId } from "react";
import type { ProposedEquipment } from "../../../../contracts/planning";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Field, FieldDescription, FieldGroup, FieldLabel, FieldLegend, FieldSet } from "@/components/ui/field";
import { NativeSelect, NativeSelectOption } from "@/components/ui/native-select";
import { timeRanges } from "@/lib/clinic";
export function AdditionalEquipmentFields({items,knownIds,busy,useWindow,onWindow,onChange}: {
  items:ProposedEquipment[];knownIds:Set<string>;busy:boolean;useWindow:string[];
  onWindow:(id:string,checked:boolean)=>void;onChange:(id:string,patch:Partial<ProposedEquipment>)=>void;
}) {
  const uid=useId();
  return <>{items.map(item=>{
    const known=knownIds.has(item.id),power=item.category === "flexible" ? item.max_power_kw : item.power_kw;
    const hours=item.category === "flexible" ? item.allowed_hours : item.required_hours;
    return <FieldSet key={item.id}><FieldLegend>{item.name} specifications</FieldLegend><FieldGroup>
      {!known ? <>
        <Field><FieldLabel htmlFor={`${uid}-${item.id}-priority`}>Does {item.name} need protected power?</FieldLabel><NativeSelect id={`${uid}-${item.id}-priority`} value={item.category ?? ""} disabled={busy} onChange={event=>{
          const category=event.target.value as "critical"|"flexible"|"";const rating=item.power_kw ?? item.max_power_kw ?? null;
          onChange(item.id,{category:category || null,power_kw:category === "flexible" ? null : rating,max_power_kw:category === "flexible" ? rating : null,required_hours:null,allowed_hours:null,required_duration_hours:null,required_energy_kwh:null,divisible:null});
        }}><NativeSelectOption value="">Not known yet</NativeSelectOption><NativeSelectOption value="critical">Essential · must run at the agreed hours</NativeSelectOption><NativeSelectOption value="flexible">Can run at different agreed times</NativeSelectOption></NativeSelect></Field>
        <Field><FieldLabel htmlFor={`${uid}-${item.id}-watts`}>{item.name} power rating (W)</FieldLabel><Input id={`${uid}-${item.id}-watts`} type="number" min="0.001" max="100000" step="any" value={power == null ? "" : power*1000} disabled={busy} onChange={event=>onChange(item.id,item.category === "flexible" ? {max_power_kw:event.target.value ? Number(event.target.value)/1000 : null} : {power_kw:event.target.value ? Number(event.target.value)/1000 : null})}/><FieldDescription>Use the printed rating; leave blank if unknown.</FieldDescription></Field>
        <Field orientation="horizontal"><Checkbox id={`${uid}-${item.id}-hours`} checked={useWindow.includes(item.id)} disabled={busy || !item.category} onCheckedChange={checked=>onWindow(item.id,checked)}/><FieldLabel htmlFor={`${uid}-${item.id}-hours`}>{item.category === "critical" ? "Require this device throughout the activity’s hours" : "Allow this device to run within the activity’s hours"}</FieldLabel></Field>
        {hours?.length ? <p className="panel-footnote">Saved device hours: {timeRanges(hours)}.</p> : null}
      </> : <p className="panel-footnote">The confirmed device rating, essential needs and operating limits stay protected.</p>}
      {item.category === "flexible" ? <>
        <Field><FieldLabel htmlFor={`${uid}-${item.id}-runtime`}>{item.name} required operating hours</FieldLabel><Input id={`${uid}-${item.id}-runtime`} type="number" min="1" max="24" step="1" value={item.required_duration_hours ?? ""} disabled={busy} onChange={event=>onChange(item.id,{required_duration_hours:event.target.value ? Number(event.target.value) : null,required_energy_kwh:event.target.value ? null : item.required_energy_kwh})}/><FieldDescription>Whole device-hours at rated power. Python calculates the electricity requirement.</FieldDescription></Field>
        {!known ? <Field><FieldLabel htmlFor={`${uid}-${item.id}-pause`}>Can {item.name} work pause and resume?</FieldLabel><NativeSelect id={`${uid}-${item.id}-pause`} value={item.divisible === true ? "yes" : ""} disabled={busy} onChange={event=>onChange(item.id,{divisible:event.target.value === "yes" ? true : null})}><NativeSelectOption value="">Not confirmed</NativeSelectOption><NativeSelectOption value="yes">Yes · work can pause and resume</NativeSelectOption></NativeSelect><FieldDescription>Continuous medical cycles need a different model; do not treat this as a verified medical-cycle schedule.</FieldDescription></Field> : null}
      </> : null}
    </FieldGroup></FieldSet>;
  })}</>;
}
