import { useEffect, useLayoutEffect, useRef, useState } from "react";
import {
  ArrowUp,
  CloudSun,
  LoaderCircle,
  MapPin,
  RefreshCw,
  AlertTriangle,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Disclosure } from "@/components/Disclosure";
import { api, num } from "@/lib/clinic";
import type { AgentStatus } from "../../contracts/agent";
import type { ActivityProposal, ComputedPlan } from "../../contracts/planning";
import {
  Workspace,
  useWorkspaceNavigation,
} from "@/features/planning/Workspace";
import { usePlanningSession } from "@/features/planning/usePlanningSession";
import { planningApi } from "@/features/planning/planning-api";
import { ActivityConfirmation } from "@/features/planning/ActivityConfirmation";
import { ActivitiesSection } from "@/features/planning/ActivitiesSection";
import { WeatherSection } from "@/features/planning/WeatherSection";
import { SolutionsSection } from "@/features/planning/SolutionsSection";
import { BatterySummary } from "@/features/planning/BatterySummary";
import { AddEquipment } from "@/features/planning/AddEquipment";
import { InlinePlan } from "@/features/planning/InlinePlan";

interface Message {
  id: string;
  role: "user" | "assistant" | "notice";
  text: string;
  tools?: string[];
  inputRevision?: number;
  plan?: ComputedPlan;
  date?: string;
  sessionId?: string;
  retryQuestion?: string;
  selectionId?: string;
}
const toolLabels: Record<string, string> = {
  conversational_reply: "Answered your message",
  explain_current_plan: "Reviewed the selected plan",
  inspect_planning_state: "Reviewed the clinic details",
  review_activity_proposal: "Prepared the activity for review",
  propose_activity: "Prepared an activity draft",
  update_activity_draft: "Updated the activity draft",
  propose_activity_revision: "Prepared an activity change",
  correct_last_activity_time: "Corrected the operating time",
  recompute_clinic_plan: "Calculated the plan and checked the weather",
};
const planQuestion =
  "Calculate the clinic’s electricity plan and compare recovery options. Describe the proposed actions and remaining limitations for clinic staff in plain English.";
export default function App() {
  const session = usePlanningSession();
  const { state, busy } = session;
  const route = useWorkspaceNavigation();
  const [messages, setMessages] = useState<Message[]>([]);
  const [text, setText] = useState("");
  const [equipmentOpen, setEquipmentOpen] = useState(false);
  const [agent, setAgent] = useState<AgentStatus | null>(null);
  const [modelError, setModelError] = useState(false);
  const [narrationPending, setNarrationPending] = useState(false);
  const [replyReady, setReplyReady] = useState(true);
  const [locations, setLocations] = useState<
    { name: string; latitude: number; longitude: number }[]
  >([]);
  const transcript = useRef<HTMLDivElement>(null);
  const input = useRef<HTMLTextAreaElement>(null);
  const following = useRef(true);
  const confirmationKeys = useRef(new Map<string, string>());
  const computed = narrationPending ? null : session.computed;
  const activeProposal = state?.proposals.find(
    (p) => p.id === state.active_proposal_id && p.status === "draft",
  );
  const recovery = computed?.recovery;
  const selected = recovery ? [recovery.existing, ...recovery.options].find(option => option.id === (state?.selected_recovery_intervention_id ?? recovery.existing.id)) ?? recovery.existing : undefined;
  const latestPlanMessageId = messages.filter(item => item.plan).at(-1)?.id;
  const addMessage = (message: Omit<Message, "id">) =>
    setMessages((items) => [...items, { id: crypto.randomUUID(), ...message }]);
  async function checkModel() {
    setModelError(false);
    try {
      setAgent(await api<AgentStatus>("agent/status"));
    } catch {
      setModelError(true);
    }
  }
  useEffect(() => {
    void checkModel();
    void api<{
      locations: { name: string; latitude: number; longitude: number }[];
    }>("forecast/locations")
      .then((data) => setLocations(data.locations))
      .catch(() => {});
  }, []);
  useLayoutEffect(() => {
    if (following.current && transcript.current)
      transcript.current.scrollTop = transcript.current.scrollHeight;
  }, [messages, busy, computed, state?.revision]);
  function focusChat(prefill = "") {
    location.hash = "assistant";
    setText(prefill);
    requestAnimationFrame(() => input.current?.focus());
  }
  async function say(question: string, showUser = true) {
    if (!question.trim() || busy || !session.stateRef.current) return;
    following.current = true;
    setText("");
    setReplyReady(false);
    if (showUser) addMessage({ role: "user", text: question });
    const before = session.stateRef.current.computed_plan;
    const response = await session.run(
      "LifeLine is preparing your response…",
      (s) => planningApi.ask(s, question),
      (r) => r.state,
      true,
    );
    if (response?.mode === "local_tool_agent") {
      const result = response.state.computed_plan;
      const newPlan =
        response.state.plan_status === "current" &&
        result?.input_revision === response.state.input_revision &&
        (response.tool_calls.includes("explain_current_plan") || !before ||
          before.generation !== result.generation ||
          before.input_revision !== result.input_revision ||
          before.computed_at !== result.computed_at);
      addMessage({
        role: "assistant",
        text: response.message,
        tools: response.tool_calls,
        inputRevision: response.state.input_revision,
        ...(newPlan
          ? {
              plan: result!,
              date: response.state.planning_date,
              sessionId: response.state.id,
              selectionId: response.tool_calls.includes("explain_current_plan") ? response.state.selected_recovery_intervention_id ?? response.state.computed_plan?.recovery?.existing.id : undefined,
            }
          : {}),
      });
      setReplyReady(true);
    } else if (response) {
      addMessage({
        role: "notice",
        text: "The local assistant couldn’t finish this reply. Please retry.",
        retryQuestion: question,
      });
    } else {
      addMessage({
        role: "notice",
        text: "The reply could not be completed.",
        retryQuestion: question,
      });
    }
    requestAnimationFrame(() => input.current?.focus());
  }
  function requestPlan(question = planQuestion) {
    location.hash = "assistant";
    void say(question);
  }
  async function confirm(proposal: ActivityProposal) {
    setNarrationPending(true);
    setReplyReady(false);
    let key = confirmationKeys.current.get(proposal.id);
    if (!key) {
      key = crypto.randomUUID();
      confirmationKeys.current.set(proposal.id, key);
    }
    const response = await session.run(
      "Confirming your activity…",
      (s) => planningApi.confirm(s, proposal.id, key!),
      (s) => s,
      true,
    );
    if (response) {
      addMessage({
        role: "notice",
        text:
          response.plan_status === "failed"
            ? "Activity confirmed. The energy calculation needs to be retried."
            : "Activity confirmed.",
      });
      await say(
        "Calculate recovery options for the activity just confirmed. Describe the updated electricity plan and next actions to clinic staff in plain English.",
        false,
      );
    }
    setNarrationPending(false);
  }
  async function cancel(proposal: ActivityProposal) {
    const response = await session.run(
      "Cancelling the draft…",
      (s) => planningApi.reject(s, proposal.id),
      (s) => s,
    );
    if (response) addMessage({ role: "notice", text: "Draft cancelled." });
  }
  const currentWeather = state?.forecast_reference ?? session.weather;
  const existing = computed?.simulation.baseline.metrics;
  const outlook = existing
    ? existing.critical_requested_kwh <= 1e-6
      ? "Essential equipment needs review"
      : existing.critical_unserved_kwh > 1e-6
        ? "Essential equipment may lose power"
        : existing.min_soc_kwh <
            computed!.simulation.effective_config.reserve_kwh - 1e-6
          ? "Battery may run too low"
          : "The forecast plan covers essential equipment"
    : "Ask LifeLine about the clinic’s electricity";
  const locationName = state
    ? (locations
        .find(
          (l) =>
            l.latitude === state.location.latitude &&
            l.longitude === state.location.longitude,
        )
        ?.name.replace(/\s*\([^)]*\)/, "") ??
      `${state.location.latitude.toFixed(4)}, ${state.location.longitude.toFixed(4)}`)
    : "";
  const errorUI = session.error ? (
    <Alert variant="destructive" role="alert">
      <AlertTriangle />
      <AlertTitle>The update needs attention</AlertTitle>
      <AlertDescription>
        {session.error}
        <Button
          variant="outline"
          disabled={Boolean(busy)}
          onClick={() => void session.reload()}
        >
          Reload shared state
        </Button>
      </AlertDescription>
    </Alert>
  ) : null;
  const planFailure =
    state?.plan_status === "failed" ? (
      <Alert variant="destructive" role="alert">
        <AlertTriangle />
        <AlertTitle>No current energy plan</AlertTitle>
        <AlertDescription>
          Confirmed activities are saved. Ask LifeLine to retry the calculation.
          <Button
            variant="outline"
            disabled={Boolean(busy)}
            onClick={() =>
              requestPlan(
                "Retry the energy calculation for our confirmed activities and describe the result.",
              )
            }
          >
            Retry with LifeLine
          </Button>
        </AlertDescription>
      </Alert>
    ) : null;
  const context = state ? (
    <div className="chat-context">
      <div className="clinic-context-row">
        <div>
          <strong>{state.clinic_name}</strong>
          <span>
            <MapPin aria-hidden="true" />
            {locationName} · {state.planning_date}
          </span>
        </div>
      </div>
      {route.page === "assistant" ? (
        <div className="chat-weather" role="status">
          <CloudSun aria-hidden="true" />
          <div>
            <strong>
              {busy || narrationPending
                ? busy || "LifeLine is preparing your response…"
                : session.weatherLoading && !currentWeather
                  ? "Checking weather…"
                  : currentWeather
                    ? outlook
                    : "Weather is unavailable"}
            </strong>
          </div>
        </div>
      ) : null}
    </div>
  ) : null;
  const assistant = (
    <>
      <div
        className="chat-transcript"
        ref={transcript}
        aria-label="Conversation with LifeLine"
        onScroll={() => {
          const el = transcript.current;
          if (el)
            following.current =
              el.scrollHeight - el.scrollTop - el.clientHeight < 80;
        }}
      >
        {session.loading ? (
          <p className="chat-loading" role="status">
            Loading your clinic…
          </p>
        ) : null}
        {!session.loading && !state ? (
          <div className="chat-initial-error" role="alert">
            <p>{session.error}</p>
            <Button
              onClick={() => void session.initialize(session.missingSession)}
            >
              {session.missingSession
                ? "Start a new session"
                : "Retry connection"}
            </Button>
          </div>
        ) : null}
        {state && !messages.length ? (
          <div className="chat-welcome">
            <h1>How can LifeLine help today?</h1>
            <p>
              Talk about your clinic’s activities, equipment times, or
              electricity. LifeLine will check the details and explain your
              options.
            </p>
            <div className="chat-suggestions" aria-label="Suggested questions">
              <Button
                variant="outline"
                disabled={Boolean(busy)}
                onClick={() => requestPlan()}
              >
                Plan our electricity
              </Button>
              {[
                "We have a vaccination campaign tomorrow from 9 AM to 3 PM.",
                "How can we prevent an energy shortage?",
              ].map((q) => (
                <Button
                  key={q}
                  variant="outline"
                  disabled={Boolean(busy)}
                  onClick={() => void say(q)}
                >
                  {q}
                </Button>
              ))}
            </div>
          </div>
        ) : null}
        {state && session.notice ? (
          <Disclosure title="About this clinic setup" keepMounted={false}>
            <p>{session.notice}</p>
          </Disclosure>
        ) : null}
        {messages.map((message) => {
          const current = Boolean(
            computed &&
              message.id === latestPlanMessageId &&
              message.sessionId === state?.id &&
              message.plan?.input_revision === computed.input_revision &&
              message.plan?.generation === computed.generation,
          );
          return (
            <article
              key={message.id}
              className={`chat-message ${message.role === "user" ? "user-message" : message.role === "notice" ? "notice-message" : "assistant-message"}`}
            >
              {message.role !== "notice" ? (
                <strong className="message-author">
                  {message.role === "user" ? "You" : "LifeLine"}
                </strong>
              ) : null}
              {message.plan && !current ? <p className="chat-result-note">Earlier calculated response · not the active plan</p> : null}
              <p className="assistant-text">{message.text}</p>
              {message.retryQuestion ? (
                <Button
                  variant="outline"
                  disabled={Boolean(busy)}
                  onClick={() => void say(message.retryQuestion!, false)}
                >
                  Retry reply
                </Button>
              ) : null}
              {message.plan &&
              computed &&
              replyReady &&
              !busy &&
              !narrationPending ? (
                current ? (
                  <InlinePlan computed={message.plan} date={message.date!} selectionId={message.selectionId} />
                ) : (
                  <Disclosure
                    title={`Earlier plan · ${message.date}${message.plan.sunshine_factor < 1 ? ` · ${Math.round((1 - message.plan.sunshine_factor) * 100)}% less sunshine` : ""}`}
                    keepMounted={false}
                  >
                    <p className="chat-result-note">
                      Earlier calculation, not the active plan.
                    </p>
                    <InlinePlan
                      computed={message.plan}
                      date={message.date!}
                      selectionId={message.selectionId}
                      historical
                    />
                  </Disclosure>
                )
              ) : null}
              {message.tools?.length ? (
                <Disclosure title="What LifeLine checked" keepMounted={false}>
                  <ul>
                    {message.tools.map((tool, i) => (
                      <li key={`${tool}-${i}`}>{toolLabels[tool] ?? tool}</li>
                    ))}
                  </ul>
                </Disclosure>
              ) : null}
            </article>
          );
        })}
        {busy || narrationPending ? (
          <p className="live-activity" role="status">
            <LoaderCircle className="loading-spin" aria-hidden="true" />
            {busy || "LifeLine is preparing your response…"}
          </p>
        ) : null}
        {state ? errorUI : null}
        {planFailure}
        {activeProposal && state && !busy && !narrationPending ? (
          <ActivityConfirmation
            key={`${activeProposal.id}-${state.revision}`}
            proposal={activeProposal}
            state={state}
            busy={false}
            onConfirm={() => void confirm(activeProposal)}
            onCancel={() => void cancel(activeProposal)}
            onEdit={() =>
              focusChat(
                `Change ${activeProposal.details.name ?? "this activity"}: `,
              )
            }
          />
        ) : null}
        {state &&
        messages.length > 0 &&
        !computed &&
        !busy &&
        !narrationPending &&
        !activeProposal &&
        state.plan_status !== "failed" ? (
          <div className="chat-suggestions" aria-label="Chat options">
            <Button variant="outline" onClick={() => requestPlan()}>
              Plan our electricity
            </Button>
          </div>
        ) : null}
      </div>
      <div className="chat-composer-region">
        <form
          className="chat-composer"
          onSubmit={(event) => {
            event.preventDefault();
            void say(text);
          }}
        >
          <label htmlFor="chat-input" className="sr-only">
            Message LifeLine
          </label>
          <textarea
            id="chat-input"
            ref={input}
            value={text}
            onChange={(event) => setText(event.target.value)}
            placeholder="Message LifeLine…"
            maxLength={2000}
            disabled={!state || Boolean(busy) || narrationPending}
            onKeyDown={(event) => {
              if (
                event.key === "Enter" &&
                !event.shiftKey &&
                !event.nativeEvent.isComposing
              ) {
                event.preventDefault();
                void say(text);
              }
            }}
          />
          <Button
            type="submit"
            aria-label="Send message"
            disabled={
              !state || Boolean(busy) || narrationPending || !text.trim()
            }
          >
            {busy || narrationPending ? (
              <LoaderCircle className="loading-spin" />
            ) : (
              <ArrowUp />
            )}
          </Button>
        </form>
        <p className="chat-composer-note">
          Local AI · Don’t enter patient information.
        </p>
      </div>
    </>
  );
  const overview = state ? (
    <>
      {errorUI}
      {planFailure}
      <div className="overview-grid">
        <ActivitiesSection
          state={state}
          busy={Boolean(busy)}
          onChat={focusChat}
        onAddEquipment={() => setEquipmentOpen(true)}
        />
        <WeatherSection location={state.location} date={state.planning_date} computed={computed} selected={selected} />
        <section
          data-overview-section="energy"
          className="overview-section overview-square"
          aria-labelledby="energy-title"
          tabIndex={0}
        >
          <h2 id="energy-title">Battery &amp; Energy</h2>
          <div className="overview-square-body">
            {computed ? (
              <BatterySummary computed={computed} date={state.planning_date} selected={selected} />
            ) : (
              <p className="panel-lead">Ask LifeLine to check the battery.</p>
            )}
            <Disclosure title="Battery assumptions" keepMounted={false}>
              <p>
                Assumed stored energy at midnight:{" "}
                {state.clinic.initial_battery_kwh != null
                  ? `${num(state.clinic.initial_battery_kwh)} kWh`
                  : "not provided"}
                . This is a planning assumption, not a current measurement.
              </p>
            </Disclosure>
            <Button
              variant="outline"
              disabled={Boolean(busy)}
              onClick={() => requestPlan(computed ? "Explain the battery results for the exact selected plan compared with the existing baseline, in plain English. Do not recalculate." : "Calculate the clinic battery forecast and describe its limitations in plain English.")}
            >
              Ask about the battery
            </Button>
          </div>
        </section>
        <SolutionsSection
          computed={computed}
          busy={Boolean(busy)}
          selected={selected}
          onSelect={id => void session.run("Updating the selected comparison…", s => planningApi.selectRecovery(s, id), s => s)}
          onChat={requestPlan}
        />
      </div>
    </>
  ) : (
    <p role="status">
      {session.loading
        ? "Loading your clinic…"
        : "Connect to LifeLine from AI Assistant to view the clinic."}
    </p>
  );
  return (<>
    <Workspace
      page={route.page}
      section={route.section}
      context={context}
      assistant={assistant}
      overview={overview}
      modelStatus={
        <>
          <span
            className={agent?.available ? "status-dot ready" : "status-dot"}
          />
          <span>
            {modelError
              ? "Local AI connection unavailable"
              : agent?.available
                ? `Local model · ${agent.model}`
                : agent
                  ? "Local AI unavailable"
                  : "Connecting to local AI…"}
          </span>
          {modelError || (agent && !agent.available) ? (
            <Button
              variant="ghost"
              aria-label="Reconnect local model"
              onClick={() => void checkModel()}
            >
              <RefreshCw data-icon="inline-start" />
              Retry
            </Button>
          ) : null}
        </>
      }
    />
    {state ? <AddEquipment open={equipmentOpen} date={state.planning_date} onClose={() => setEquipmentOpen(false)} onSubmit={requestPlan} /> : null}
  </>);
}
