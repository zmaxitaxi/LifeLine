import type { SimulationResponse } from "../../../contracts/api";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter,
} from "@/components/ui/card";
import { num } from "../lib/clinic";
export function PlanSummary({ result }: { result: SimulationResponse }) {
  const c = result.comparison,
    m = result.optimized.metrics;
  const shortage = m.critical_unserved_kwh > 1e-6;
  const same = c.same_flexible_work_completed;
  const delta = c.battery_preserved_at_midnight_kwh;
  const label = shortage
    ? "Critical energy still unserved"
    : same
      ? delta > 1e-6
        ? "More battery at midnight"
        : Math.abs(delta) <= 1e-6
          ? "No measurable battery gain"
          : "Battery difference at midnight"
      : "Battery difference · work completion differs";
  return (
    <>
      <Card
        className={`hero-result ${shortage ? "critical-result" : !same ? "tradeoff-result" : ""}`}
      >
        <CardHeader>
          <CardDescription>
            Computed from this clinic · 24-hour simulation
          </CardDescription>
          <CardTitle>
            <h2>{label}</h2>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="hero-value" data-testid="battery-preserved">
            {num(shortage ? m.critical_unserved_kwh : delta)} <span>kWh</span>
          </div>
          {!shortage ? (
            <p className="battery-context">
              Stored at midnight: {num(result.baseline.metrics.final_soc_kwh)} →{" "}
              {num(m.final_soc_kwh)} kWh
            </p>
          ) : null}
          <p className="hero-explanation">
            {shortage
              ? "Scheduling alone cannot cover essential requirements under these constraints. Explore infrastructure changes below."
              : same
                ? `Complete the same ${num(m.flexible_served_kwh)} kWh of flexible work. ${delta > 1e-6 ? "The plan below uses available solar and reduces reliance on stored energy." : "Review the operating hours below; scheduling offers no extra stored energy in this case."}`
                : `Existing work: ${num(result.baseline.metrics.flexible_served_kwh)} kWh. LifeLine: ${num(m.flexible_served_kwh)} kWh. This is not a same-work improvement.`}
          </p>
        </CardContent>
        <CardFooter>
          <span className="small muted">
            {shortage
              ? "Remaining demand is explicit; no electricity guarantee."
              : c.heuristic_matches_optimizer_metrics
                ? "Sunshine-first matches the optimizer’s key metrics here."
                : "Compare the heuristic and all tradeoffs in detailed analysis."}
          </span>
        </CardFooter>
      </Card>
      <div className="metric-band supporting-metrics">
        <div>
          <span>Critical-load coverage</span>
          <strong>
            {m.critical_coverage_pct === null
              ? "N/A"
              : `${num(m.critical_coverage_pct, 1)}%`}
          </strong>
        </div>
        <div>
          <span>Flexible work completed</span>
          <strong>
            {num(m.flexible_served_kwh)} <small>kWh</small>
          </strong>
          <em>
            {same
              ? "Same work as existing schedule"
              : "Work completion differs"}
          </em>
        </div>
        <div>
          <span>Conversion loss reduction</span>
          <strong>
            {num(c.conversion_loss_reduction_kwh)} <small>kWh</small>
          </strong>
        </div>
      </div>
    </>
  );
}
