import { useId, useState } from "react";
import type { ActivityDraft, EquipmentConstraint, PlanningState } from "../../../../contracts/planning";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Field, FieldDescription, FieldGroup, FieldLabel, FieldLegend, FieldSet } from "@/components/ui/field";
import { NativeSelect, NativeSelectOption } from "@/components/ui/native-select";
import { Disclosure } from "@/components/Disclosure";
import { AdditionalEquipmentFields } from "./AdditionalEquipmentFields";
import { humanHour } from "./plan-language";
import { num, timeRanges } from "@/lib/clinic";

export function ActivityEditor({ state, initial = {}, busy, onSave, onCancel }: {
  state: PlanningState; initial?: ActivityDraft; busy: boolean;
  onSave: (details: ActivityDraft, revision: number) => Promise<void>; onCancel: () => void;
}) {
  const id = useId();
  const [revision] = useState(state.revision);
  const [name, setName] = useState(initial.name ?? "");
  const [start, setStart] = useState(initial.start_hour?.toString() ?? "");
  const [duration,setDuration]=useState(initial.duration_hours?.toString() ?? "");
  const [end, setEnd] = useState(initial.end_hour?.toString() ?? "");
  const [equipmentIds, setEquipmentIds] = useState(initial.equipment_ids ?? []);
  const [reviewed, setReviewed] = useState(initial.equipment_ids != null);
  const [constraintModes, setConstraintModes] = useState<Record<string,string>>(() => Object.fromEntries((initial.equipment_constraints ?? []).map(c => [c.equipment_id,"keep"])));
  const [deviceHours,setDeviceHours]=useState<Record<string,string>>(()=>Object.fromEntries((initial.equipment_constraints ?? []).filter(c=>c.required_duration_hours != null).map(c=>[c.equipment_id,String(c.required_duration_hours)])));
  const [error, setError] = useState("");
  const [additional,setAdditional]=useState(()=>(initial.additional_equipment ?? []).map(item=>({...item})));
  const [additionalWindows,setAdditionalWindows]=useState<string[]>([]);
  const inventory = state.equipment_inventory.filter(e => !additional.some(a => a.id === e.id));
  const equipment = [...inventory, ...additional];
  return <form onSubmit={async event => {
    event.preventDefault();setError("");
    if (start && end && Number(end) <= Number(start)) { setError("Choose a finish time after the start time.");return; }
    if(duration && (!Number.isInteger(Number(duration)) || Number(duration)<1 || Number(duration)>24 || (start && end && Number(duration)>Number(end)-Number(start)))){setError("The activity duration must be whole hours that fit between its start and finish.");return;}
    const hours = start && end ? Array.from({ length: Number(end) - Number(start) }, (_, index) => Number(start) + index) : null;
    if (equipmentIds.some(device => constraintModes[device] === "activity") && !hours) {setError("Choose start and finish times before changing equipment hours.");return;}
    const constraints:EquipmentConstraint[] = equipmentIds.flatMap<EquipmentConstraint>(device => {
      const mode=constraintModes[device];
      if(mode === "keep")return (initial.equipment_constraints ?? []).filter(c=>c.equipment_id===device).map(c=>({...c,required_duration_hours:undefined}));
      if(mode !== "activity")return [];
      const e = equipment.find(item => item.id === device);
      return [e?.category === "critical" ? {equipment_id:device,required_hours:hours} : {equipment_id:device,allowed_hours:hours}];
    });
    for(const device of equipmentIds){
      const value=deviceHours[device];if(!value)continue;
      if(!Number.isInteger(Number(value)) || Number(value)<1 || Number(value)>24){setError("Device operating time must be from 1 to 24 whole hours per day.");return;}
      const existing=constraints.find(c=>c.equipment_id===device);
      if(existing)existing.required_duration_hours=Number(value);else constraints.push({equipment_id:device,required_duration_hours:Number(value)});
    }
    if(additionalWindows.length && !hours){setError("Choose activity start and finish times for the new equipment.");return;}
    const additions=additional.filter(item=>!reviewed || equipmentIds.includes(item.id)).map(item=>additionalWindows.includes(item.id) ? {...item,...(item.category === "critical" ? {required_hours:hours} : {allowed_hours:hours})} : item);
    await onSave({...initial,additional_equipment:additions,name:name.trim() || null,planning_date:state.planning_date,start_hour:start === "" ? null : Number(start),end_hour:end === "" ? null : Number(end),duration_hours:duration ? Number(duration) : null,equipment_ids:reviewed ? equipmentIds : null,equipment_constraints:constraints.filter(c=>c.required_hours != null || c.allowed_hours != null || c.required_duration_hours != null)},revision);
  }}>
    <FieldGroup>
      <Field><FieldLabel htmlFor={`${id}-name`}>Activity name</FieldLabel><Input id={`${id}-name`} value={name} onChange={e=>setName(e.target.value)} placeholder="For example, vaccination campaign" maxLength={120} disabled={busy} autoFocus /></Field>
      <p className="editor-date">Planning date: <strong>{state.planning_date}</strong></p>
      <div className="equipment-entry-times">{([["start","Start time",start,setStart,0,23],["end","Finish time",end,setEnd,1,24]] as const).map(([key,label,value,change,min,max])=><Field key={key}><FieldLabel htmlFor={`${id}-${key}`}>{label}</FieldLabel><NativeSelect id={`${id}-${key}`} value={value} disabled={busy} onChange={e=>change(e.target.value)}><NativeSelectOption value="">Not known yet</NativeSelectOption>{Array.from({length:max-min+1},(_,offset)=>min+offset).map(hour=><NativeSelectOption key={hour} value={hour}>{humanHour(hour)}</NativeSelectOption>)}</NativeSelect></Field>)}</div>
      {inventory.filter(e=>e.category === "flexible" && equipmentIds.includes(e.id)).map(e=><Field key={e.id}><FieldLabel htmlFor={`${id}-runtime-${e.id}`}>{e.name}: required daily operating hours</FieldLabel><Input id={`${id}-runtime-${e.id}`} type="number" min="1" max="24" step="1" value={deviceHours[e.id] ?? ""} disabled={busy} onChange={event=>setDeviceHours(values=>({...values,[e.id]:event.target.value}))} placeholder="Use the clinic’s baseline requirement"/><FieldDescription>Total hours needed for this physical device across the whole day, not extra hours for this activity. Existing larger requirements remain protected. Python calculates the energy from its rated power.</FieldDescription></Field>)}
      <Field><FieldLabel htmlFor={`${id}-duration`}>Activity duration (hours, if known)</FieldLabel><Input id={`${id}-duration`} type="number" min="1" max="24" step="1" value={duration} disabled={busy} onChange={event=>setDuration(event.target.value)} placeholder="Leave blank if unknown"/><FieldDescription>This describes the event. Equipment operating time is reviewed separately.</FieldDescription></Field>
      <FieldSet><FieldLegend>Which equipment will this activity use?</FieldLegend><FieldDescription>Existing equipment stays counted once. Linking it to an activity does not add another device.</FieldDescription>
        {equipment.map(e=><Field key={e.id} orientation="horizontal"><Checkbox id={`${id}-${e.id}`} checked={equipmentIds.includes(e.id)} disabled={busy} onCheckedChange={checked=>{setReviewed(true);setEquipmentIds(items=>checked?[...items,e.id]:items.filter(item=>item!==e.id));}} /><FieldLabel htmlFor={`${id}-${e.id}`}>{e.name}{e.category === "critical" && e.power_kw != null ? ` · ${num(e.power_kw*1000,0)} W` : e.category === "flexible" && e.max_power_kw != null ? ` · up to ${num(e.max_power_kw*1000,0)} W` : ""}</FieldLabel></Field>)}
        <Field orientation="horizontal"><Checkbox id={`${id}-reviewed`} checked={reviewed} disabled={busy} onCheckedChange={setReviewed}/><FieldLabel htmlFor={`${id}-reviewed`}>I have reviewed the equipment list, including if none is needed.</FieldLabel></Field>
      </FieldSet>
      <AdditionalEquipmentFields items={additional.filter(item=>equipmentIds.includes(item.id))} knownIds={new Set(state.equipment_inventory.map(e=>e.id))} busy={busy} useWindow={additionalWindows} onWindow={(id,checked)=>setAdditionalWindows(ids=>checked?[...ids,id]:ids.filter(value=>value!==id))} onChange={(id,patch)=>setAdditional(items=>items.map(item=>item.id===id?{...item,...patch}:item))}/>
      {equipmentIds.length ? <Disclosure title="Change equipment operating hours" keepMounted={false}><p>Existing clinic power requirements stay protected. Choose an activity-specific requirement only when needed.</p>{equipment.filter(e=>equipmentIds.includes(e.id)).map(e=>{
        const prior=initial.equipment_constraints?.find(c=>c.equipment_id===e.id);
        return <Field key={e.id}><FieldLabel htmlFor={`${id}-window-${e.id}`}>{e.name} operating hours</FieldLabel><NativeSelect id={`${id}-window-${e.id}`} value={constraintModes[e.id] ?? "none"} disabled={busy || !e.category} onChange={event=>setConstraintModes(modes=>({...modes,[e.id]:event.target.value}))}>
          <NativeSelectOption value="none">No extra activity-specific hours</NativeSelectOption>
          {prior ? <NativeSelectOption value="keep">Keep this activity’s saved requirement: {timeRanges(prior.required_hours ?? prior.allowed_hours ?? [])}</NativeSelectOption> : null}
          <NativeSelectOption value="activity">{e.category === "critical" ? "Also require power throughout the activity" : "Allow its work only within the activity hours"}</NativeSelectOption>
        </NativeSelect></Field>;
      })}<ul>{inventory.filter(e=>equipmentIds.includes(e.id)).map(e=><li key={e.id}>{e.name}: {timeRanges(e.category === "critical" ? e.required_hours : e.allowed_hours)}</li>)}</ul></Disclosure> : null}
    </FieldGroup>
    {error ? <p role="alert" className="editor-error">{error}</p> : null}
    <p className="proposal-note">You’ll review the proposal before confirming. Nothing changes yet.</p>
    <div className="proposal-actions"><Button type="submit" disabled={busy}>{busy ? "Saving…" : "Review activity"}</Button><Button variant="ghost" type="button" disabled={busy} onClick={onCancel}>Cancel</Button></div>
  </form>;
}
