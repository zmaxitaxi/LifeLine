import type { SimulationResponse } from "../../../contracts/api";
import { clock, num } from "../lib/clinic";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "@/components/ui/card";
import {
  Table,
  TableHeader,
  TableBody,
  TableHead,
  TableCell,
  TableRow,
  TableCaption,
} from "@/components/ui/table";
import { Disclosure } from "./Disclosure";
const plans = ["baseline", "heuristic", "optimized"] as const;
const labels = {
  baseline: "Existing",
  heuristic: "Sunshine-first",
  optimized: "LifeLine",
};
export function Schedules({ result }: { result: SimulationResponse }) {
  const tasks = result.equipment.filter((e) => e.category === "flexible");
  return (
    <Card className="section schedule-section" id="detailed-schedule">
      <CardHeader>
        <div className="section-heading">
          <div>
            <span className="section-number">02 / SCHEDULE</span>
            <CardTitle>
              <h2>Same clinic. Three schedules.</h2>
            </CardTitle>
          </div>
          <span className="small muted">Local time · Africa/Nairobi</span>
        </div>
        <CardDescription>
          Colored blocks show work actually served; dashed outlines show
          existing work requested but not supplied. Hover for energy and
          duration. Night is shaded.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <p className="mobile-timeline-hint small muted">
          Swipe the timeline to see all 24 hours.
        </p>
        <div
          className="timeline-scroll"
          role="region"
          aria-label="Daily equipment schedules"
          tabIndex={0}
        >
          <div className="timeline">
            <div className="timeline-axis">
              <span>Equipment / plan</span>
              <div className="time-grid">
                {Array.from({ length: 24 }, (_, h) => (
                  <span key={h}>
                    {h % 3 === 0 ? String(h).padStart(2, "0") : ""}
                  </span>
                ))}
              </div>
              <span>Served</span>
            </div>
            {tasks.map((task) => (
              <div className="task-group" key={task.id}>
                <h3>{task.name}</h3>
                {plans.map((plan) => {
                  const outcome = result[plan].flexible_tasks.find(
                    (t) => t.task_id === task.id,
                  )!;
                  return (
                    <div className="timeline-row" key={plan}>
                      <span className="plan-label">
                        <i className={`legend-line ${plan}`} />
                        {labels[plan]}
                      </span>
                      <div
                        className="time-grid"
                        role="img"
                        aria-label={`${task.name}, ${labels[plan]}: ${
                          outcome.allocations
                            .filter((a) => a.served_kwh > 1e-6)
                            .map((a) => clock(a.hour))
                            .join(", ") || "no work served"
                        }`}
                      >
                        {Array.from({ length: 24 }, (_, h) => {
                          const energy =
                            outcome.allocations.find((a) => a.hour === h)
                              ?.served_kwh ?? 0;
                          const requested =
                            plan === "baseline" && task.category === "flexible"
                              ? (task.baseline_allocations.find(
                                  (a) => a.hour === h,
                                )?.requested_kwh ?? 0)
                              : energy;
                          return (
                            <div
                              key={h}
                              className={`time-cell ${h < 6 || h >= 18 ? "night" : ""}`}
                              title={`${clock(h)}: ${num(energy)} kWh served (${num(requested)} requested), ${num(energy / (task.category === "flexible" ? task.max_power_kw : 1), 2)} h equivalent runtime`}
                            >
                              {requested > energy + 1e-6 ? (
                                <span
                                  className="requested-block"
                                  style={{
                                    width: `${Math.min(100, (requested / (task.category === "flexible" ? task.max_power_kw : 1)) * 100)}%`,
                                  }}
                                />
                              ) : null}
                              <span
                                className={`work-block ${plan}`}
                                style={{
                                  width: `${Math.min(100, (energy / (task.category === "flexible" ? task.max_power_kw : 1)) * 100)}%`,
                                }}
                              />
                            </div>
                          );
                        })}
                      </div>
                      <span className="served">
                        {num(outcome.served_kwh)} <small>kWh</small>
                      </span>
                    </div>
                  );
                })}
                <p className="task-change">
                  Existing requested:{" "}
                  {(task.category === "flexible"
                    ? task.baseline_allocations
                    : []
                  )
                    .filter((a) => a.requested_kwh > 1e-6)
                    .map((a) => clock(a.hour))
                    .join(", ") || "none"}{" "}
                  <span>→</span> LifeLine:{" "}
                  {result.optimized.flexible_tasks
                    .find((t) => t.task_id === task.id)!
                    .allocations.filter((a) => a.served_kwh > 1e-6)
                    .map((a) => clock(a.hour))
                    .join(", ") || "deferred"}{" "}
                  ·{" "}
                  {num(
                    result.optimized.flexible_tasks.find(
                      (t) => t.task_id === task.id,
                    )!.deferred_kwh,
                  )}{" "}
                  kWh deferred
                </p>
              </div>
            ))}
            {tasks.length === 0 ? (
              <p>
                No flexible equipment to reschedule. Critical hours stay fixed.
              </p>
            ) : null}
          </div>
        </div>
        <Disclosure
          className="critical-details"
          title={`${result.equipment.filter((e) => e.category === "critical").length} protected loads · fixed in every schedule`}
        >
          {result.equipment
            .filter((e) => e.category === "critical")
            .map((e) => (
              <p key={e.id}>
                <strong>{e.name}</strong> ·{" "}
                {e.category === "critical" ? Math.round(e.power_kw * 1000) : 0}{" "}
                W ·{" "}
                {e.category === "critical"
                  ? e.required_hours.map(clock).join(", ")
                  : ""}
              </p>
            ))}
        </Disclosure>
      </CardContent>
    </Card>
  );
}
export function ComparisonTable({ result }: { result: SimulationResponse }) {
  const rows: [string, (p: SimulationResponse["baseline"]) => string][] = [
    [
      "Critical coverage",
      (p) =>
        p.metrics.critical_coverage_pct === null
          ? "N/A"
          : `${num(p.metrics.critical_coverage_pct, 1)}%`,
    ],
    [
      "Minimum reserve · 18:00–24:00",
      (p) =>
        `${num(Math.min(p.hourly[17].soc_end_kwh, ...p.hourly.slice(18).map((h) => h.soc_end_kwh)))} kWh`,
    ],
    ["Minimum battery · full day", (p) => `${num(p.metrics.min_soc_kwh)} kWh`],
    [
      "Battery conversion loss",
      (p) => `${num(p.metrics.conversion_loss_kwh)} kWh`,
    ],
    [
      "Flexible work completed",
      (p) => `${num(p.metrics.flexible_served_kwh)} kWh`,
    ],
    [
      "Flexible work deferred",
      (p) => `${num(p.metrics.flexible_deferred_kwh)} kWh`,
    ],
    [
      "Critical demand unmet",
      (p) => `${num(p.metrics.critical_unserved_kwh)} kWh`,
    ],
  ];
  return (
    <Card className="section comparison-card">
      <CardHeader>
        <div className="section-heading">
          <div>
            <span className="section-number">03 / COMPARE</span>
            <CardTitle>
              <h2>Account for every kilowatt-hour.</h2>
            </CardTitle>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <Table>
          <TableCaption className="sr-only">
            Computed outcomes under identical inputs and physical constraints
          </TableCaption>
          <TableHeader>
            <TableRow>
              <TableHead>Computed outcome</TableHead>
              {plans.map((p) => (
                <TableHead key={p}>{labels[p]}</TableHead>
              ))}
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.map(([label, read]) => (
              <TableRow key={label}>
                <TableHead scope="row">{label}</TableHead>
                {plans.map((p) => (
                  <TableCell key={p}>{read(result[p])}</TableCell>
                ))}
              </TableRow>
            ))}
          </TableBody>
        </Table>
        <p className="heuristic-note">
          {result.comparison.heuristic_matches_optimizer_metrics
            ? "Sunshine-first matches LifeLine’s key metrics here. A simple rule works well in this case; we do not claim an optimizer advantage."
            : "The heuristic and optimizer differ. Compare completed work, coverage, and reserve together; a higher battery level alone is not proof of a better schedule."}
        </p>
      </CardContent>
    </Card>
  );
}
