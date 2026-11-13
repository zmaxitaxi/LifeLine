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
import type {
  Activity,
  ActivityDraft,
  ActivityProposal,
} from "../../contracts/planning";
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
import { BatteryEvidence } from "@/features/planning/BatteryEvidence";
import { PlanOutcome } from "@/features/planning/PlanOutcome";

interface Message {
  id: string;
  role: "user" | "assistant" | "notice";
  text: string;
  tools?: string[];
  inputRevision?: number;
}
const toolLabels: Record<string, string> = {
  inspect_planning_state: "Inspect clinic planning state",
  review_activity_proposal: "Review the activity draft",
  propose_activity: "Propose a clinic activity",
  update_activity_draft: "Update the activity draft",
  propose_activity_revision: "Prepare a reviewed activity change",
  correct_last_activity_time: "Correct the draft’s operating time",
  recompute_clinic_plan: "Calculate the clinic energy plan",
};
export default function App() {
  const session = usePlanningSession();
  const { state, computed, busy } = session;
  const route = useWorkspaceNavigation();
  const [messages, setMessages] = useState<Message[]>([]);
  const [text, setText] = useState("");
  const [agent, setAgent] = useState<AgentStatus | null>(null);
  const [modelError, setModelError] = useState(false);
  const [locations, setLocations] = useState<
    { name: string; latitude: number; longitude: number }[]
  >([]);
  const [editingId, setEditingId] = useState<string | null>(null);
  const transcript = useRef<HTMLDivElement>(null);
  const input = useRef<HTMLTextAreaElement>(null);
  const following = useRef(true);
  const confirmationKeys = useRef(new Map<string, string>());
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
  const activeProposal = state?.proposals.find(
    (p) => p.id === state.active_proposal_id && p.status === "draft",
  );
  const recovery = computed?.recovery;
  const selected = recovery?.options.find(
    (o) =>
      o.id ===
      (state?.selected_recovery_intervention_id ??
        recovery.recommended_option_id),
  );
  async function say(question: string) {
    if (!question.trim() || busy || !state) return;
    following.current = true;
    setText("");
    setMessages((items) => [
      ...items,
      { id: crypto.randomUUID(), role: "user", text: question },
    ]);
    const response = await session.run(
      "Sending your message to the local assistant…",
      (s) => planningApi.ask(s, question),
      (r) => r.state,
      true,
    );
    if (response) {
      setMessages((items) => [
        ...items,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          text: response.message,
          tools: response.tool_calls,
          inputRevision: response.state.input_revision,
        },
      ]);
      setEditingId(null);
      requestAnimationFrame(() => input.current?.focus());
    }
  }
  async function save(proposal: ActivityProposal, details: ActivityDraft) {
    const response = await session.run(
      "Saving the draft for review…",
      (s) => planningApi.edit(s, proposal.id, details),
      (s) => s,
    );
    if (response) {
      setEditingId(null);
      setMessages((items) => [
        ...items,
        {
          id: crypto.randomUUID(),
          role: "notice",
          text: "Draft saved for review. It has not changed the active energy plan.",
        },
      ]);
    }
  }
  async function confirm(proposal: ActivityProposal) {
    let idempotencyKey = confirmationKeys.current.get(proposal.id);
    if (!idempotencyKey) {
      idempotencyKey = crypto.randomUUID();
      confirmationKeys.current.set(proposal.id, idempotencyKey);
    }
    const response = await session.run(
      "Confirming the activity and calculating the updated plan…",
      (s) => planningApi.confirm(s, proposal.id, idempotencyKey!),
      (s) => s,
      true,
    );
    if (response) {
      setEditingId(null);
      setMessages((items) => [
        ...items,
        {
          id: crypto.randomUUID(),
          role: "notice",
          text:
            response.plan_status === "failed"
              ? "The activity is confirmed. The updated energy calculation failed; no earlier plan is shown as current."
              : "Activity confirmed. Both pages now use the updated clinic requirements.",
        },
      ]);
    }
  }
  async function cancel(proposal: ActivityProposal) {
    const response = await session.run(
      "Cancelling the activity draft…",
      (s) => planningApi.reject(s, proposal.id),
      (s) => s,
    );
    if (response) {
      setEditingId(null);
      setMessages((items) => [
        ...items,
        {
          id: crypto.randomUUID(),
          role: "notice",
          text: "Draft cancelled. Confirmed activities and their electrical requirements are unchanged.",
        },
      ]);
    }
  }
  async function recompute(factor?: number) {
    await session.run(
      "Calculating the plan from confirmed requirements and the weather forecast…",
      (s) => planningApi.recompute(s, factor ?? s.sunshine_factor),
      (s) => s,
      true,
    );
  }
  function calculateFromChat() {
    if (!state || busy) return;
    following.current = true;
    setMessages((items) => [
      ...items,
      {
        id: crypto.randomUUID(),
        role: "user",
        text: "Calculate the energy plan.",
      },
      ...(state.proposals.some((proposal) => proposal.status === "draft")
        ? [
            {
              id: crypto.randomUUID(),
              role: "notice" as const,
              text: "This calculation uses confirmed activities only. Draft activities are excluded until you confirm them.",
            },
          ]
        : []),
    ]);
    void recompute();
  }
  async function add() {
    const response = await session.run(
      "Creating an activity draft…",
      (s) => planningApi.propose(s, { planning_date: s.planning_date }),
      (s) => s,
    );
    if (response) setEditingId(response.active_proposal_id);
  }
  async function edit(activity: Activity) {
    const response = await session.run(
      "Preparing a draft of the activity changes…",
      (s) => planningApi.propose(s, activity.details, activity.id),
      (s) => s,
    );
    if (response) setEditingId(response.active_proposal_id);
  }
  const currentWeather = state?.forecast_reference ?? session.weather;
  const essential = computed?.simulation.baseline.metrics;
  const outlook = essential
    ? essential.critical_requested_kwh <= 1e-6
      ? "Essential equipment needs review"
      : essential.critical_unserved_kwh > 1e-6
        ? "Energy shortage in the current schedule"
        : essential.min_soc_kwh <
            computed!.simulation.effective_config.reserve_kwh - 1e-6
          ? "Current schedule may use the battery reserve"
          : "Current schedule supplies essential equipment in the model"
    : "Ask LifeLine to check the energy outlook";
  const errorUI = session.error ? (
    <Alert variant="destructive" role="alert" className="shared-error">
      <AlertTriangle />
      <AlertTitle>Planning update needs attention</AlertTitle>
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
          {state.plan_error ?? "The calculation failed."} Confirmed activities
          are saved. No old battery or solution is shown.
          <Button
            variant="outline"
            disabled={Boolean(busy)}
            onClick={() => void recompute()}
          >
            Retry energy calculation
          </Button>
        </AlertDescription>
      </Alert>
    ) : null;
  const locationName = state
    ? (locations
        .find(
          (location) =>
            location.latitude === state.location.latitude &&
            location.longitude === state.location.longitude,
        )
        ?.name.replace(/\s*\([^)]*\)/, "") ??
      `${state.location.latitude.toFixed(4)}, ${state.location.longitude.toFixed(4)}`)
    : "";
  const context = state ? (
    <div className="chat-context">
      <div className="clinic-context-row">
        <div>
          <strong>{state.clinic_name}</strong>
          <span>
            <MapPin aria-hidden="true" />
            {locationName} · {state.planning_date}
            {state.timezone
              ? ` · ${state.timezone}`
              : " · timezone awaiting forecast"}
          </span>
        </div>
      </div>
      <div className="chat-weather" role="status">
        <CloudSun aria-hidden="true" />
        <div>
          <strong>
            {session.weatherLoading && !currentWeather
              ? "Checking live weather…"
              : currentWeather
                ? currentWeather.cache_status === "stale"
                  ? `Older forecast · ${outlook}`
                  : outlook
                : "Live weather is unavailable"}
          </strong>
        </div>
      </div>
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
            <LoaderCircle className="loading-spin" />
            Loading the shared clinic plan…
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
            <h1>Plan your clinic’s day.</h1>
            <p>
              Describe an activity. Review its equipment needs before it changes
              the energy plan.
            </p>
            <div className="chat-suggestions" aria-label="Suggested questions">
              <Button
                variant="outline"
                disabled={Boolean(busy)}
                onClick={calculateFromChat}
              >
                Calculate plan
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
          <p className="chat-notice" role="status">
            {session.notice}
          </p>
        ) : null}
        {messages.map((message) => (
          <article
            key={message.id}
            className={`chat-message ${message.role === "user" ? "user-message" : message.role === "notice" ? "notice-message" : "assistant-message"}`}
          >
            {message.role !== "notice" ? (
              <strong className="message-author">
                {message.role === "user" ? "You" : "LifeLine"}
              </strong>
            ) : null}
            <p className="assistant-text">{message.text}</p>
            {message.inputRevision !== undefined &&
            state &&
            message.inputRevision !== state.input_revision ? (
              <p className="chat-result-note">
                Earlier response · clinic requirements have since changed.
              </p>
            ) : null}
            {message.tools?.length ? (
              <Disclosure title="Reported tool activity" keepMounted={false}>
                <ul>
                  {message.tools.map((tool, i) => (
                    <li key={`${tool}-${i}`}>
                      Requested: {toolLabels[tool] ?? tool}
                    </li>
                  ))}
                </ul>
                <p>
                  These are tool requests reported by the backend. Reviewed
                  drafts and verified calculation results are shown separately;
                  a request alone does not confirm a change.
                </p>
              </Disclosure>
            ) : null}
          </article>
        ))}
        {busy ? (
          <p className="live-activity" role="status">
            <LoaderCircle className="loading-spin" aria-hidden="true" />
            {busy}
          </p>
        ) : null}
        {state ? errorUI : null}
        {planFailure}
        {activeProposal && state ? (
          <ActivityConfirmation
            key={`assistant-${activeProposal.id}-${state.revision}`}
            proposal={activeProposal}
            state={state}
            busy={Boolean(busy)}
            editInitially={activeProposal.id === editingId}
            onSave={(details) => void save(activeProposal, details)}
            onConfirm={() => void confirm(activeProposal)}
            onCancel={() => void cancel(activeProposal)}
          />
        ) : null}
        {computed ? (
          <PlanOutcome
            computed={computed}
            onExplore={() => route.explore("solutions")}
          />
        ) : null}
        {state &&
        messages.length > 0 &&
        !computed &&
        !busy &&
        state.plan_status !== "failed" ? (
          <div className="chat-suggestions" aria-label="Chat options">
            <Button variant="outline" onClick={calculateFromChat}>
              Calculate plan
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
            onChange={(e) => setText(e.target.value)}
            placeholder="Describe a clinic activity or ask about electricity…"
            maxLength={2000}
            disabled={!state || Boolean(busy)}
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
            disabled={!state || Boolean(busy) || !text.trim()}
          >
            {busy ? <LoaderCircle className="loading-spin" /> : <ArrowUp />}
          </Button>
        </form>
        <p className="chat-composer-note">
          Runs locally. Live weather needs internet. Don’t enter patient
          information.
        </p>
      </div>
    </>
  );
  const overview = state ? (
    <>
      {errorUI}
      {planFailure}
      {busy ? <p role="status">{busy}</p> : null}
      <ActivitiesSection
        state={state}
        busy={Boolean(busy)}
        editingId={editingId}
        error=""
        onAdd={() => void add()}
        onEdit={(activity) => void edit(activity)}
        onSave={(proposal, details) => void save(proposal, details)}
        onConfirm={(proposal) => void confirm(proposal)}
        onCancel={(proposal) => void cancel(proposal)}
      />
      <WeatherSection
        forecast={currentWeather}
        simulation={computed?.simulation ?? null}
        date={state.planning_date}
        loading={session.weatherLoading}
        error={session.weatherError}
        onRetry={() => void session.refreshWeather()}
      />
      <section
        data-overview-section="energy"
        className="overview-section"
        aria-labelledby="energy-title"
      >
        <h2 id="energy-title">Battery &amp; Energy</h2>
        {computed ? (
          <BatteryEvidence
            key={`${state.id}-${computed.input_revision}-${computed.generation}`}
            result={computed.simulation}
            date={state.planning_date}
            intervention={selected}
            showIndicators={false}
          />
        ) : (
          <p>
            No current verified battery forecast. Confirmed activities remain
            saved; calculate the plan to inspect the battery.
          </p>
        )}
        <Disclosure
          title="Starting energy and battery assumptions"
          keepMounted={false}
        >
          <p>
            Starting stored energy:{" "}
            {state.clinic.initial_battery_kwh != null
              ? num(state.clinic.initial_battery_kwh)
              : "Not provided"}{" "}
            kWh at 00:00 {state.planning_date}. This comes from the configured
            clinic assumption, not a current battery measurement. The session is
            based on {state.selected_clinic_id} inputs.
          </p>
        </Disclosure>
        <Button
          variant="outline"
          disabled={Boolean(busy)}
          onClick={() => void recompute()}
        >
          Calculate plan
        </Button>
      </section>
      <SolutionsSection
        computed={computed}
        selectedId={state.selected_recovery_intervention_id}
        busy={Boolean(busy)}
        onSelect={(id) =>
          void session.run(
            "Saving the selected recovery comparison…",
            (s) => planningApi.selectRecovery(s, id),
            (s) => s,
          )
        }
        onRecompute={() => void recompute()}
      />
      <a className="return-to-chat" href="#assistant">
        Return to AI Assistant
      </a>
    </>
  ) : (
    <p role="status">
      {session.loading
        ? "Loading the shared clinic state…"
        : "Connect to the planning service from AI Assistant to view clinic details."}
    </p>
  );
  return (
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
              ? "Local model connection unavailable"
              : agent?.available
                ? `Local model · ${agent.model}`
                : agent
                  ? "Local model unavailable · manual planning ready"
                  : "Checking the local model…"}
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
  );
}
