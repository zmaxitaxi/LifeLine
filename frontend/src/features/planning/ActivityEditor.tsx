import { useId, useState } from "react";
import type {
  ActivityDraft,
  ProposedEquipment,
} from "../../../../contracts/planning";
import type { Equipment } from "../../../../contracts/api";
import { Input } from "@/components/ui/input";
import {
  NativeSelect,
  NativeSelectOption,
} from "@/components/ui/native-select";
import {
  Field,
  FieldDescription,
  FieldGroup,
  FieldLabel,
} from "@/components/ui/field";
import { Disclosure } from "@/components/Disclosure";
import { shortName } from "@/lib/clinic";

const hourPattern = "(?:[01]?[0-9]|2[0-3])(?:\\s*,\\s*(?:[01]?[0-9]|2[0-3]))*";
function HoursInput({
  name,
  value,
  required = false,
}: {
  name: string;
  value?: number[] | null;
  required?: boolean;
}) {
  return (
    <Input
      name={name}
      defaultValue={value?.join(", ") ?? ""}
      pattern={hourPattern}
      required={required}
      placeholder="9, 10, 11"
    />
  );
}
function ExtraEquipment({
  equipment,
  index,
}: {
  equipment: ProposedEquipment;
  index: number;
}) {
  const [category, setCategory] = useState(equipment.category ?? "");
  const prefix = `extra.${index}.`;
  return (
    <fieldset className="extra-equipment-fields">
      <legend>{equipment.name} · additional equipment</legend>
      <input type="hidden" name={prefix + "id"} value={equipment.id} />
      <FieldGroup>
        <Field>
          <FieldLabel>
            Equipment name
            <Input
              name={prefix + "name"}
              defaultValue={equipment.name}
              required
            />
          </FieldLabel>
        </Field>
        <Field>
          <FieldLabel>
            How is this equipment used?
            <NativeSelect
              name={prefix + "category"}
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              required
            >
              <NativeSelectOption value="">
                Choose its requirement
              </NativeSelectOption>
              <NativeSelectOption value="critical">
                Essential · must run at specified hours
              </NativeSelectOption>
              <NativeSelectOption value="flexible">
                Flexible · can run within an agreed window
              </NativeSelectOption>
            </NativeSelect>
          </FieldLabel>
          <FieldDescription>
            The clinic operator must review this choice. LifeLine does not
            assign medical priority.
          </FieldDescription>
        </Field>
        {category ? (
          <Field>
            <FieldLabel>
              Power rating on the label (W)
              <Input
                name={prefix + "watts"}
                type="number"
                min="0.001"
                max="100000"
                step="any"
                defaultValue={
                  (category === "critical"
                    ? equipment.power_kw
                    : equipment.max_power_kw) != null
                    ? (category === "critical"
                        ? equipment.power_kw!
                        : equipment.max_power_kw!) * 1000
                    : ""
                }
                required
              />
            </FieldLabel>
            <FieldDescription>
              Enter watts from the equipment label. Do not guess a rating.
            </FieldDescription>
          </Field>
        ) : null}
        {category === "critical" ? (
          <Field>
            <FieldLabel>
              Hours when it must run
              <HoursInput
                name={prefix + "hours"}
                value={equipment.required_hours}
                required
              />
            </FieldLabel>
            <FieldDescription>
              Use hour start times from 0 to 23: 9, 10, 11 means 09:00–12:00.
              Whole hours only.
            </FieldDescription>
          </Field>
        ) : category === "flexible" ? (
          <>
            <Field>
              <FieldLabel>
                Electricity required for the activity (kWh)
                <Input
                  name={prefix + "energy"}
                  type="number"
                  min="0.000001"
                  step="any"
                  defaultValue={equipment.required_energy_kwh ?? ""}
                  required
                />
              </FieldLabel>
              <FieldDescription>
                Use an operator-reviewed energy requirement. Power alone does
                not establish required work.
              </FieldDescription>
            </Field>
            <Field>
              <FieldLabel>
                Hours when it may run
                <HoursInput
                  name={prefix + "hours"}
                  value={equipment.allowed_hours}
                  required
                />
              </FieldLabel>
              <FieldDescription>
                Use hour start times from 0 to 23, separated by commas.
              </FieldDescription>
            </Field>
            <label className="check-choice">
              <input
                type="checkbox"
                name={prefix + "divisible"}
                defaultChecked={equipment.divisible === true}
                required
              />
              An operator has confirmed that this work can be split and
              interrupted.
            </label>
          </>
        ) : null}
      </FieldGroup>
    </fieldset>
  );
}

export function ActivityEditor({
  details,
  inventory,
  planningDate,
}: {
  details: ActivityDraft;
  inventory: Equipment[];
  planningDate: string;
}) {
  const id = useId();
  return (
    <div className="activity-editor">
      <FieldGroup>
        <Field>
          <FieldLabel htmlFor={`${id}-name`}>Activity name</FieldLabel>
          <Input
            id={`${id}-name`}
            name="name"
            defaultValue={details.name ?? ""}
            required
            maxLength={120}
          />
        </Field>
        <Field>
          <FieldLabel htmlFor={`${id}-date`}>Activity date</FieldLabel>
          <Input
            id={`${id}-date`}
            name="planning_date"
            type="date"
            defaultValue={details.planning_date ?? planningDate}
            min={planningDate}
            max={planningDate}
            required
          />
        </Field>
        <div className="activity-time-fields">
          <Field>
            <FieldLabel htmlFor={`${id}-start`}>Start hour (0–23)</FieldLabel>
            <Input
              id={`${id}-start`}
              name="start_hour"
              type="number"
              min="0"
              max="23"
              step="1"
              defaultValue={details.start_hour ?? ""}
              required
            />
            <FieldDescription>9 means 9 AM; 15 means 3 PM.</FieldDescription>
          </Field>
          <Field>
            <FieldLabel htmlFor={`${id}-end`}>Finish hour (1–24)</FieldLabel>
            <Input
              id={`${id}-end`}
              name="end_hour"
              type="number"
              min="1"
              max="24"
              step="1"
              defaultValue={details.end_hour ?? ""}
              required
            />
          </Field>
        </div>
        <div className="activity-time-fields">
          <Field>
            <FieldLabel>
              Required duration (hours, if known)
              <Input
                name="duration_hours"
                type="number"
                min="1"
                max="24"
                step="1"
                defaultValue={details.duration_hours ?? ""}
              />
            </FieldLabel>
          </Field>
          <Field>
            <FieldLabel>
              Must finish by (hour, optional)
              <Input
                name="deadline_hour"
                type="number"
                min="1"
                max="24"
                step="1"
                defaultValue={details.deadline_hour ?? ""}
              />
            </FieldLabel>
          </Field>
        </div>
      </FieldGroup>
      <fieldset className="activity-equipment-choice">
        <legend>Which existing equipment will be used?</legend>
        {inventory.map((e) => (
          <label className="check-choice" key={e.id}>
            <input
              type="checkbox"
              name="equipment_ids"
              value={e.id}
              defaultChecked={details.equipment_ids?.includes(e.id) ?? false}
            />
            {shortName(e.name)}
          </label>
        ))}
        <label className="check-choice">
          <input
            type="checkbox"
            name="equipment_reviewed"
            defaultChecked={
              details.equipment_ids !== null &&
              details.equipment_ids !== undefined
            }
            required
          />
          I reviewed this list, including if no existing equipment is needed.
        </label>
        <p className="proposal-note">
          Linking existing equipment does not add another device or change its
          electricity requirements.
        </p>
      </fieldset>
      <Disclosure
        title="Review changes to equipment operating hours"
        keepMounted
      >
        <p>
          Existing essential hours stay protected. Leave blank to keep the
          current requirements. Only list hours inside this activity’s window.
        </p>
        <FieldGroup>
          {inventory.map((e) => (
            <Field key={e.id}>
              <FieldLabel>
                {shortName(e.name)} ·{" "}
                {e.category === "critical"
                  ? "extra required hours"
                  : "restrict available hours"}
                <HoursInput
                  name={`constraint.${e.id}`}
                  value={
                    details.equipment_constraints?.find(
                      (c) => c.equipment_id === e.id,
                    )?.[
                      e.category === "critical"
                        ? "required_hours"
                        : "allowed_hours"
                    ]
                  }
                />
              </FieldLabel>
            </Field>
          ))}
        </FieldGroup>
      </Disclosure>
      {(details.additional_equipment ?? []).map((e, i) => (
        <ExtraEquipment key={e.id} equipment={e} index={i} />
      ))}
    </div>
  );
}
export function readActivityForm(
  form: HTMLFormElement,
  original: ActivityDraft,
  inventory: Equipment[],
): ActivityDraft {
  const data = new FormData(form);
  const text = (key: string) => String(data.get(key) ?? "").trim();
  const number = (key: string) => (text(key) ? Number(text(key)) : null);
  const hours = (key: string) =>
    text(key)
      ? [
          ...new Set(
            text(key)
              .split(",")
              .map((h) => Number(h.trim())),
          ),
        ].sort((a, b) => a - b)
      : [];
  return {
    ...original,
    name: text("name"),
    planning_date: text("planning_date"),
    start_hour: number("start_hour"),
    end_hour: number("end_hour"),
    duration_hours: number("duration_hours"),
    deadline_hour: number("deadline_hour"),
    equipment_ids: [
      ...new Set([
        ...data.getAll("equipment_ids").map(String),
        ...(original.equipment_ids ?? []).filter((id) =>
          original.additional_equipment?.some((e) => e.id === id),
        ),
      ]),
    ],
    equipment_constraints: inventory
      .filter((e) => text(`constraint.${e.id}`))
      .map((e) => ({
        equipment_id: e.id,
        [e.category === "critical" ? "required_hours" : "allowed_hours"]: hours(
          `constraint.${e.id}`,
        ),
      })),
    additional_equipment: (original.additional_equipment ?? []).map((e, i) => {
      const prefix = `extra.${i}.`;
      const category = text(prefix + "category") as "critical" | "flexible";
      return {
        id: e.id,
        name: text(prefix + "name"),
        category,
        ...(category === "critical"
          ? {
              power_kw: Number(text(prefix + "watts")) / 1000,
              required_hours: hours(prefix + "hours"),
            }
          : {
              max_power_kw: Number(text(prefix + "watts")) / 1000,
              required_energy_kwh: Number(text(prefix + "energy")),
              allowed_hours: hours(prefix + "hours"),
              divisible: true as const,
            }),
      };
    }),
  };
}
