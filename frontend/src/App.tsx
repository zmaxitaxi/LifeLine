import { PlanSummary } from "@/components/PlanSummary";
import { ScheduleOverview } from "@/components/ScheduleOverview";
import { DetailedAnalysis } from "@/components/DetailedAnalysis";
import { ClinicConfiguration } from "@/components/ClinicConfiguration";
import { Disclosure } from "@/components/Disclosure";
import { Slider } from "@/components/ui/slider";
import { Badge } from "@/components/ui/badge";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Alert, AlertTitle, AlertDescription } from "@/components/ui/alert";
import { FormFields } from "@/components/FormFields";
import {
  NativeSelect,
  NativeSelectOption,
} from "@/components/ui/native-select";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useCallback, useEffect, useRef, useState } from "react";
import {
  Activity,
  ArrowRight,
  RotateCcw,
  Sun,
  BatteryCharging,
  Settings2,
  AlertTriangle,
  CheckCircle2,
} from "lucide-react";
import type {
  ScenarioSummary,
  SimulationResponse,
  ScenarioListResponse,
  SimulationRequest,
  EffectiveConfig,
} from "../../contracts/api";
import { api, fromPreset, requestFor, num, type Draft } from "./lib/clinic";
import { EquipmentEditor } from "./components/EquipmentEditor";
import { CapacityExplorer } from "./components/CapacityExplorer";
const statusLabel = {
  OK: "Within modeled limits",
  RESERVE_AT_RISK: "Reserve at risk",
  CRITICAL_SHORTAGE: "Critical energy shortage",
};
export default function App() {
  const [presets, setPresets] = useState<ScenarioSummary[]>([]);
  const [draft, setDraft] = useState<Draft | null>(null);
  const [result, setResult] = useState<SimulationResponse | null>(null);
  const [lastRequest, setLastRequest] = useState<SimulationRequest | null>(
    null,
  );
  const [dirty, setDirty] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const form = useRef<HTMLFormElement>(null);
  const controller = useRef<AbortController | null>(null);
  const sequence = useRef(0);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const run = useCallback(async (d: Draft) => {
    controller.current?.abort();
    const current = ++sequence.current;
    controller.current = new AbortController();
    setBusy(true);
    setError("");
    try {
      const payload = requestFor(d);
      const response = await api<SimulationResponse>(
        "simulate",
        payload,
        controller.current.signal,
      );
      if (current === sequence.current) {
        setResult(response);
        setLastRequest(payload);
        setDirty(false);
      }
    } catch (e) {
      if (
        e instanceof Error &&
        e.name !== "AbortError" &&
        current === sequence.current
      )
        setError(e.message);
    } finally {
      if (current === sequence.current) setBusy(false);
    }
  }, []);
  const initialize = useCallback(() => {
    setError("");
    api<ScenarioListResponse>("scenarios")
      .then((r) => {
        setPresets(r.scenarios);
        setDraft(fromPreset(r.scenarios.find((p) => p.id === "scheduling")!));
      })
      .catch((e) =>
        setError(
          `Cannot reach the local API. Start the backend and retry. ${e.message}`,
        ),
      );
  }, []);
  useEffect(() => {
    initialize();
    return () => controller.current?.abort();
  }, [initialize]);
  useEffect(() => {
    if (!draft) return;
    timer.current = setTimeout(() => {
      if (form.current?.checkValidity()) void run(draft);
    }, 650);
    return () => {
      if (timer.current) clearTimeout(timer.current);
    };
  }, [draft, run]);
  function edit(next: Draft) {
    controller.current?.abort();
    ++sequence.current;
    setBusy(false);
    setDirty(true);
    setDraft(next);
  }
  function config(key: keyof EffectiveConfig, value: number) {
    if (draft) edit({ ...draft, config: { ...draft.config, [key]: value } });
  }
  function choose(p: ScenarioSummary) {
    edit(fromPreset(p));
  }
  function exportResult() {
    if (!result) return;
    const blob = new Blob([JSON.stringify(result, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "lifeline-plan.json";
    a.click();
    URL.revokeObjectURL(url);
  }
  return (
    <>
      <header className="app-header">
        <a className="brand" href="#">
          <Activity size={25} strokeWidth={2.5} />
          <span>LifeLine</span>
        </a>
        <span className="header-description">Energy reliability planning</span>
        <span className="simulation-label">Decision-support prototype</span>
      </header>
      <div className="workflow">
        <span>01 Configure clinic</span>
        <ArrowRight size={13} />
        <a href="#schedule">02 Assess & schedule</a>
        <ArrowRight size={13} />
        <span>03 Compare & explore</span>
      </div>
      {error ? (
        <Alert variant="destructive" className="mx-auto my-3 max-w-5xl">
          <AlertTitle>Unable to calculate this plan</AlertTitle>
          <AlertDescription>
            {error}{" "}
            <Button
              type="button"
              onClick={() => (draft ? void run(draft) : initialize())}
            >
              Retry
            </Button>
          </AlertDescription>
        </Alert>
      ) : null}
      {!draft ? (
        <div className="loading" role="status">
          Connecting to the clinic planner…
        </div>
      ) : (
        <form
          ref={form}
          className="workspace"
          onSubmit={(e) => {
            e.preventDefault();
            if (timer.current) clearTimeout(timer.current);
            void run(draft);
          }}
        >
          <ClinicConfiguration>
            <div className="inspector-heading">
              <Settings2 size={18} />
              <h2>Configure clinic</h2>
              <Button
                type="button"
                variant="ghost"
                size="icon-sm"
                title="Reset selected quick start"
                aria-label="Reset selected quick start"
                onClick={() =>
                  choose(presets.find((p) => p.id === draft.scenario)!)
                }
              >
                <RotateCcw data-icon="inline-start" />
              </Button>
            </div>
            <label className="preset-label">
              Quick-start example
              <NativeSelect
                className="w-full"
                aria-label="Quick-start example"
                value={draft.scenario}
                onChange={(e) =>
                  choose(presets.find((p) => p.id === e.target.value)!)
                }
              >
                {presets.map((p) => (
                  <NativeSelectOption key={p.id} value={p.id}>
                    {p.name}
                  </NativeSelectOption>
                ))}
              </NativeSelect>
            </label>
            <p className="small muted">
              Examples are starting inputs. Edit any setting to calculate a new
              plan.
            </p>
            <div className="control-heading">
              <Sun size={16} />
              <h3>Energy infrastructure</h3>
            </div>
            <FormFields className="system-fields">
              {(
                [
                  ["pv_capacity_kw", "Solar capacity (kW)", 0, 100],
                  ["battery_capacity_kwh", "Battery capacity (kWh)", 0.1, 200],
                  ["initial_battery_kwh", "Current charge (kWh)", 0, 200],
                  ["reserve_kwh", "Reserve target (kWh)", 0, 200],
                ] as const
              ).map(([key, label, min, max]) => (
                <label key={key}>
                  {label}
                  <Input
                    aria-label={label}
                    type="number"
                    step="any"
                    min={min}
                    max={max}
                    value={
                      Number.isFinite(draft.config[key])
                        ? draft.config[key]
                        : ""
                    }
                    onChange={(e) => config(key, e.target.valueAsNumber)}
                    required
                  />
                </label>
              ))}
            </FormFields>
            <Disclosure
              className="advanced"
              title="Power limits & efficiencies"
            >
              <FormFields className="system-fields">
                {(
                  [
                    ["max_charge_kw", "Charge limit (kW)", 0, 100],
                    ["max_discharge_kw", "Discharge limit (kW)", 0, 100],
                    ["charge_efficiency", "Charge efficiency", 0.01, 1],
                    ["discharge_efficiency", "Discharge efficiency", 0.01, 1],
                  ] as const
                ).map(([key, label, min, max]) => (
                  <label key={key}>
                    {label}
                    <Input
                      aria-label={label}
                      type="number"
                      min={min}
                      max={max}
                      step="any"
                      value={
                        Number.isFinite(draft.config[key])
                          ? draft.config[key]
                          : ""
                      }
                      onChange={(e) => config(key, e.target.valueAsNumber)}
                      required
                    />
                  </label>
                ))}
              </FormFields>
            </Disclosure>
            <div className="weather-controls">
              <h3>Weather & adverse conditions</h3>
              <label>
                Representative weather
                <NativeSelect
                  className="w-full"
                  aria-label="Representative weather"
                  value={draft.dataset}
                  onChange={(e) =>
                    edit({
                      ...draft,
                      dataset: e.target.value as Draft["dataset"],
                      clouds:
                        e.target.value === "synthetic"
                          ? presets.find((p) => p.id === draft.scenario)!
                              .cloud_factors
                          : Array(24).fill(1),
                      weather: 100,
                    })
                  }
                >
                  <NativeSelectOption value="synthetic">
                    Synthetic scenario curve
                  </NativeSelectOption>
                  <NativeSelectOption value="kisumu-2025-01-14">
                    Kisumu · NASA · 14 Jan 2025
                  </NativeSelectOption>
                </NativeSelect>
              </label>
              <div className="sunshine-slider">
                <label id="sunshine-label">
                  Available sunshine <strong>{draft.weather}%</strong>
                </label>
                <Slider
                  aria-labelledby="sunshine-label"
                  thumbLabel="Available sunshine"
                  min={0}
                  max={100}
                  step={5}
                  value={[draft.weather]}
                  onValueChange={(value) =>
                    edit({
                      ...draft,
                      weather: Array.isArray(value) ? value[0] : value,
                    })
                  }
                />
              </div>
              <Button
                variant="outline"
                size="sm"
                type="button"
                onClick={() => edit({ ...draft, weather: 25 })}
              >
                Test 25% sunshine
              </Button>
              <p className="small muted">
                Changes weather only; equipment and starting battery stay fixed.
              </p>
            </div>
            <EquipmentEditor
              equipment={draft.equipment}
              onChange={(equipment) => edit({ ...draft, equipment })}
            />
            <div className="generate">
              <Button
                className="w-full"
                size="lg"
                type="submit"
                disabled={busy}
              >
                {busy ? "Calculating…" : "Generate schedule"}
                <ArrowRight data-icon="inline-end" />
              </Button>
              <span className="small muted">
                Valid edits recalculate automatically.
              </span>
            </div>
          </ClinicConfiguration>
          <main className="main-content">
            <div className="page-heading">
              <div>
                <h1>Clinic energy plan</h1>
                <p>
                  Essential requirements first. Then put flexible work where
                  energy is available.
                </p>
              </div>
              {result ? (
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={exportResult}
                  disabled={dirty || busy}
                >
                  Export JSON
                </Button>
              ) : null}
            </div>
            <div className="results-state" role="status" aria-live="polite">
              {busy
                ? "Recalculating from your clinic inputs…"
                : dirty
                  ? "Inputs changed. Generate a valid new schedule to update these results."
                  : "Plan calculated from current inputs."}
            </div>
            {result ? (
              <div
                aria-busy={busy}
                className={dirty ? "results stale" : "results"}
              >
                <section
                  className={`assessment ${result.status.toLowerCase()}`}
                >
                  <div>
                    {result.status === "OK" ? (
                      <CheckCircle2 size={23} />
                    ) : (
                      <AlertTriangle size={23} />
                    )}
                    <Badge
                      variant={
                        result.status === "CRITICAL_SHORTAGE"
                          ? "destructive"
                          : "secondary"
                      }
                    >
                      {statusLabel[result.status]}
                    </Badge>
                  </div>
                  <p>
                    {result.status === "OK"
                      ? "Essential demand is covered in this model. Review the recommendation below."
                      : result.diagnosis.explanation}
                  </p>
                  {result.diagnosis.constraints.length ? (
                    <p className="small">
                      Identified:{" "}
                      {result.diagnosis.constraints
                        .join(" · ")
                        .replaceAll("_", " ")
                        .toLowerCase()}
                    </p>
                  ) : null}
                </section>
                <PlanSummary result={result} />
                <ScheduleOverview result={result} />
                <DetailedAnalysis result={result} />
                {lastRequest && !dirty ? (
                  <CapacityExplorer
                    key={JSON.stringify(lastRequest)}
                    base={result}
                    request={lastRequest}
                  />
                ) : null}
                <Card className="section recommendations">
                  <CardHeader>
                    <span className="section-number">05 / UNDERSTAND</span>
                    <CardTitle>
                      <h2>Decisions & remaining limits</h2>
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    {result.recommendations
                      .filter((r) => r.severity !== "info" || r.task_id)
                      .map((r, i) => (
                        <article key={i} className={r.severity}>
                          <h3>{r.title}</h3>
                          <p>{r.explanation}</p>
                        </article>
                      ))}
                    <Disclosure
                      title={`All plan warnings (${result.warnings.length})`}
                    >
                      {result.warnings.map((w, i) => (
                        <p key={i}>
                          <strong>{w.plan}: </strong>
                          {w.message}
                        </p>
                      ))}
                    </Disclosure>
                  </CardContent>
                </Card>
                <Card className="section sources">
                  <CardHeader>
                    <CardTitle>
                      <h2>Assumptions & data sources</h2>
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p>
                      <strong>Equipment:</strong>{" "}
                      {result.input_provenance.equipment.replaceAll("_", " ")}.
                      All demo clinic demand is illustrative, not measured
                      facility consumption.
                    </p>
                    <p>
                      <strong>Weather:</strong>{" "}
                      {result.weather_dataset === "synthetic"
                        ? "Synthetic daylight curve."
                        : "NASA POWER historical satellite-derived irradiance, Kisumu (−0.0917°, 34.768°), 14 January 2025. Hourly UTC converted to EAT; Wh/m² divided by 1000. Horizontal irradiance approximates PV input; tilt and shading are omitted."}
                    </p>
                    <p>
                      <a
                        href="https://power.larc.nasa.gov/docs/services/api/temporal/hourly/"
                        target="_blank"
                        rel="noreferrer"
                      >
                        NASA POWER documentation
                      </a>{" "}
                      ·{" "}
                      <a
                        href="https://www.seforall.org/publications/medical-appliances-for-resource-constrained-settings"
                        target="_blank"
                        rel="noreferrer"
                      >
                        SEforALL / CLASP equipment study
                      </a>
                    </p>
                    <Disclosure title="View all modeling assumptions">
                      {result.assumptions.map((a, i) => (
                        <p key={i}>{a}</p>
                      ))}
                    </Disclosure>
                    <p className="small">
                      Flexible work is divisible and interruptible. This model
                      does not capture medical appliance cycles, refrigeration
                      temperature, voltage quality, degradation, or future
                      weather uncertainty.
                    </p>
                  </CardContent>
                </Card>
              </div>
            ) : (
              <div className="empty-plan">
                <BatteryCharging size={40} />
                <h2>Ready to assess your clinic</h2>
                <p>
                  Configure the system and equipment, then generate a schedule.
                </p>
              </div>
            )}
            <footer>
              Illustrative simulation; not for clinical or operational use. No
              medical equipment control or electricity guarantee.
              <br />
              SDG 7.1 · Reliable energy access &nbsp; / &nbsp; SDG 3.8 ·
              Essential health services
            </footer>
          </main>
        </form>
      )}
    </>
  );
}
