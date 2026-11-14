import { useState } from "react";
import type { ComputedPlan } from "../../../../contracts/planning";
import type { RecoveryOption } from "../../../../contracts/recovery";
import { Button } from "@/components/ui/button";
import { Disclosure } from "@/components/Disclosure";
import { num, shortName, timeRanges } from "@/lib/clinic";
import { recoveryTitle } from "./plan-language";

function Alternative({ option }: { option: RecoveryOption }) {
  const [open, setOpen] = useState(false);
  return (
    <li className="inline-alternative" data-option-id={option.id}>
      <strong>{recoveryTitle(option.kind)}</strong>
      <span>
        {option.metrics.essential_requested_kwh <= 1e-6
          ? "Essential needs not configured"
          : option.metrics.essential_unserved_kwh > 1e-6
            ? "Essential power still short"
            : "Essential power covered"}{" "}
        ·{" "}
        {option.metrics.reserve_shortfall_kwh > 1e-6
          ? "Battery below reserve"
          : "Reserve met"}{" "}
        ·{" "}
        {option.metrics.flexible_unfinished_kwh > 1e-6
          ? "Some work unfinished"
          : "Requested work covered"}
      </span>
      {option.infrastructure_changes.map((c) => (
        <p key={c.field}>
          {
            {
              pv_capacity_kw: "Solar capacity",
              battery_capacity_kwh: "Battery size",
              max_discharge_kw: "Battery output",
            }[c.field]
          }
          : {num(c.before)} → {num(c.after)} {c.unit}
        </p>
      ))}
      {option.work_changes.map((c) => (
        <p key={c.equipment_id}>
          {shortName(c.name)}: {num(c.explicitly_postponed_kwh)} kWh of work
          postponed.
        </p>
      ))}
      <Button
        variant="ghost"
        aria-expanded={open}
        onClick={() => setOpen((value) => !value)}
      >
        {open ? "Hide details" : "Show this plan"}
      </Button>
      {open ? (
        <div className="alternative-details">
          <p>
            Essential energy missing:{" "}
            {num(option.metrics.essential_unserved_kwh)} kWh. Lowest stored
            energy: {num(option.metrics.minimum_battery_kwh)} kWh. Unfinished
            original work: {num(option.metrics.flexible_unfinished_kwh)} kWh.
          </p>
          <ul>
            {option.plan.flexible_tasks.map((t) => (
              <li key={t.task_id}>
                {shortName(
                  option.simulation.equipment.find((e) => e.id === t.task_id)
                    ?.name ?? t.task_id,
                )}
                :{" "}
                {timeRanges(
                  t.allocations
                    .filter((a) => a.served_kwh > 1e-6)
                    .map((a) => a.hour),
                ) || "Not scheduled"}
                ; {num(t.served_kwh)} kWh supplied.
              </li>
            ))}
          </ul>
          {option.remaining_constraints.length ? (
            <ul>
              {option.remaining_constraints.map((c) => (
                <li key={c}>{c}</li>
              ))}
            </ul>
          ) : null}
        </div>
      ) : null}
    </li>
  );
}

/** Evidence from an actual server calculation. The assistant's explanation is
 * rendered above this component, never manufactured by the frontend. */
export function InlinePlan({
  computed,
  date,
  historical = false,
  selectionId,
  optionIds = [],
  showSchedule = true,
}: {
  computed: ComputedPlan;
  date: string;
  historical?: boolean;
  selectionId?: string;
  optionIds?: string[];
  showSchedule?: boolean;
}) {
  const recovery = computed.recovery;
  const available = recovery ? [recovery.existing,...recovery.options] : [];
  const alternatives = optionIds.map(id=>available.find(option=>option.id === id)).filter((option):option is RecoveryOption=>Boolean(option));
  const chosen = recovery ? [recovery.existing, ...recovery.options].find(o => o.id === (selectionId ?? optionIds[0] ?? recovery.recommended_option_id)) : undefined;
  const plan = chosen?.plan ?? computed.simulation.optimized;
  const equipment =
    chosen?.simulation.equipment ?? computed.simulation.equipment;
  return (
    <section
      className="inline-plan"
      aria-label={historical ? "Earlier calculated plan" : "Calculated plan"}
      data-testid={historical ? "historical-plan" : "current-plan-summary"}
      data-generation={computed.generation}
      data-selection-id={chosen?.id}
    >
      <p className="plan-date">
        {date} · forecast-based simulation
        {computed.sunshine_factor < 1
          ? ` · ${Math.round((1 - computed.sunshine_factor) * 100)}% less sunshine`
          : ""}
      </p>
      <p className="plan-date">{optionIds.length > 1 ? "Calculated comparisons" : `${selectionId ? "Selected comparison" : "Recommended plan"}: ${chosen ? recoveryTitle(chosen.kind) : "When to run equipment"}`}</p>
      {selectionId ? <dl className="focused-plan-facts"><div><dt>Essential power missing</dt><dd>{num(chosen?.metrics.essential_unserved_kwh ?? plan.metrics.critical_unserved_kwh)} kWh</dd></div><div><dt>Lowest battery</dt><dd>{num(plan.metrics.min_soc_kwh)} kWh</dd></div><div><dt>Unfinished work</dt><dd>{num(chosen?.metrics.flexible_unfinished_kwh ?? plan.metrics.flexible_deferred_kwh)} kWh</dd></div></dl> : null}
      {showSchedule ? <Disclosure title="Equipment times in this plan" keepMounted={false}>
        <ul className="assistant-plan-actions">
          {plan.flexible_tasks.map((task) => (
            <li key={task.task_id}>
              <strong>
                {shortName(
                  equipment.find((e) => e.id === task.task_id)?.name ??
                    task.task_id,
                )}
                :{" "}
              </strong>
              {timeRanges(
                task.allocations
                  .filter((a) => a.served_kwh > 1e-6)
                  .map((a) => a.hour),
              ) || "Not scheduled"}
              . {num(task.served_kwh)} kWh supplied
              {task.deferred_kwh > 1e-6
                ? `; ${num(task.deferred_kwh)} kWh unfinished`
                : ""}
              .
            </li>
          ))}
        </ul>
        <p>
          These are hourly slots; some contain partial use. They do not
          establish a complete medical equipment cycle.
        </p>
      </Disclosure> : null}
      {alternatives.length ? (
        <div className="inline-options">
          <h3>Calculated alternatives</h3>
          <ul>
            {alternatives.map((option) => (
              <Alternative key={option.id} option={option} />
            ))}
          </ul>
        </div>
      ) : null}
      <Disclosure title="Exact calculation and assumptions" keepMounted={false}>
        <p>
          Calculated at {computed.computed_at}. Lowest stored energy:{" "}
          {plan.metrics.min_soc_kwh.toFixed(6)} kWh. Essential energy missing:{" "}
          {plan.metrics.critical_unserved_kwh.toFixed(6)} kWh.
        </p>
        <ul>
          {(chosen?.simulation.assumptions ?? recovery?.assumptions ?? computed.simulation.assumptions).map(
            (a) => (
              <li key={a}>{a}</li>
            ),
          )}
        </ul>
      </Disclosure>
    </section>
  );
}
