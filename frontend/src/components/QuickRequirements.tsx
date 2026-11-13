import { useState } from "react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import {
  NativeSelect,
  NativeSelectOption,
} from "@/components/ui/native-select";
import { FormFields } from "@/components/FormFields";
import { shortName, type Draft } from "../lib/clinic";

export function QuickRequirements({
  draft,
  onChange,
  onDetails,
  onClose,
}: {
  draft: Draft;
  onChange: (d: Draft) => void;
  onDetails: () => void;
  onClose: () => void;
}) {
  const movable = draft.equipment.filter((e) => e.category === "flexible");
  const [selected, setSelected] = useState(movable[0]?.id ?? "");
  const item = movable.find((e) => e.id === selected) ?? movable[0];
  return (
    <section
      className="quick-requirements"
      aria-labelledby="requirements-title"
    >
      <div className="section-heading">
        <h3 id="requirements-title">Change a requirement</h3>
        <Button type="button" variant="ghost" onClick={onClose}>
          Done
        </Button>
      </div>
      <p>Valid changes calculate a new plan automatically.</p>
      <FormFields className="quick-fields">
        {item ? (
          <label>
            Equipment to change
            <NativeSelect
              className="w-full"
              aria-label="Equipment to change"
              value={item.id}
              onChange={(e) => setSelected(e.target.value)}
            >
              {movable.map((e) => (
                <NativeSelectOption key={e.id} value={e.id}>
                  {shortName(e.name)}
                </NativeSelectOption>
              ))}
            </NativeSelect>
          </label>
        ) : null}
        {item ? (
          <label>
            How long should it run? (hours)
            <Input
              aria-label="Required equipment hours"
              type="number"
              min={0}
              max={24}
              step="any"
              value={Number.isFinite(item.duration) ? item.duration : ""}
              onChange={(e) =>
                onChange({
                  ...draft,
                  equipment: draft.equipment.map((eq) =>
                    eq.id === item.id
                      ? { ...eq, duration: e.target.valueAsNumber }
                      : eq,
                  ),
                })
              }
            />
          </label>
        ) : null}
        <label>
          Starting battery charge (%)
          <Input
            aria-label="Starting battery charge (%)"
            type="number"
            min={0}
            max={100}
            step="any"
            value={
              Number.isFinite(draft.config.initial_battery_kwh)
                ? Number(
                    (
                      (100 * draft.config.initial_battery_kwh) /
                      draft.config.battery_capacity_kwh
                    ).toFixed(6),
                  )
                : ""
            }
            onChange={(e) =>
              onChange({
                ...draft,
                config: {
                  ...draft.config,
                  initial_battery_kwh:
                    (draft.config.battery_capacity_kwh *
                      e.target.valueAsNumber) /
                    100,
                },
              })
            }
          />
        </label>
      </FormFields>
      <Button type="button" variant="link" onClick={onDetails}>
        Edit equipment, required hours, or power ratings
      </Button>
    </section>
  );
}
