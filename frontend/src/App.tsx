import {
  lazy,
  Suspense,
  useCallback,
  useEffect,
  useRef,
  useState,
} from "react";
import { Activity, ArrowLeft, LoaderCircle, Settings2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  NativeSelect,
  NativeSelectOption,
} from "@/components/ui/native-select";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Disclosure } from "@/components/Disclosure";
import { PlanningHome, type ChatMessage } from "@/components/PlanningHome";
import { WeatherContext } from "@/components/WeatherContext";
import { SimplePlan } from "@/components/SimplePlan";
import { QuickRequirements } from "@/components/QuickRequirements";
import { AdvancedSettings } from "@/components/AdvancedSettings";
import { EquipmentEditor } from "@/components/EquipmentEditor";
import {
  api,
  clinicNames,
  draftProblem,
  fromPreset,
  fromResult,
  requestFor,
  validDraft,
  type Draft,
} from "@/lib/clinic";
import type {
  AssistantResponse,
  PlanningQuestion,
  PlanningStatus,
  ScenarioListResponse,
  ScenarioSummary,
  SimulationRequest,
  SimulationResponse,
} from "../../contracts/api";
import type { AgentStatus } from "../../contracts/agent";

const TechnicalResults = lazy(() => import("@/components/TechnicalResults"));
type View = "simple" | "detailed" | "advanced";

export default function App() {
  const [presets, setPresets] = useState<ScenarioSummary[]>([]);
  const [draft, setDraft] = useState<Draft | null>(null);
  const [view, setView] = useState<View>("simple");
  const [result, setResult] = useState<SimulationResponse | null>(null);
  const [lastRequest, setLastRequest] = useState<SimulationRequest | null>(
    null,
  );
  const [status, setStatus] = useState<PlanningStatus | null>(null);
  const [statusError, setStatusError] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [forecastQuestion, setForecastQuestion] = useState<{
    text: string;
    id: number;
  } | null>(null);
  const [usingForecast, setUsingForecast] = useState(false);
  const [localAIAvailable, setLocalAIAvailable] = useState(false);
  const [pending, setPending] = useState<PlanningQuestion | null>(null);
  const [dirty, setDirty] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [quickEdit, setQuickEdit] = useState(false);
  const [initializing, setInitializing] = useState(true);
  const controller = useRef<AbortController | null>(null);
  const sequence = useRef(0);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const initialize = useCallback(async () => {
    setInitializing(true);
    setError("");
    const outcomes = await Promise.allSettled([
      api<ScenarioListResponse>("scenarios"),
      api<PlanningStatus>("planning-status"),
      api<AgentStatus>("agent/status"),
    ]);
    if (outcomes[0].status === "fulfilled") {
      const list = outcomes[0].value.scenarios;
      const first = list.find((p) => p.id === "scheduling") ?? list[0];
      if (first) {
        setPresets(list);
        setDraft(fromPreset(first));
      } else
        setError("There are no clinic examples available. Please try again.");
    } else
      setError(
        "The clinic examples could not be loaded. Check that the local planner is running, then retry.",
      );
    if (outcomes[1].status === "fulfilled") {
      setStatus(outcomes[1].value);
      setStatusError(false);
    } else setStatusError(true);
    setLocalAIAvailable(
      outcomes[2].status === "fulfilled" && outcomes[2].value.available,
    );
    setInitializing(false);
  }, []);
  useEffect(() => {
    void initialize();
    return () => {
      controller.current?.abort();
      if (timer.current) clearTimeout(timer.current);
    };
  }, [initialize]);

  function invalidate() {
    if (timer.current) clearTimeout(timer.current);
    controller.current?.abort();
    ++sequence.current;
    setBusy(false);
  }
  const run = useCallback(async (d: Draft) => {
    controller.current?.abort();
    const current = ++sequence.current;
    const abort = new AbortController();
    controller.current = abort;
    setBusy(true);
    setError("");
    setPending(null);
    setMessages([]);
    setDirty(true);
    try {
      const payload = requestFor(d);
      const response = await api<SimulationResponse>(
        "simulate",
        payload,
        abort.signal,
      );
      if (sequence.current !== current) return;
      setResult(response);
      setLastRequest(payload);
      setDirty(false);
    } catch (e) {
      if (
        e instanceof Error &&
        e.name !== "AbortError" &&
        sequence.current === current
      )
        setError(e.message);
    } finally {
      if (sequence.current === current) setBusy(false);
    }
  }, []);

  function edit(next: Draft) {
    setUsingForecast(false);
    invalidate();
    setDraft(next);
    setDirty(true);
    setError("");
    setPending(null);
    setMessages([]);
    if (result && validDraft(next))
      timer.current = setTimeout(() => void run(next), 650);
  }
  function choose(id: string) {
    setUsingForecast(false);
    const selected = presets.find((p) => p.id === id);
    if (!selected) return;
    invalidate();
    setDraft(fromPreset(selected));
    setResult(null);
    setLastRequest(null);
    setMessages([]);
    setPending(null);
    setDirty(false);
    setError("");
    setQuickEdit(false);
    setView("simple");
  }
  async function ask(message: string, followup = false) {
    if (!draft) return;
    if (!validDraft(draft)) {
      setError(
        "Please correct the equipment and battery information before making a plan. Charge and reserve must fit within battery capacity; equipment needs valid power, hours, and a name.",
      );
      return;
    }
    invalidate();
    const current = ++sequence.current;
    const abort = new AbortController();
    controller.current = abort;
    const question = followup ? pending : null;
    if (
      !question &&
      (/\bforecasts?\b/i.test(message) ||
        usingForecast ||
        (localAIAvailable && draft.dataset !== "kisumu-2025-01-14"))
    ) {
      setBusy(false);
      setError("");
      setView("simple");
      setPending(null);
      setForecastQuestion({ text: message, id: Date.now() });
      setMessages((prev) => [
        ...prev,
        { role: "user", text: message },
        {
          role: "assistant",
          text: "In the live-weather panel, review the clinic location, equipment and assumed charge at local midnight, then calculate the plan. Local AI can select validated planning tools when Ollama is running; guided fallback remains available.",
        },
      ]);
      return;
    }
    setBusy(true);
    setError("");
    setView("simple");
    setDirty(!!result);
    setMessages((prev) => [...prev, { role: "user", text: message }]);
    try {
      const response = await api<AssistantResponse>(
        "assistant",
        { message, plan: requestFor(draft), pending: question },
        abort.signal,
      );
      if (current !== sequence.current) return;
      setMessages((prev) => [
        ...prev,
        { role: "assistant", text: response.message },
      ]);
      setPending(response.question);
      if (response.result && response.request) {
        const next = fromResult(response.result);
        next.dataset = response.request.weather_dataset ?? "synthetic";
        setDraft(next);
        setResult(response.result);
        setLastRequest(response.request);
        setDirty(false);
        requestAnimationFrame(() => {
          document.getElementById("plan-title")?.focus();
        });
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
  }
  function changeView(next: View) {
    setView(next);
    requestAnimationFrame(() => {
      const panel = document.getElementById(`${next}-view`);
      if (panel && !panel.contains(document.activeElement)) panel.focus();
    });
  }
  async function loadCompetingExample() {
    invalidate();
    const current = ++sequence.current;
    const abort = new AbortController();
    controller.current = abort;
    setBusy(true);
    setError("");
    setMessages([]);
    setPending(null);
    setUsingForecast(false);
    setDirty(true);
    try {
      const demo = await api<{
        request: SimulationRequest;
        description: string;
        limitations: string[];
      }>("demos/competing-windows", undefined, abort.signal);
      const response = await api<SimulationResponse>(
        "simulate",
        demo.request,
        abort.signal,
      );
      if (current !== sequence.current) return;
      const next = fromResult(response);
      next.dataset = "kisumu-2025-01-14";
      setDraft(next);
      setResult(response);
      setLastRequest(demo.request);
      setDirty(false);
      setMessages([
        {
          role: "assistant",
          text: [demo.description, ...demo.limitations].join(" "),
        },
      ]);
      setView("detailed");
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
  }
  const valid = draft ? validDraft(draft) : false;
  const problem = draft ? draftProblem(draft) : null;
  const currentResult = !dirty ? result : null;
  return (
    <>
      <a className="skip-link" href="#main">
        Skip to clinic planner
      </a>
      <header className="app-header">
        <a
          className="brand"
          href="#main"
          onClick={() => setView("simple")}
          aria-label="LifeLine home"
        >
          <Activity size={28} strokeWidth={2} />
          <span>LifeLine</span>
        </a>
        <nav aria-label="Planning views">
          <Button
            type="button"
            variant={view === "simple" ? "secondary" : "ghost"}
            aria-pressed={view === "simple"}
            onClick={() => changeView("simple")}
          >
            Simple mode
          </Button>
          <Button
            type="button"
            variant={view === "detailed" ? "secondary" : "ghost"}
            aria-pressed={view === "detailed"}
            onClick={() => changeView("detailed")}
          >
            Detailed mode
          </Button>
          <Button
            type="button"
            variant={view === "advanced" ? "secondary" : "ghost"}
            aria-pressed={view === "advanced"}
            onClick={() => changeView("advanced")}
          >
            <Settings2 data-icon="inline-start" />
            Advanced settings
          </Button>
        </nav>
      </header>
      <main id="main" className="clinic-workspace">
        {initializing ? (
          <p className="loading" role="status">
            <LoaderCircle className="loading-spin" />
            Loading your clinic planner…
          </p>
        ) : null}
        {error ? (
          <Alert variant="destructive" className="planner-error" role="alert">
            <AlertTitle>
              {draft
                ? "This plan could not be updated"
                : "LifeLine could not connect"}
            </AlertTitle>
            <AlertDescription>
              <p>{error}</p>
              <Button
                type="button"
                variant="outline"
                disabled={busy || (!!draft && !valid)}
                onClick={() =>
                  draft ? valid && void run(draft) : void initialize()
                }
              >
                {draft ? "Retry with local planner" : "Retry"}
              </Button>
              {draft ? (
                <p>
                  The local planner checks the entered requirements. Any
                  unanswered conversation request will still need to be entered.
                </p>
              ) : null}
            </AlertDescription>
          </Alert>
        ) : null}
        {draft ? (
          <>
            <section className="clinic-context" aria-label="Selected clinic">
              <label className="clinic-selector">
                Choose a clinic
                <NativeSelect
                  className="w-full"
                  aria-label="Choose a clinic"
                  value={draft.scenario}
                  onChange={(e) => choose(e.target.value)}
                >
                  {presets.map((p) => (
                    <NativeSelectOption key={p.id} value={p.id}>
                      {clinicNames[p.id]}
                    </NativeSelectOption>
                  ))}
                </NativeSelect>
              </label>
              <h1>{clinicNames[draft.scenario]}</h1>
              <p>Equipment profile · choose the forecast location below</p>
            </section>
            <WeatherContext
              draft={draft}
              status={status}
              statusError={statusError}
              result={currentResult}
              onChange={edit}
              forecastQuestion={forecastQuestion}
              onForecastAnswer={(answer) => {
                setUsingForecast(true);
                setResult(null);
                setLastRequest(null);
                setDirty(false);
                setPending(null);
                setMessages((prev) => [
                  ...prev,
                  { role: "assistant", text: answer },
                ]);
              }}
            />
            {problem ? (
              <Alert variant="destructive" className="requirements-error">
                <AlertTitle>Check one requirement</AlertTitle>
                <AlertDescription>{problem}</AlertDescription>
              </Alert>
            ) : null}
            <div
              className={`planning-state ${!busy && !result && !pending && !error ? "quiet-state" : ""}`}
              role="status"
              aria-live="polite"
            >
              {busy ? (
                <>
                  <LoaderCircle className="loading-spin" />
                  Checking the equipment, battery, and available energy…
                </>
              ) : error ? (
                "No updated plan is available. Review the error above and retry."
              ) : pending ? (
                "One question before updating your plan. Any previous plan is hidden."
              ) : dirty && result ? (
                valid ? (
                  "Requirements changed. The previous plan is hidden while LifeLine recalculates."
                ) : (
                  "Please correct the requirements. The previous plan is hidden until a new plan can be calculated."
                )
              ) : result ? (
                "Plan calculated from current inputs."
              ) : (
                ""
              )}
            </div>
            {view === "simple" ? (
              <div id="simple-view" tabIndex={-1} className="view-content">
                <PlanningHome
                  busy={busy}
                  messages={messages}
                  pending={pending}
                  hasPlan={!!result}
                  onAsk={(text, followup) => void ask(text, followup)}
                  onCancel={() => {
                    setPending(null);
                    setMessages([]);
                    if (result) void run(draft);
                  }}
                />
                {quickEdit ? (
                  <QuickRequirements
                    draft={draft}
                    onChange={edit}
                    onDetails={() => changeView("detailed")}
                    onClose={() => setQuickEdit(false)}
                  />
                ) : null}
                {currentResult ? (
                  <SimplePlan
                    result={currentResult}
                    onDetails={() => changeView("detailed")}
                    onChange={() => {
                      setQuickEdit(true);
                      requestAnimationFrame(() =>
                        document
                          .getElementById("requirements-title")
                          ?.scrollIntoView({ block: "center" }),
                      );
                    }}
                  />
                ) : null}
              </div>
            ) : (
              <div
                id={`${view}-view`}
                tabIndex={-1}
                className="view-content secondary-view"
              >
                <Button
                  type="button"
                  variant="link"
                  onClick={() => changeView("simple")}
                >
                  <ArrowLeft data-icon="inline-start" />
                  Back to your simple plan
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  disabled={busy}
                  onClick={() => void loadCompetingExample()}
                >
                  Load competing-window example
                </Button>
                <form
                  onSubmit={(e) => {
                    e.preventDefault();
                    if (valid) void run(draft);
                  }}
                >
                  {view === "advanced" ? (
                    <AdvancedSettings
                      draft={draft}
                      result={currentResult}
                      onChange={edit}
                      onReset={() => {
                        const p = presets.find((p) => p.id === draft.scenario);
                        if (p) edit(fromPreset(p));
                      }}
                    />
                  ) : (
                    <>
                      <div className="detailed-heading">
                        <h2>Detailed mode</h2>
                        <p>
                          Review equipment requirements, battery forecasts,
                          schedule comparisons, and alternative scenarios.
                        </p>
                      </div>
                      <EquipmentEditor
                        equipment={draft.equipment}
                        onChange={(equipment) => edit({ ...draft, equipment })}
                      />
                    </>
                  )}
                  <Button type="submit" size="lg" disabled={busy || !valid}>
                    {busy
                      ? "Calculating…"
                      : result
                        ? "Recalculate plan"
                        : "Calculate a plan"}
                  </Button>
                </form>
                {view === "detailed" && currentResult && lastRequest ? (
                  <Suspense
                    fallback={<p role="status">Loading detailed results…</p>}
                  >
                    <TechnicalResults
                      result={currentResult}
                      request={lastRequest}
                    />
                  </Suspense>
                ) : null}
                {view === "detailed" && !result ? (
                  <p className="detail-empty">
                    Review the clinic’s requirements above, then calculate a
                    plan to see the comparisons.
                  </p>
                ) : null}
              </div>
            )}
            <footer className="planner-footer">
              <p>
                Demonstration clinic. Review equipment and battery information
                before relying on a plan. LifeLine does not measure live power
                or control equipment.
              </p>
              <Disclosure title="Assumptions and data sources">
                <p>
                  All example clinics and equipment are illustrative. Entered
                  values are unverified. Live weather planning uses Open-Meteo;
                  a hosted AI model is not connected. The local assistant uses
                  supported requests and the same simulator and optimizer as
                  Detailed mode.
                </p>
                <p>
                  Historical weather: NASA POWER satellite-derived irradiance
                  for Kisumu, 14 January 2025. It is not a clinic measurement or
                  a forecast. Synthetic sunshine uses a fixed daylight curve.
                  Live forecast dates, retrieval times and timezone are
                  displayed in the live-weather planner when retrieved.
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
                    Equipment study
                  </a>
                </p>
                <p>
                  This prototype does not model refrigeration temperature,
                  voltage quality, sub-hour surges, degradation, or validated
                  medical appliance cycles. No safety or availability guarantee.
                  Illustrative simulation; not for clinical or operational use.
                </p>
              </Disclosure>
            </footer>
          </>
        ) : null}
      </main>
    </>
  );
}
