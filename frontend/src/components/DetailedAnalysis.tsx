import { lazy, Suspense } from "react";
import type { SimulationResponse } from "../../../contracts/api";
import { Schedules, ComparisonTable } from "./Schedules";
const EnergyCharts = lazy(() =>
  import("./EnergyCharts").then((m) => ({ default: m.EnergyCharts })),
);
export function DetailedAnalysis({
  result,
  idPrefix = "",
}: {
  result: SimulationResponse;
  idPrefix?: string;
}) {
  return (
    <section
      className="detailed-analysis"
      aria-label="Detailed technical results"
    >
      <Schedules result={result} id={`${idPrefix}detailed-schedule`} />
      <Suspense fallback={<p>Loading battery forecasts…</p>}>
        <EnergyCharts result={result} />
      </Suspense>
      <ComparisonTable result={result} />
    </section>
  );
}
