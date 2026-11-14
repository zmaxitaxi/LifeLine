import type { RecoveryOption } from "../../../../contracts/recovery";
import type { ComputedPlan } from "../../../../contracts/planning";
import { Button } from "@/components/ui/button";
import { shortName, timeRanges, num } from "@/lib/clinic";
import { recoveryTitle } from "./plan-language";

export function SolutionsSection({
  computed,
  busy,
  onChat,
  selected,
  onSelect,
}: {
  computed: ComputedPlan | null;
  busy: boolean;
  onChat: (question: string) => void;
  selected?: RecoveryOption;
  onSelect: (id: string) => void;
}) {
  const recovery = computed?.recovery;
  const proposed = selected ?? recovery?.existing;
  const existing = computed?.simulation.baseline.metrics;
  const next = proposed?.plan ?? computed?.simulation.baseline;
  return (
    <section
      data-overview-section="solutions"
      className="overview-section overview-square"
      aria-labelledby="solutions-title"
      tabIndex={0}
    >
      <h2 id="solutions-title">Plans</h2>
      <div className="overview-square-body">

        {computed && existing && next ? (
          <>
            {computed.weather_mode === "demo" ? <p className="panel-footnote">Demo-weather simulation · not a live forecast.</p> : null}
            <p className="panel-lead">{existing.critical_unserved_kwh > 1e-6 ? "Essential equipment may lose power" : existing.min_soc_kwh < computed.simulation.effective_config.reserve_kwh - 1e-6 ? "Battery may run too low" : existing.flexible_deferred_kwh > 1e-6 ? "Some work is unfinished" : existing.critical_requested_kwh <= 1e-6 ? "Essential needs need review" : "Current modeled needs are met"}</p>
            <table className="plan-outcomes"><caption className="sr-only">Current and selected plan outcomes</caption>
              <thead><tr><th scope="col">Daily outcome</th><th scope="col">Current</th><th scope="col">Selected</th></tr></thead>
              <tbody>
                <tr><th scope="row">Essential power</th>{[existing, next.metrics].map((m, i) => <td key={i}>{m.critical_requested_kwh <= 1e-6 ? "Not configured" : m.critical_unserved_kwh > 1e-6 ? `${num(m.critical_unserved_kwh)} kWh short` : "Needs covered"}</td>)}</tr>
                <tr><th scope="row">Battery reserve</th><td>{existing.min_soc_kwh < computed.simulation.effective_config.reserve_kwh - 1e-6 ? "Below target" : "Target met"}</td><td>{next.metrics.min_soc_kwh < (proposed?.config.reserve_kwh ?? computed.simulation.effective_config.reserve_kwh) - 1e-6 ? "Below target" : "Target met"}</td></tr>
                <tr><th scope="row">Unfinished work</th><td>{num(existing.flexible_deferred_kwh)} kWh</td><td>{num(proposed?.metrics.flexible_unfinished_kwh ?? next.metrics.flexible_deferred_kwh)} kWh</td></tr>
              </tbody>
            </table>
            {proposed && proposed.kind !== "existing" ? <p className="selected-plan-name"><strong>Selected:</strong> {recoveryTitle(proposed.kind)}</p> : null}
            {proposed?.infrastructure_changes.map((change) => (
              <p className="panel-change" key={change.field}>
                {
                  {
                    pv_capacity_kw: "Solar panels",
                    battery_capacity_kwh: "Battery size",
                    max_discharge_kw: "Battery output",
                  }[change.field]
                }
                : {num(change.before)} → {num(change.after)} {change.unit}
              </p>
            ))}
            {proposed?.work_changes.map(change => <p className="panel-change" key={change.equipment_id}>{shortName(change.name)}: {num(change.original_required_kwh)} → {num(change.tested_required_kwh)} kWh of work today. {num(change.explicitly_postponed_kwh)} kWh postponed, still unfinished.</p>)}
            <p className="panel-footnote">Comparison only · nothing physically changed.</p>
            <div className="plan-equipment-times"><h3>When to run equipment</h3>
              <ul>
                {next.flexible_tasks.map((t) => (
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
                    ; {num(t.served_kwh)} kWh supplied.
                  </li>
                ))}
              </ul>
              <p>
                Essential energy missing:{" "}
                {num(next.metrics.critical_unserved_kwh)} kWh. Lowest stored
                energy: {num(next.metrics.min_soc_kwh)} kWh.
              </p>
            </div>
            {recovery && proposed ? <fieldset className="plan-choices"><legend>Choose a calculated plan</legend>
              {[recovery.existing, ...recovery.options].map(option => <label key={option.id} className="plan-choice" data-selected={proposed.id === option.id}>
                <input type="radio" name="clinic-plan" value={option.id} checked={proposed.id === option.id} disabled={busy} onChange={() => onSelect(option.id)} />
                <span><strong>{option.kind === "existing" ? "Current plan" : recoveryTitle(option.kind)}{option.infrastructure_changes.length ? ` · ${option.infrastructure_changes.map(change => `${change.after} ${change.unit}`).join(", ")}` : ""}</strong>
                {option.id === recovery.recommended_option_id ? <small>Recommended</small> : null}</span>
              </label>)}
            </fieldset> : null}

          </>
        ) : (
          <p className="panel-lead">Ask LifeLine to find a better plan.</p>
        )}
        <Button
          variant="outline"
          disabled={busy}
          onClick={() =>
            onChat(
              computed ? "Explain the exact selected plan compared with the existing baseline. Explain what changes and which shortages remain in plain English. Keep this selected comparison; do not recalculate." : "Calculate recovery options for the clinic and describe what staff should review in plain English.",
            )
          }
        >
          Ask about this plan
        </Button>
      </div>
    </section>
  );
}
