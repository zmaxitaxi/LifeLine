import { useEffect, useId, useRef, useState } from "react";
import { X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Field, FieldGroup, FieldLabel, FieldDescription } from "@/components/ui/field";
import { NativeSelect, NativeSelectOption } from "@/components/ui/native-select";
import { humanHour } from "./plan-language";

export function AddEquipment({ open, date, onClose, onSubmit }: { open: boolean; date: string; onClose: () => void; onSubmit: (question: string) => void }) {
  const dialog = useRef<HTMLDialogElement>(null);
  const id = useId();
  const [priority, setPriority] = useState("");
  useEffect(() => {
    if (open && dialog.current && !dialog.current.open) {
      dialog.current.showModal();
      dialog.current.querySelector<HTMLInputElement>('input[name="name"]')?.focus();
    }
    if (!open && dialog.current?.open) dialog.current.close();
  }, [open]);
  return <dialog ref={dialog} className="chat-settings equipment-entry" aria-labelledby={`${id}-title`} onCancel={onClose} onClose={onClose}>
    <div className="settings-heading"><div><h2 id={`${id}-title`}>Add clinic equipment</h2><p>Share what you know. LifeLine will ask for anything missing.</p></div><Button variant="ghost" aria-label="Close equipment form" onClick={onClose}><X /></Button></div>
    <form onSubmit={event => {
      event.preventDefault(); const form = event.currentTarget; const data = new FormData(form);
      const value = (name: string) => String(data.get(name) ?? "").trim();
      const name = value("name");
      let question = `Please prepare an equipment-planning activity called “${name}” for ${date}, adding a new physical device named “${name}”.`;
      if (value("watts")) question += ` Its printed rating is ${value("watts")} W.`;
      if (value("priority")) question += ` I designate it ${value("priority")}.`;
      const start = value("start"); const end = value("end");
      if ((start && !end) || (!start && end) || (start && end && Number(start) >= Number(end))) {
        const control = form.elements.namedItem("end") as HTMLSelectElement; control.setCustomValidity("Choose a finish time after the start, or leave both times unknown."); control.reportValidity(); return;
      }
      if (start && end) {
        const from = `${start.padStart(2, "0")}:00`; const until = `${end.padStart(2, "0")}:00`;
        question += ` The activity runs from ${from} to ${until}.`;
        question += value("priority") === "flexible" ? ` The device may run from ${from} to ${until}.` : ` Its electrical operation is required from ${from} to ${until} in whole hourly slots.`;
      }
      if (value("priority") === "flexible") {
        if (value("runtime")) question += ` This device must run at its rated power for ${value("runtime")} whole hours within the allowed window. This is device runtime, not activity duration.`;
        if (value("interruptible") === "yes") question += " I confirm its work can be paused and resumed across whole-hour slots (divisible).";
        if (value("interruptible") === "no") question += " Its work cannot be paused or interrupted. Please explain if this is unsupported.";
      }
      question += " Ask me to clarify any missing specifications. Prepare a draft for my review; do not confirm it.";
      onClose(); onSubmit(question); form.reset(); setPriority("");
    }}>
      <FieldGroup>
        <Field><FieldLabel htmlFor={`${id}-name`}>Equipment name</FieldLabel><Input id={`${id}-name`} name="name" autoFocus required maxLength={120} placeholder="For example, a clinic light" /></Field>
        <Field><FieldLabel htmlFor={`${id}-watts`}>Power rating on the label (W)</FieldLabel><Input id={`${id}-watts`} name="watts" type="number" min="0.001" max="100000" step="any" placeholder="Leave blank if unknown" /><FieldDescription>Copy watts from the equipment label. Don’t guess.</FieldDescription></Field>
        <Field><FieldLabel htmlFor={`${id}-priority`}>Does it need protected power?</FieldLabel><NativeSelect id={`${id}-priority`} name="priority" value={priority} onChange={event => setPriority(event.target.value)}><NativeSelectOption value="">I’m not sure yet</NativeSelectOption><NativeSelectOption value="critical">Essential · must run at the agreed hours</NativeSelectOption><NativeSelectOption value="flexible">Can run at different agreed times</NativeSelectOption></NativeSelect></Field>
        <div className="equipment-entry-times">{([['start', 'Start time', 0, 23], ['end', 'Finish time', 1, 24]] as const).map(([name, label, min, max]) => <Field key={name}><FieldLabel htmlFor={`${id}-${name}`}>{label}</FieldLabel><NativeSelect id={`${id}-${name}`} name={name} onChange={event => event.currentTarget.setCustomValidity("")}><NativeSelectOption value="">Not known yet</NativeSelectOption>{Array.from({ length: max - min + 1 }, (_, offset) => min + offset).map(hour => <NativeSelectOption key={hour} value={String(hour)}>{humanHour(hour)}</NativeSelectOption>)}</NativeSelect></Field>)}</div>
        {priority === "flexible" ? <>
          <Field><FieldLabel htmlFor={`${id}-runtime`}>How many hours must this device run?</FieldLabel><Input id={`${id}-runtime`} name="runtime" type="number" min="1" max="24" step="1" placeholder="Leave blank if unknown" /><FieldDescription>Whole hours at the printed power rating. This is different from the hours when the device is available.</FieldDescription></Field>
          <Field><FieldLabel htmlFor={`${id}-interruptible`}>Can the work pause and resume?</FieldLabel><NativeSelect id={`${id}-interruptible`} name="interruptible"><NativeSelectOption value="">I’m not sure</NativeSelectOption><NativeSelectOption value="yes">Yes</NativeSelectOption><NativeSelectOption value="no">No · it must run without interruption</NativeSelectOption></NativeSelect></Field>
        </> : null}
      </FieldGroup>
      <p className="proposal-note">Nothing is added until you review and confirm LifeLine’s proposal.</p>
      <div className="proposal-actions"><Button type="submit">Review with LifeLine</Button><Button variant="ghost" type="button" onClick={onClose}>Cancel</Button></div>
    </form>
  </dialog>;
}
