import type { ComputedPlan } from "../../../../contracts/planning";
import { Button } from "@/components/ui/button";
import {
  NativeSelect,
  NativeSelectOption,
} from "@/components/ui/native-select";
import { Disclosure } from "@/components/Disclosure";
import { OutcomeIndicators } from "./BatteryEvidence";
import { PlanOutcome } from "./PlanOutcome";
import { num, shortName, timeRanges } from "@/lib/clinic";

export function SolutionsSection({
  computed,
  selectedId,
  busy,
  onSelect,
  onRecompute,
}: {
  computed: ComputedPlan | null;
  selectedId: string | null;
  busy: boolean;
  onSelect: (id: string) => void;
  onRecompute: () => void;
}) {
  const recovery = computed?.recovery;
  const selected = recovery?.options.find(
    (o) => o.id === (selectedId ?? recovery.recommended_option_id),
  );
  return (
    <section
      data-overview-section="solutions"
      className="overview-section"
      aria-labelledby="solutions-title"
    >
      <h2 id="solutions-title">Solutions</h2>
      {computed ? (
        <>
          <PlanOutcome computed={computed} />
          {recovery && selected ? (
            <>
              <label className="recovery-select">
                Explore calculated recovery options
                <NativeSelect
                  aria-label="Calculated recovery option"
                  value={selected.id}
                  disabled={busy}
                  onChange={(e) => onSelect(e.target.value)}
                >
                  {recovery.options.map((o) => (
                    <NativeSelectOption key={o.id} value={o.id}>
                      {o.label}
                      {o.id === recovery.recommended_option_id
                        ? " · recommended"
                        : ""}
                    </NativeSelectOption>
                  ))}
                </NativeSelect>
              </label>
              <OutcomeIndicators
                current={{
                  label: "Current",
                  simulation: recovery.reference,
                  plan: recovery.existing.plan,
                }}
                proposed={{
                  label: "Selected proposal",
                  simulation: selected.simulation,
                  plan: selected.plan,
                }}
              />
              <div className="recovery-changes">
                <h4>What changes in this comparison</h4>
                <p>
                  {selected.kind === "existing"
                    ? "Existing requested equipment timing. No intervention is proposed."
                    : "Flexible equipment timing is recalculated within its allowed hours. Essential requirements stay fixed."}
                </p>
                <ul>
                  {selected.infrastructure_changes.map((c) => (
                    <li key={c.field}>
                      {
                        {
                          pv_capacity_kw: "Solar capacity",
                          battery_capacity_kwh: "Battery capacity",
                          max_discharge_kw: "Battery output limit",
                        }[c.field]
                      }
                      : {num(c.before)} → {num(c.after)} {c.unit}
                    </li>
                  ))}
                  {selected.work_changes.map((c) => (
                    <li key={c.equipment_id}>
                      {shortName(c.name)}: {num(c.tested_required_kwh)} kWh
                      requested instead of {num(c.original_required_kwh)} kWh.{" "}
                      {num(c.explicitly_postponed_kwh)} kWh explicitly
                      postponed.
                    </li>
                  ))}
                </ul>
                <p>
                  Starting stored energy stays{" "}
                  {num(selected.config.initial_battery_kwh)} kWh. Selecting a
                  proposal records a comparison; it does not install hardware.
                </p>
              </div>
              <div className="recovery-limits">
                <h4>Remaining shortages and limits</h4>
                {selected.remaining_constraints.length ? (
                  <ul>
                    {selected.remaining_constraints.map((c) => (
                      <li key={c}>{c}</li>
                    ))}
                  </ul>
                ) : (
                  <p>
                    No modeled shortfall remains against the original energy
                    requirements and reserve. Forecast and model limitations
                    still apply.
                  </p>
                )}
              </div>
              <Disclosure
                title="Exact before-and-after comparison"
                keepMounted={false}
              >
                <p>
                  Essential shortage reduction:{" "}
                  {selected.essential_shortage_reduction_kwh.toFixed(6)} kWh.
                  Minimum stored-energy improvement:{" "}
                  {selected.minimum_battery_improvement_kwh.toFixed(6)} kWh.
                  Flexible energy completion improvement:{" "}
                  {selected.flexible_completion_improvement_kwh.toFixed(6)} kWh.
                </p>
                <ul>
                  {recovery.assumptions.map((a) => (
                    <li key={a}>{a}</li>
                  ))}
                </ul>
              </Disclosure>
            </>
          ) : (
            <Button variant="outline" disabled={busy} onClick={onRecompute}>
              Evaluate recovery options
            </Button>
          )}
          <Disclosure
            title="Existing and recommended equipment times"
            keepMounted={false}
          >
            {(
              [
                ["Existing schedule", computed.simulation.baseline],
                ["Recommended operating plan", computed.simulation.optimized],
              ] as const
            ).map(([name, plan]) => (
              <div key={name}>
                <h3>{name}</h3>
                <ul>
                  {plan.flexible_tasks.map((t) => (
                    <li key={t.task_id}>
                      {shortName(
                        computed.simulation.equipment.find(
                          (e) => e.id === t.task_id,
                        )?.name ?? t.task_id,
                      )}
                      :{" "}
                      {timeRanges(
                        t.allocations
                          .filter((a) => a.served_kwh > 1e-6)
                          .map((a) => a.hour),
                      ) || "Not scheduled"}
                      ; {num(t.served_kwh)} kWh supplied, {num(t.deferred_kwh)}{" "}
                      kWh unfinished.
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </Disclosure>
        </>
      ) : (
        <p>
          No current verified solution is available. Calculate a plan after
          reviewing the confirmed activities.
        </p>
      )}
    </section>
  );
}
