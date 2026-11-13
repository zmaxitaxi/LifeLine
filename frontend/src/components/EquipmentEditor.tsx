import { FieldSet, FieldLegend } from "@/components/ui/field";
import { FormFields } from "@/components/FormFields";
import {
  NativeSelect,
  NativeSelectOption,
} from "@/components/ui/native-select";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { Input } from "@/components/ui/input";
import { Plus, Trash2 } from "lucide-react";
import type { EditableEquipment } from "../lib/clinic";
import { clock } from "../lib/clinic";
interface Props {
  equipment: EditableEquipment[];
  onChange: (next: EditableEquipment[]) => void;
}
export function EquipmentEditor({ equipment, onChange }: Props) {
  function update(id: string, patch: Partial<EditableEquipment>) {
    onChange(equipment.map((e) => (e.id === id ? { ...e, ...patch } : e)));
  }
  function duration(e: EditableEquipment, value: number) {
    const hours =
      e.category === "critical"
        ? Array.from(
            { length: Math.min(24, Math.max(0, Math.floor(value))) },
            (_, i) => (e.start + i) % 24,
          )
        : e.hours;
    update(e.id, { duration: value, hours });
  }
  return (
    <section className="section" id="equipment">
      <div className="section-heading">
        <div>
          <span className="section-number">CLINIC INPUTS</span>
          <h2>Clinic equipment</h2>
        </div>
        <Button
          type="button"
          variant="outline"
          size="sm"
          disabled={equipment.length >= 20}
          onClick={() =>
            onChange([
              ...equipment,
              {
                id: crypto.randomUUID(),
                name: "New equipment",
                category: "flexible",
                power: 0.2,
                duration: 2,
                start: 18,
                hours: Array.from({ length: 13 }, (_, i) => i + 8),
              },
            ])
          }
        >
          <Plus data-icon="inline-start" /> Add equipment
        </Button>
      </div>
      <p className="muted">
        Keep essential equipment on its required hours. Choose when other work
        can run. Edit a row to change its requirements.
      </p>
      <div className="equipment-list">
        {equipment.map((e) => (
          <Collapsible key={e.id} className="equipment-editor">
            <CollapsibleTrigger
              render={
                <Button
                  type="button"
                  variant="ghost"
                  className="equipment-toggle"
                />
              }
            >
              <span className={`dot ${e.category}`} />
              <strong>{e.name || "Unnamed equipment"}</strong>
              <span className="equipment-summary">
                {Number((e.power * 1000).toFixed(3))} W · {e.duration} h ·{" "}
                {e.category === "critical" ? "Essential" : "Can be moved"}
              </span>
              <span className="edit-label">Edit</span>
            </CollapsibleTrigger>
            <CollapsibleContent keepMounted>
              <FormFields className="editor-fields">
                <label>
                  Name
                  <Input
                    aria-label={`Name ${e.id}`}
                    value={e.name}
                    maxLength={100}
                    onChange={(ev) => update(e.id, { name: ev.target.value })}
                    required
                  />
                </label>
                <label>
                  Power (W)
                  <Input
                    aria-label={`Power ${e.name}`}
                    type="number"
                    min={e.category === "critical" ? 0 : 0.001}
                    max={100000}
                    step="any"
                    value={
                      Number.isFinite(e.power)
                        ? Number((e.power * 1000).toFixed(6))
                        : ""
                    }
                    onChange={(ev) =>
                      update(e.id, { power: ev.target.valueAsNumber / 1000 })
                    }
                    required
                  />
                </label>
                <label>
                  Priority
                  <NativeSelect
                    className="w-full"
                    aria-label={`Priority ${e.name}`}
                    value={e.category}
                    onChange={(ev) => {
                      const category = ev.target
                        .value as EditableEquipment["category"];
                      update(e.id, {
                        category,
                        duration:
                          category === "critical" ? e.hours.length : e.duration,
                      });
                    }}
                  >
                    <NativeSelectOption value="critical">
                      Essential · fixed hours
                    </NativeSelectOption>
                    <NativeSelectOption value="flexible">
                      Can be moved
                    </NativeSelectOption>
                  </NativeSelect>
                </label>
                <label>
                  Required duration (h)
                  <Input
                    aria-label={`Duration ${e.name}`}
                    type="number"
                    min={0}
                    max={24}
                    step={e.category === "critical" ? 1 : "any"}
                    value={Number.isFinite(e.duration) ? e.duration : ""}
                    onChange={(ev) => duration(e, ev.target.valueAsNumber)}
                    required
                  />
                </label>
                <label>
                  {e.category === "critical" ? "Fixed start" : "Existing start"}
                  <NativeSelect
                    className="w-full"
                    aria-label={`Existing start ${e.name}`}
                    value={e.start}
                    onChange={(ev) => {
                      const start = Number(ev.target.value);
                      update(e.id, {
                        start,
                        ...(e.category === "critical"
                          ? {
                              hours: Array.from(
                                { length: e.duration },
                                (_, i) => (start + i) % 24,
                              ),
                            }
                          : {}),
                      });
                    }}
                  >
                    {Array.from({ length: 24 }, (_, h) => (
                      <NativeSelectOption key={h} value={h}>
                        {clock(h)}
                      </NativeSelectOption>
                    ))}
                  </NativeSelect>
                </label>
                <Button
                  type="button"
                  variant="destructive"
                  size="sm"
                  aria-label={`Remove ${e.name}`}
                  onClick={() =>
                    onChange(equipment.filter((item) => item.id !== e.id))
                  }
                >
                  <Trash2 data-icon="inline-start" />
                  Remove
                </Button>
              </FormFields>
              <FieldSet className="hours-field">
                <FieldLegend>
                  {e.category === "critical"
                    ? "Required fixed hours"
                    : "Allowed hours"}{" "}
                  · each cell is one hour
                </FieldLegend>
                <div className="hours-picker">
                  {Array.from({ length: 24 }, (_, h) => (
                    <label
                      key={h}
                      className={e.hours.includes(h) ? "checked" : ""}
                    >
                      <Checkbox
                        aria-label={`${e.name} hour ${h}`}
                        checked={e.hours.includes(h)}
                        onCheckedChange={() => {
                          const hours = e.hours.includes(h)
                            ? e.hours.filter((x) => x !== h)
                            : [...e.hours, h].sort((a, b) => a - b);
                          update(e.id, {
                            hours,
                            ...(e.category === "critical"
                              ? { duration: hours.length }
                              : {}),
                          });
                        }}
                      />
                      <span>{String(h).padStart(2, "0")}</span>
                    </label>
                  ))}
                </div>
              </FieldSet>
              <p className="small muted">
                {e.category === "flexible"
                  ? "Divisible, interruptible energy model. Existing work starts at the selected hour and fills subsequent allowed slots; unavailable work is reported as deferred."
                  : "These hours stay fixed in every comparison. Critical is an operator-defined input, not a medical recommendation."}
              </p>
            </CollapsibleContent>
          </Collapsible>
        ))}
      </div>
      {equipment.length === 0 ? (
        <p className="empty-note">
          No equipment. Add a load to plan its energy use.
        </p>
      ) : null}
    </section>
  );
}
