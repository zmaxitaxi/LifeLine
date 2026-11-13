import { lazy, Suspense } from "react";
import { ChevronDown } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import type { SimulationResponse } from "../../../contracts/api";
import { Schedules, ComparisonTable } from "./Schedules";
const EnergyCharts = lazy(() =>
  import("./EnergyCharts").then((m) => ({ default: m.EnergyCharts })),
);
export function DetailedAnalysis({ result }: { result: SimulationResponse }) {
  return (
    <Collapsible className="detailed-analysis">
      <CollapsibleTrigger
        render={<Button variant="outline" className="w-full justify-between" />}
      >
        <span>
          Detailed analysis · full timeline, forecasts & sunshine-first
        </span>
        <ChevronDown data-icon="inline-end" />
      </CollapsibleTrigger>
      <CollapsibleContent>
        <Schedules result={result} />
        <Suspense fallback={<p>Loading battery forecasts…</p>}>
          <EnergyCharts result={result} />
        </Suspense>
        <ComparisonTable result={result} />
      </CollapsibleContent>
    </Collapsible>
  );
}
