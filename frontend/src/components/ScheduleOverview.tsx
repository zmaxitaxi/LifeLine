import { ArrowRight } from "lucide-react";
import type {
  SimulationResponse,
  TaskAllocation,
  RequestedTaskAllocation,
} from "../../../contracts/api";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "@/components/ui/card";
import { clock, num } from "../lib/clinic";
function hours(
  allocations: (TaskAllocation | RequestedTaskAllocation)[],
  power: number,
) {
  const valid = allocations.filter(
    (a) => ("served_kwh" in a ? a.served_kwh : a.requested_kwh) > 1e-6,
  );
  return valid.length
    ? valid
        .map((a) => {
          const energy = "served_kwh" in a ? a.served_kwh : a.requested_kwh;
          return `${clock(a.hour)}${Math.abs(energy - power) > 1e-6 ? ` (${num(energy, 2)} kWh)` : ""}`;
        })
        .join(" · ")
    : "No operation scheduled";
}
export function ScheduleOverview({
  result,
  id = "schedule",
}: {
  result: SimulationResponse;
  id?: string;
}) {
  const tasks = result.equipment.filter((e) => e.category === "flexible");
  return (
    <Card className="schedule-overview" id={id}>
      <CardHeader>
        <CardTitle>
          <h2>Your recommended operating schedule</h2>
        </CardTitle>
        <CardDescription>
          Before → After · local time, {result.timezone}. Partial-hour energy is
          shown in parentheses.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="overview-headings">
          <span>Equipment</span>
          <span>Before · existing request</span>
          <span>After · LifeLine plan</span>
        </div>
        {tasks.map((task) => {
          const old = result.baseline.flexible_tasks.find(
            (t) => t.task_id === task.id,
          )!;
          const next = result.optimized.flexible_tasks.find(
            (t) => t.task_id === task.id,
          )!;
          return (
            <article key={task.id} className="recommendation-row">
              <h3>{task.name}</h3>
              <div className="before-block">
                <span className="mobile-column-label">Before</span>
                <p>{hours(task.baseline_allocations, task.max_power_kw)}</p>
                <small>{num(old.served_kwh)} kWh served</small>
              </div>
              <div className="after-block">
                <span className="mobile-column-label">After</span>
                <p>
                  <ArrowRight size={14} />
                  {hours(next.allocations, task.max_power_kw)}
                </p>
                <small>
                  {num(next.served_kwh)} kWh served
                  {next.deferred_kwh > 1e-6
                    ? ` · ${num(next.deferred_kwh)} kWh deferred`
                    : ""}
                </small>
              </div>
            </article>
          );
        })}
        {tasks.length === 0 ? (
          <p>
            No flexible equipment to move. Protected equipment hours stay fixed.
          </p>
        ) : null}
        <p className="schedule-footnote">
          Protected loads stay fixed. Flexible work uses an interruptible hourly
          energy model, not a validated medical appliance cycle.
        </p>
      </CardContent>
    </Card>
  );
}
