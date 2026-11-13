import { Download } from "lucide-react";
import { Button } from "@/components/ui/button";
import { DetailedAnalysis } from "@/components/DetailedAnalysis";
import { PlanSummary } from "@/components/PlanSummary";
import { ScheduleOverview } from "@/components/ScheduleOverview";
import { CapacityExplorer } from "@/components/CapacityExplorer";
import { Disclosure } from "@/components/Disclosure";
import type {
  SimulationRequest,
  SimulationResponse,
} from "../../../contracts/api";

export default function TechnicalResults({
  result,
  request,
}: {
  result: SimulationResponse;
  request: SimulationRequest;
}) {
  function exportResult() {
    const url = URL.createObjectURL(
      new Blob([JSON.stringify(result, null, 2)], { type: "application/json" }),
    );
    const a = document.createElement("a");
    a.href = url;
    a.download = "lifeline-plan.json";
    a.click();
    URL.revokeObjectURL(url);
  }
  return (
    <section
      className="technical-results"
      aria-label="Computed technical results"
    >
      <div className="section-heading">
        <h2>Computed results</h2>
        <Button type="button" variant="outline" onClick={exportResult}>
          <Download data-icon="inline-start" />
          Export JSON
        </Button>
      </div>
      <PlanSummary result={result} />
      <ScheduleOverview result={result} />
      <DetailedAnalysis result={result} />
      <CapacityExplorer
        key={JSON.stringify(request)}
        base={result}
        request={request}
      />
      <Disclosure title={`All schedule warnings (${result.warnings.length})`}>
        {result.warnings.map((w, i) => (
          <p key={i}>
            <strong>{w.plan}:</strong> {w.message}
          </p>
        ))}
      </Disclosure>
      <Disclosure title="All modeling assumptions">
        {result.assumptions.map((a, i) => (
          <p key={i}>{a}</p>
        ))}
      </Disclosure>
    </section>
  );
}
