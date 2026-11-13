import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter,
} from "@/components/ui/card";
import { FormFields } from "@/components/FormFields";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useEffect, useRef, useState } from "react";
import type {
  SimulationRequest,
  SimulationResponse,
} from "../../../contracts/api";
import { api, num } from "../lib/clinic";
export function CapacityExplorer({
  base,
  request,
}: {
  base: SimulationResponse;
  request: SimulationRequest;
}) {
  const [proposal, setProposal] = useState({
    pv_capacity_kw: base.effective_config.pv_capacity_kw,
    battery_capacity_kwh: base.effective_config.battery_capacity_kwh,
    initial_battery_kwh: base.effective_config.initial_battery_kwh,
    max_discharge_kw: base.effective_config.max_discharge_kw,
  });
  const [result, setResult] = useState<SimulationResponse | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const sequence = useRef(0);
  useEffect(() => {
    const current = ++sequence.current;
    setResult(null);
    setError("");
    const controller = new AbortController();
    const timer = setTimeout(() => {
      setBusy(true);
      api<SimulationResponse>(
        "simulate",
        { ...request, ...proposal },
        controller.signal,
      )
        .then((r) => {
          if (current === sequence.current) setResult(r);
        })
        .catch((e) => {
          if (e.name !== "AbortError" && current === sequence.current)
            setError(e.message);
        })
        .finally(() => {
          if (current === sequence.current) setBusy(false);
        });
    }, 500);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [proposal, request]);
  return (
    <Card className="section explorer" id="capacity">
      <CardHeader className="p-0">
        <div className="section-heading">
          <div>
            <span className="section-number">04 / EXPLORE</span>
            <CardTitle>
              <h2>What would change the outcome?</h2>
            </CardTitle>
          </div>
        </div>
        <CardDescription>
          Test a proposal against this exact clinic, weather, and equipment.
          Stored energy and output power are different constraints.
        </CardDescription>
      </CardHeader>
      <CardContent className="p-0">
        <FormFields className="explorer-controls">
          {(
            [
              ["pv_capacity_kw", "Proposed solar (kW)", 100],
              ["battery_capacity_kwh", "Proposed battery (kWh)", 200],
              ["initial_battery_kwh", "Proposed initial charge (kWh)", 200],
              ["max_discharge_kw", "Proposed output limit (kW)", 100],
            ] as const
          ).map(([key, label, max]) => (
            <label key={key}>
              {label}
              <Input
                type="number"
                aria-label={label}
                min={key === "battery_capacity_kwh" ? 0.1 : 0}
                max={max}
                step="any"
                value={Number.isFinite(proposal[key]) ? proposal[key] : ""}
                onChange={(e) =>
                  setProposal((p) => ({ ...p, [key]: e.target.valueAsNumber }))
                }
              />
            </label>
          ))}
        </FormFields>
        {error ? (
          <p role="alert" className="error">
            {error}
          </p>
        ) : null}
        {busy ? <p role="status">Recalculating the proposed system…</p> : null}
        {result && !busy ? (
          <div className="explorer-result">
            <div>
              <span className="small muted">
                Unmet critical energy · current → proposed
              </span>
              <strong>
                {num(base.optimized.metrics.critical_unserved_kwh)} →{" "}
                {num(result.optimized.metrics.critical_unserved_kwh)}{" "}
                <small>kWh</small>
              </strong>
            </div>
            <div>
              <span className="small muted">Proposed critical coverage</span>
              <strong>
                {result.optimized.metrics.critical_coverage_pct === null
                  ? "N/A"
                  : `${num(result.optimized.metrics.critical_coverage_pct, 1)}%`}
              </strong>
            </div>
            <p data-testid="capacity-outcome">{result.diagnosis.explanation}</p>
            <p className="small">
              Remaining constraints:{" "}
              {result.diagnosis.constraints
                .join(", ")
                .replaceAll("_", " ")
                .toLowerCase() || "none identified in this model"}
              .
            </p>
          </div>
        ) : null}
      </CardContent>
      <CardFooter>
        <p className="small muted">
          A model comparison, not certified system sizing, installation advice,
          or a procurement recommendation. No cost estimates.
        </p>
      </CardFooter>
    </Card>
  );
}
