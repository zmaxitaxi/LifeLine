import { AlertTriangle, ArrowRight, CheckCircle2, Clock3 } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Disclosure } from "@/components/Disclosure";
import type { SimulationResponse } from "../../../contracts/api";
import { clock, num, shortName, timeRanges } from "../lib/clinic";

export function SimplePlan({
  result,
  onDetails,
  onChange,
}: {
  result: SimulationResponse;
  onDetails: () => void;
  onChange: () => void;
}) {
  const m = result.optimized.metrics;
  const shortage = m.critical_unserved_kwh > 1e-6;
  const low = m.reserve_breach_boundaries.length > 0;
  const deferred = m.flexible_deferred_kwh > 1e-6;
  const noEssentials = m.critical_requested_kwh <= 1e-6;
  const fixed = result.equipment.filter(
    (e) => e.category === "critical" && !e.id.startsWith("assistant_equipment"),
  );
  const headline = shortage
    ? "There isn’t enough power for all essential equipment"
    : noEssentials
      ? "Add essential equipment before checking its power"
      : low
        ? "Essential equipment has power, but the battery may run too low"
        : deferred
          ? "Essential equipment has power; some other work cannot finish"
          : "Essential equipment has enough power in this model";
  const limitation = shortage
    ? `Essential equipment loses power during ${timeRanges(m.critical_shortage_hours)}. Missing energy: ${num(m.critical_unserved_kwh)} kWh. Moving other work cannot resolve this shortage.`
    : noEssentials
      ? "No essential equipment energy is entered. Add its required power and hours before judging whether the clinic has enough electricity."
      : low
        ? `Battery may run too low. It reaches ${num(m.min_soc_kwh)} kWh, below the ${num(result.effective_config.reserve_kwh)} kWh reserve target. First below target at ${clock(m.reserve_breach_boundaries[0])}.`
        : deferred
          ? `${num(m.flexible_deferred_kwh)} kWh of requested work cannot be completed in the available hours. Unfinished equipment is marked below.`
          : "Tomorrow’s live forecast is unavailable. This plan uses an example day, so tomorrow’s electricity supply is still uncertain.";
  const actions = shortage
    ? [
        "Arrange another power source for the shortage hours before relying on this plan.",
        result.diagnosis.discharge_limited_hours.length
          ? "Ask a technician to review the battery’s output limit; a larger battery alone may not help."
          : "Ask a technician to review the available sunshine and stored battery energy.",
        "Review the essential equipment requirements with your clinic team.",
      ]
    : noEssentials
      ? [
          "Add your essential equipment and its required hours.",
          "Check the starting battery charge before recalculating.",
        ]
      : [
          low
            ? "Plan for backup power if the battery reaches its reserve target."
            : "Keep essential equipment on its required hours.",
          deferred
            ? "Review the unfinished work below and change its requirements if appropriate."
            : "Run other equipment during the times below to use the available energy.",
          "Review the clinic’s equipment and starting battery charge.",
        ];
  return (
    <section
      className="simple-plan"
      aria-labelledby="plan-title"
      data-testid="simple-plan"
    >
      <div className="plan-heading">
        <h2 id="plan-title" tabIndex={-1}>
          Your electricity plan
        </h2>
        <p>
          {result.weather_dataset === "synthetic"
            ? "Demonstration day"
            : "Historical example · 14 Jan 2025"}{" "}
          · not a live forecast
        </p>
      </div>
      <Alert
        className={`simple-assessment ${shortage ? "danger" : low || deferred || noEssentials ? "caution" : ""}`}
      >
        {shortage || low || deferred || noEssentials ? (
          <AlertTriangle aria-hidden="true" />
        ) : (
          <CheckCircle2 aria-hidden="true" />
        )}
        <AlertTitle>
          <h3>{headline}</h3>
        </AlertTitle>
        <AlertDescription>
          <p>
            {shortage
              ? "Scheduling alone cannot meet every essential requirement under these inputs."
              : "Calculated from the equipment, weather example, and battery information entered for this clinic."}
          </p>
        </AlertDescription>
      </Alert>
      <Alert
        variant={shortage ? "destructive" : "default"}
        className="plan-limitation"
      >
        <AlertTriangle aria-hidden="true" />
        <AlertTitle>
          {shortage
            ? "Essential power shortage"
            : low
              ? "Battery may run too low"
              : deferred
                ? "Some work is unfinished"
                : "Main limitation"}
        </AlertTitle>
        <AlertDescription>{limitation}</AlertDescription>
      </Alert>
      <section className="plan-actions" aria-labelledby="actions-title">
        <h3 id="actions-title">What to do</h3>
        <ol>
          {actions.map((action) => (
            <li key={action}>{action}</li>
          ))}
        </ol>
      </section>
      <section className="simple-timeline" aria-labelledby="timeline-title">
        <h3 id="timeline-title">When to run equipment</h3>
        <p>Local time · Africa/Nairobi · each block is one hour</p>
        <div className="simple-time-axis" aria-hidden="true">
          <span>00:00</span>
          <span>06:00</span>
          <span>12:00</span>
          <span>18:00</span>
          <span>24:00</span>
        </div>
        <ul className="equipment-plan-list">
          {fixed.length ? (
            <li className="essential-plan-row">
              <Disclosure
                title={`Essential equipment · ${fixed.length} fixed requirements`}
              >
                {fixed.map((e) => (
                  <p key={e.id}>
                    <strong>{shortName(e.name)}:</strong>{" "}
                    {e.category === "critical"
                      ? timeRanges(e.required_hours) || "No hours entered"
                      : ""}
                  </p>
                ))}
              </Disclosure>
              <p>Required hours stay fixed in every plan.</p>
              {shortage ? (
                <p className="unfinished">
                  Warning: essential equipment power is short during{" "}
                  {timeRanges(m.critical_shortage_hours)}.
                </p>
              ) : null}
            </li>
          ) : null}
          {result.equipment
            .filter(
              (e) =>
                e.category === "flexible" ||
                e.id.startsWith("assistant_equipment"),
            )
            .map((e) => {
              const task = result.optimized.flexible_tasks.find(
                (t) => t.task_id === e.id,
              );
              const active =
                e.category === "critical"
                  ? e.required_hours
                  : (task?.allocations
                      .filter((a) => a.served_kwh > 1e-6)
                      .map((a) => a.hour) ?? []);
              const partial =
                e.category === "flexible" &&
                task?.allocations.some(
                  (a) =>
                    a.served_kwh > 1e-6 &&
                    Math.abs(a.served_kwh - e.max_power_kw) > 1e-6,
                );
              return (
                <li key={e.id} className="equipment-plan-row">
                  <div className="equipment-plan-label">
                    <strong>{shortName(e.name)}</strong>
                    <span>
                      {e.category === "critical"
                        ? "Essential · fixed hours"
                        : "Can be moved"}
                    </span>
                  </div>
                  <div className="hour-blocks" aria-hidden="true">
                    {Array.from({ length: 24 }, (_, h) => (
                      <span
                        key={h}
                        className={
                          active.includes(h)
                            ? e.category === "critical"
                              ? "fixed-hour"
                              : "scheduled-hour"
                            : ""
                        }
                      />
                    ))}
                  </div>
                  <p>
                    <Clock3 aria-hidden="true" />
                    {timeRanges(active) || "No operation scheduled"}
                    {partial ? " · partial use in some hours" : ""}
                  </p>
                  {e.category === "critical" &&
                  shortage &&
                  active.some((h) => m.critical_shortage_hours.includes(h)) ? (
                    <p className="unfinished">
                      Warning: essential power is short during some of these
                      hours.
                    </p>
                  ) : null}
                  {task && task.deferred_kwh > 1e-6 ? (
                    <p className="unfinished">
                      Unfinished: {num(task.deferred_kwh)} kWh of{" "}
                      {num(task.requested_kwh)} kWh requested.
                    </p>
                  ) : null}
                </li>
              );
            })}
        </ul>
        <p className="cycle-note">
          <AlertTriangle aria-hidden="true" />
          Equipment cycles are approximated. Confirm actual device requirements;
          this model does not validate medical appliance cycles.
        </p>
      </section>
      <Disclosure title="Exact measurements and warnings">
        <dl className="exact-measurements">
          <div>
            <dt>Essential equipment power</dt>
            <dd>
              {m.critical_coverage_pct === null
                ? "No essential demand entered"
                : `${num(m.critical_coverage_pct, 1)}% of requested energy`}
            </dd>
          </div>
          <div>
            <dt>Essential energy unmet</dt>
            <dd>{num(m.critical_unserved_kwh)} kWh</dd>
          </div>
          <div>
            <dt>Lowest battery charge</dt>
            <dd>{num(m.min_soc_kwh)} kWh</dd>
          </div>
          <div>
            <dt>Battery charge at midnight</dt>
            <dd>{num(m.final_soc_kwh)} kWh</dd>
          </div>
          <div>
            <dt>Available solar energy in this model</dt>
            <dd>{num(m.total_solar_kwh)} kWh</dd>
          </div>
          <div>
            <dt>Other work unfinished</dt>
            <dd>{num(m.flexible_deferred_kwh)} kWh</dd>
          </div>
        </dl>
        {result.optimized.flexible_tasks.map((task) => (
          <p key={task.task_id}>
            <strong>
              {result.equipment.find((e) => e.id === task.task_id)?.name}:
            </strong>{" "}
            {task.allocations
              .map((a) => `${clock(a.hour)}: ${num(a.served_kwh)} kWh`)
              .join(" · ") || "No energy supplied"}
          </p>
        ))}
        {result.warnings
          .filter((w) => w.plan === "optimized")
          .map((w, i) => (
            <p key={i}>{w.message}</p>
          ))}
        {m.reserve_breach_boundaries.length ? (
          <p>
            Battery below reserve at:{" "}
            {m.reserve_breach_boundaries.map(clock).join(", ")}
          </p>
        ) : null}
      </Disclosure>
      <div className="plan-footer-actions">
        <Button type="button" onClick={onChange}>
          Change a requirement
        </Button>
        <Button type="button" variant="outline" onClick={onDetails}>
          Explore detailed results
          <ArrowRight data-icon="inline-end" />
        </Button>
      </div>
    </section>
  );
}
