import type { ComputedPlan } from "../../../../contracts/planning";
import { Button } from "@/components/ui/button";
import { Disclosure } from "@/components/Disclosure";
import { num, shortName, timeRanges } from "@/lib/clinic";

export function PlanOutcome({
  computed,
  onExplore,
}: {
  computed: ComputedPlan;
  onExplore?: () => void;
}) {
  const recovery = computed.recovery;
  const existing = computed.simulation.baseline.metrics;
  const recommended = recovery?.options.find(
    (o) => o.id === recovery.recommended_option_id,
  );
  const operational = recommended?.plan ?? computed.simulation.optimized;
  const plannedInventory =
    recommended?.simulation.equipment ?? computed.simulation.equipment;
  const reserve = computed.simulation.effective_config.reserve_kwh;
  return (
    <div className="plan-outcome" data-testid="current-plan-summary">
      <h3>Energy outlook</h3>
      <p className="recovery-diagnosis">
        <strong>Current schedule: </strong>
        {existing.critical_requested_kwh <= 1e-6
          ? "No essential needs are configured; review the equipment inventory."
          : existing.critical_unserved_kwh > 1e-6
            ? `There is not enough electricity for all essential equipment. ${num(existing.critical_unserved_kwh)} kWh is missing.`
            : existing.min_soc_kwh < reserve - 1e-6
              ? `Essential equipment is supplied, but the battery falls below its ${num(reserve)} kWh reserve target.`
              : existing.flexible_deferred_kwh > 1e-6
                ? `Essential power is covered, but ${num(existing.flexible_deferred_kwh)} kWh of other requested work remains unfinished.`
                : "All configured energy needs and the reserve target are met in this modeled day."}
      </p>
      <p className="recovery-recommendation">
        <strong>
          {recommended
            ? `Recommended: ${recommended.label}`
            : "Recommended operating plan"}
        </strong>
        <span>
          {recovery?.next_action ??
            "Review the proposed equipment times with staff. Essential requirements stay protected; this is an energy calculation, not a medical-cycle check."}
        </span>
      </p>
      {recommended?.remaining_constraints.length ? (
        <div className="recovery-limits">
          <h4>Still unresolved</h4>
          <ul>
            {recommended.remaining_constraints.map((issue) => (
              <li key={issue}>{issue}</li>
            ))}
          </ul>
        </div>
      ) : null}
      <p className="recommended-impact">
        With this recommendation:{" "}
        {operational.metrics.critical_requested_kwh <= 1e-6
          ? "essential needs are not configured"
          : operational.metrics.critical_unserved_kwh > 1e-6
            ? `${num(operational.metrics.critical_unserved_kwh)} kWh of essential energy is still missing`
            : "essential energy needs are covered in the model"}
        . Lowest stored energy: {num(operational.metrics.min_soc_kwh)} kWh.{" "}
        {num(
          recommended?.metrics.flexible_unfinished_kwh ??
            operational.metrics.flexible_deferred_kwh,
        )}{" "}
        kWh of the original flexible work remains unfinished.
      </p>
      <ul className="assistant-plan-actions">
        {operational.flexible_tasks
          .filter((t) => t.served_kwh > 1e-6)
          .slice(0, 2)
          .map((t) => (
            <li key={t.task_id}>
              <strong>
                {shortName(
                  plannedInventory.find((e) => e.id === t.task_id)?.name ??
                    t.task_id,
                )}
                :{" "}
              </strong>
              {timeRanges(
                t.allocations
                  .filter((a) => a.served_kwh > 1e-6)
                  .map((a) => a.hour),
              )}{" "}
              · {num(t.served_kwh)} kWh modeled.
              {t.deferred_kwh > 1e-6
                ? ` ${num(t.deferred_kwh)} kWh unfinished.`
                : ""}
            </li>
          ))}
      </ul>
      <p className="answer-provenance">
        Forecast-based simulation · computed {computed.computed_at}. No proposed
        hardware change has been physically applied.
      </p>
      {onExplore ? (
        <Button variant="outline" onClick={onExplore}>
          Explore plan
        </Button>
      ) : null}
      <Disclosure title="Model limitations" keepMounted={false}>
        <ul>
          {(recovery?.limitations ?? computed.simulation.assumptions).map(
            (a) => (
              <li key={a}>{a}</li>
            ),
          )}
        </ul>
      </Disclosure>
    </div>
  );
}
