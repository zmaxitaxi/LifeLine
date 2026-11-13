import { RotateCcw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Slider } from "@/components/ui/slider";
import { Disclosure } from "@/components/Disclosure";
import { FormFields } from "@/components/FormFields";
import type {
  EffectiveConfig,
  SimulationResponse,
} from "../../../contracts/api";
import type { Draft } from "../lib/clinic";

export function AdvancedSettings({
  draft,
  result,
  onChange,
  onReset,
}: {
  draft: Draft;
  result: SimulationResponse | null;
  onChange: (d: Draft) => void;
  onReset: () => void;
}) {
  function config(key: keyof EffectiveConfig, value: number) {
    onChange({ ...draft, config: { ...draft.config, [key]: value } });
  }
  return (
    <section className="advanced-settings" aria-labelledby="advanced-title">
      <div className="section-heading">
        <div>
          <h2 id="advanced-title">Advanced settings</h2>
          <p>
            System specifications used by the simulator. Valid changes
            recalculate your plan.
          </p>
        </div>
        <Button type="button" variant="outline" onClick={onReset}>
          <RotateCcw data-icon="inline-start" />
          Reset example
        </Button>
      </div>
      <h3>Solar and battery</h3>
      <FormFields className="advanced-fields">
        {(
          [
            ["pv_capacity_kw", "Solar capacity (kW)", 0, 100],
            ["battery_capacity_kwh", "Battery capacity (kWh)", 0.1, 200],
            ["initial_battery_kwh", "Current charge (kWh)", 0, 200],
            ["reserve_kwh", "Reserve target (kWh)", 0, 200],
            ["max_charge_kw", "Charge limit (kW)", 0, 100],
            ["max_discharge_kw", "Discharge limit (kW)", 0, 100],
            ["charge_efficiency", "Charge efficiency", 0.01, 1],
            ["discharge_efficiency", "Discharge efficiency", 0.01, 1],
          ] as const
        ).map(([key, label, min, max]) => (
          <label key={key}>
            {label}
            <Input
              aria-label={label}
              type="number"
              min={min}
              max={max}
              step="any"
              required
              value={
                Number.isFinite(draft.config[key]) ? draft.config[key] : ""
              }
              onChange={(e) => config(key, e.target.valueAsNumber)}
            />
          </label>
        ))}
      </FormFields>
      <div className="sunshine-control">
        <h3>Test less sunshine</h3>
        <p>
          Changes the weather example only. Equipment and starting battery stay
          fixed.
        </p>
        <label id="sunshine-label">
          Available sunshine{" "}
          <strong>{draft.weather}% of the selected profile</strong>
        </label>
        <Slider
          aria-labelledby="sunshine-label"
          thumbLabel="Available sunshine"
          min={0}
          max={100}
          step={5}
          value={[draft.weather]}
          onValueChange={(value) =>
            onChange({
              ...draft,
              weather: Array.isArray(value) ? value[0] : value,
            })
          }
        />
        <Button
          type="button"
          variant="outline"
          onClick={() => onChange({ ...draft, weather: 25 })}
        >
          Test 25% sunshine
        </Button>
      </div>
      <Disclosure title="Solver and model details">
        <p>
          LifeLine compares the existing schedule, sunshine-first scheduling,
          and a mixed-integer optimization using SciPy / HiGHS. The
          deterministic simulator verifies energy balances for each schedule.
        </p>
        <p>
          24 one-hour slots · Africa/Nairobi. Flexible equipment is modeled as
          divisible, interruptible energy. Essential requirements are fixed.
          This model does not validate medical appliance cycles.
        </p>
        {result ? (
          <>
            <p>
              Model version: {result.model_version}. Solar performance ratio:{" "}
              {result.pv_performance_ratio}.
            </p>
            {result.assumptions.map((a, i) => (
              <p key={i}>{a}</p>
            ))}
          </>
        ) : null}
      </Disclosure>
    </section>
  );
}
