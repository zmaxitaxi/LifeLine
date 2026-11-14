import { useEffect, useId, useRef, useState } from "react";
import { X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Field, FieldGroup, FieldLabel, FieldDescription } from "@/components/ui/field";
import { NativeSelect, NativeSelectOption } from "@/components/ui/native-select";
import type { ActivityDraft, ProposedEquipment } from "../../../../contracts/planning";
import { humanHour } from "./plan-language";

export function AddEquipment({ open, date, busy, error, onClose, onDraft }: { open: boolean; date: string; busy:boolean;error:string; onClose: () => void; onDraft: (details:ActivityDraft) => Promise<boolean> }) {
  const dialog = useRef<HTMLDialogElement>(null);
  const id = useId();
  const deviceId=useRef(`device-${crypto.randomUUID()}`);
  const [formError,setFormError]=useState("");
  const [priority, setPriority] = useState("");
  useEffect(() => {
    if (open && dialog.current && !dialog.current.open) {
      dialog.current.showModal();
      dialog.current.querySelector<HTMLInputElement>('input[name="name"]')?.focus();
    }
    if (!open && dialog.current?.open) dialog.current.close();
  }, [open]);
  return <dialog ref={dialog} className="chat-settings equipment-entry" aria-labelledby={`${id}-title`} onCancel={event=>{if(busy)event.preventDefault();else onClose();}} onClose={onClose}>
    <div className="settings-heading"><div><h2 id={`${id}-title`}>Add clinic equipment</h2><p>Add what you know, then review the equipment requirements.</p></div><Button variant="ghost" aria-label="Close equipment form" disabled={busy} onClick={onClose}><X /></Button></div>
    {error ? <p role="alert" className="editor-error">{error}</p> : null}
    <form onSubmit={async event => {
      event.preventDefault(); const form = event.currentTarget; const data = new FormData(form);
      const value = (name: string) => String(data.get(name) ?? "").trim();
      const name = value("name");
      setFormError("");
      const start = value("start"); const end = value("end");
      if ((start && !end) || (!start && end) || (start && end && Number(start) >= Number(end))) {
        const control = form.elements.namedItem("end") as HTMLSelectElement; control.setCustomValidity("Choose a finish time after the start, or leave both times unknown."); control.reportValidity(); return;
      }
      if(value("interruptible") === "no"){setFormError("This planner models work that can pause and resume. A continuous equipment cycle cannot be confirmed with this model.");return;}
      const category=value("priority") as "critical"|"flexible"|"";
      const rating=value("watts") ? Number(value("watts"))/1000 : null;
      const hours=start && end ? Array.from({length:Number(end)-Number(start)},(_,i)=>Number(start)+i) : null;
      const device:ProposedEquipment={id:deviceId.current,name,category:category || null,...(category === "flexible" ? {max_power_kw:rating,allowed_hours:hours,required_duration_hours:value("runtime") ? Number(value("runtime")) : null,divisible:value("interruptible") === "yes" ? true : null} : {power_kw:rating,required_hours:category === "critical" ? hours : null})};
      const saved=await onDraft({name,planning_date:date,start_hour:start ? Number(start) : null,end_hour:end ? Number(end) : null,equipment_ids:[device.id],additional_equipment:[device]});
      if(saved){form.reset();setPriority("");deviceId.current=`device-${crypto.randomUUID()}`;}

    }}>
      <fieldset disabled={busy}><FieldGroup>
        <Field><FieldLabel htmlFor={`${id}-name`}>Equipment name</FieldLabel><Input id={`${id}-name`} name="name" autoFocus required maxLength={120} placeholder="For example, a clinic light" /></Field>
        <Field><FieldLabel htmlFor={`${id}-watts`}>Power rating on the label (W)</FieldLabel><Input id={`${id}-watts`} name="watts" type="number" min="0.001" max="100000" step="any" placeholder="Leave blank if unknown" /><FieldDescription>Copy watts from the equipment label. Don’t guess.</FieldDescription></Field>
        <Field><FieldLabel htmlFor={`${id}-priority`}>Does it need protected power?</FieldLabel><NativeSelect id={`${id}-priority`} name="priority" value={priority} onChange={event => setPriority(event.target.value)}><NativeSelectOption value="">I’m not sure yet</NativeSelectOption><NativeSelectOption value="critical">Essential · must run at the agreed hours</NativeSelectOption><NativeSelectOption value="flexible">Can run at different agreed times</NativeSelectOption></NativeSelect></Field>
        <div className="equipment-entry-times">{([['start', 'Start time', 0, 23], ['end', 'Finish time', 1, 24]] as const).map(([name, label, min, max]) => <Field key={name}><FieldLabel htmlFor={`${id}-${name}`}>{label}</FieldLabel><NativeSelect id={`${id}-${name}`} name={name} onChange={event => event.currentTarget.setCustomValidity("")}><NativeSelectOption value="">Not known yet</NativeSelectOption>{Array.from({ length: max - min + 1 }, (_, offset) => min + offset).map(hour => <NativeSelectOption key={hour} value={String(hour)}>{humanHour(hour)}</NativeSelectOption>)}</NativeSelect></Field>)}</div>
        {priority === "flexible" ? <>
          <Field><FieldLabel htmlFor={`${id}-runtime`}>How many hours must this device run?</FieldLabel><Input id={`${id}-runtime`} name="runtime" type="number" min="1" max="24" step="1" placeholder="Leave blank if unknown" /><FieldDescription>Whole hours at the printed power rating. This is different from the hours when the device is available.</FieldDescription></Field>
          <Field><FieldLabel htmlFor={`${id}-interruptible`}>Can the work pause and resume?</FieldLabel><NativeSelect id={`${id}-interruptible`} name="interruptible"><NativeSelectOption value="">I’m not sure</NativeSelectOption><NativeSelectOption value="yes">Yes</NativeSelectOption><NativeSelectOption value="no">No · it must run without interruption</NativeSelectOption></NativeSelect></Field>
        </> : null}
      </FieldGroup></fieldset>
      {formError ? <p role="alert" className="editor-error">{formError}</p> : null}
      <p className="proposal-note">Nothing is added until you review and confirm LifeLine’s proposal.</p>
      <div className="proposal-actions"><Button type="submit" disabled={busy}>{busy ? "Saving…" : "Review equipment"}</Button><Button variant="ghost" type="button" disabled={busy} onClick={onClose}>Cancel</Button></div>
    </form>
  </dialog>;
}
