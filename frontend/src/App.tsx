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
import type { ActivityDraft, ActivityProposal, ComputedPlan, EnergySettingsProposal } from "../../contracts/planning";
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
import { ActivityWorkspace, type ActivitySelection } from "@/features/planning/ActivityWorkspace";
import { EnergySettingsWorkspace, type EnergySelection } from "@/features/planning/EnergySettingsWorkspace";
import type { EnergyFormValue } from "@/features/planning/EnergySettingsEditor";
import { InlinePlan } from "@/features/planning/InlinePlan";

import { restoreMessages, resultAttachment, type ChatMessage } from "@/features/planning/conversation-view";
import { EnergySettingsReview } from "@/features/planning/EnergySettingsReview";
const toolLabels: Record<string, string> = {
  conversational_reply: "Answered your message",
  explain_current_plan: "Reviewed the selected plan",
  inspect_planning_state: "Reviewed the clinic details",
  review_activity_proposal: "Prepared the activity for review",
  propose_energy_settings: "Prepared power settings for review",
  update_energy_settings_draft: "Updated the power settings draft",
  propose_activity: "Prepared an activity draft",
  update_activity_draft: "Updated the activity draft",
  propose_activity_revision: "Prepared an activity change",
  correct_last_activity_time: "Corrected the operating time",
  recompute_clinic_plan: "Calculated the plan and checked the weather",
};
const planQuestion =
  "Will we have enough electricity for our planned clinic activities? Help us decide what needs to change.";
export default function App() {
  const session = usePlanningSession();
  const { state, busy } = session;
  const route = useWorkspaceNavigation();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [historyLoading,setHistoryLoading]=useState(false);
  const [historyError,setHistoryError]=useState("");
  const [text, setText] = useState("");
  const [energySelection,setEnergySelection]=useState<EnergySelection | null>(null);
  const [activitySelection, setActivitySelection] = useState<ActivitySelection | null>(null);
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
  function addMessage(message:Omit<ChatMessage,"id"|"createdAt">,id:string=crypto.randomUUID()) {
    setMessages(items=>[...items,{id,createdAt:new Date().toISOString(),...message}]);return id;
  }
  async function loadHistory(snapshot=session.stateRef.current,signal?:AbortSignal) {
    if(!snapshot)return;setHistoryLoading(true);setHistoryError("");
    try {
      const history=await planningApi.conversation(snapshot.id,signal);
      if(signal?.aborted || session.stateRef.current?.id !== snapshot.id)return;
      const current=session.stateRef.current;
      setMessages(items=>{
        const cached=new Map(items.map(item=>[item.id,item]));
        const restored=restoreMessages(history.messages,current).map(item=>({...cached.get(item.id),...item}));
        const localNotices=items.filter(item=>item.role === "notice" && !item.presentation && !history.messages.some(remote=>remote.id===item.id));
        return [...restored,...localNotices].sort((a,b)=>a.createdAt.localeCompare(b.createdAt));
      });
    } catch {if(!signal?.aborted)setHistoryError("The conversation could not be loaded. Your clinic information is still available.");}
    finally {if(!signal?.aborted)setHistoryLoading(false);}
  }
  useEffect(()=>{const abort=new AbortController();if(state?.id)void loadHistory(state,abort.signal);return ()=>abort.abort();},[state?.id]);
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
    if (!question.trim() || busy || historyLoading || !session.stateRef.current) return;
    following.current = true;
    setText("");
    setReplyReady(false);
    const optimisticUserId = showUser ? addMessage({ role: "user", text: question }) : undefined;
    const response = await session.run(
      "LifeLine is preparing your response…",
      (s) => planningApi.ask(s, question),
      (r) => r.state,
    );
    if(response?.user_message_id && optimisticUserId)setMessages(items=>items.map(item=>item.id === optimisticUserId ? {...item,id:response.user_message_id!} : item));
    if (response?.mode === "local_tool_agent") {
      addMessage({role:"assistant",text:response.message,tools:response.tool_calls,presentation:response.presentation,...resultAttachment(response.presentation,response.state)},response.message_id ?? undefined);
      setReplyReady(true);
    } else if (response) {
      addMessage({
        role: "notice",
        text: "The local assistant couldn’t finish this reply. Please retry.",
        retryQuestion: question,
        presentation: response.presentation,
      },response.message_id ?? undefined);
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
      if (response.plan_status === "current" && response.computed_plan) {
        addMessage({role:"notice",text:"Updated electricity plan",plan:response.computed_plan,date:response.planning_date,sessionId:response.id});
        setReplyReady(true);
      }
    }
    setNarrationPending(false);
    return Boolean(response);
  }
  async function cancel(proposal: ActivityProposal) {
    const response = await session.run(
      "Cancelling the draft…",
      (s) => planningApi.reject(s, proposal.id),
      (s) => s,
    );
    if (response) addMessage({ role: "notice", text: "Draft cancelled." });
    return Boolean(response);
  }
  async function saveActivity(details:ActivityDraft, revision:number, proposalId?:string, targetId?:string) {
    const response = await session.run("Saving the activity draft…", s => proposalId ? planningApi.edit({...s,revision},proposalId,details) : planningApi.propose({...s,revision},details,targetId), s=>s);
    return response?.active_proposal_id ?? null;
  }
  async function saveEnergy(value:EnergyFormValue,revision:number,proposalId?:string) {
    const response = await session.run("Saving the power settings draft…",s=>proposalId ? planningApi.editEnergy({...s,revision},proposalId,value.settings,value.reading) : planningApi.proposeEnergy({...s,revision},value.settings,value.reading),s=>s);
    return response?.active_energy_proposal_id ?? null;
  }
  async function confirmEnergy(proposal:EnergySettingsProposal) {
    const receipt=`energy-${proposal.id}`;let key=confirmationKeys.current.get(receipt);if(!key){key=crypto.randomUUID();confirmationKeys.current.set(receipt,key);}
    const response=await session.run("Updating power settings and calculating the plan…",s=>planningApi.confirmEnergy(s,proposal.id,key!),s=>s,true);
    if(response){addMessage({role:"notice",text:response.plan_status === "failed" ? "Power settings saved. The energy calculation needs to be retried." : "Power settings saved. The electricity plan is updated.",...(response.plan_status === "current" && response.computed_plan ? {plan:response.computed_plan,date:response.planning_date,sessionId:response.id} : {})});setReplyReady(true);}
    return Boolean(response);
  }
  async function rejectEnergy(proposal:EnergySettingsProposal) {
    const response=await session.run("Cancelling the power settings draft…",s=>planningApi.rejectEnergy(s,proposal.id),s=>s);
    if(response)addMessage({role:"notice",text:"Power settings draft cancelled."});return Boolean(response);
  }
  function openEnergy() {setEnergySelection(state?.active_energy_proposal_id ? {kind:"proposal",id:state.active_energy_proposal_id} : {kind:"new"});}
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
        {historyLoading ? <p role="status" className="chat-loading">Loading your conversation…</p> : null}
        {historyError ? <div className="chat-initial-error" role="alert"><p>{historyError}</p><Button variant="outline" onClick={()=>void loadHistory()}>Retry conversation</Button></div> : null}
        {state && !messages.length && !historyLoading ? (
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
              {(message.plan && !current) || (message.presentation?.generation != null && (message.presentation.generation !== computed?.generation || message.presentation.input_revision !== computed?.input_revision)) ? <p className="chat-result-note">Earlier calculated response · not the active plan</p> : null}
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
                  <InlinePlan computed={message.plan} date={message.date!} selectionId={message.selectionId} optionIds={message.optionIds} showSchedule={message.showSchedule ?? true}/>
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
                      optionIds={message.optionIds}
                      showSchedule={message.showSchedule ?? true}
                      historical
                    />
                  </Disclosure>
                )
              ) : null}
              {message.tools?.some(tool => !["conversational_reply","respond_to_user","compose_planning_reply"].includes(tool)) ? (
                <Disclosure title="What LifeLine checked" keepMounted={false}>
                  <ul>
                    {message.tools.filter(tool => !["conversational_reply","respond_to_user","compose_planning_reply"].includes(tool)).map((tool, i) => (
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
        {activeProposal && state && messages.at(-1)?.presentation?.kind === "activity_review" && !busy && !narrationPending ? (
          <ActivityConfirmation
            key={`${activeProposal.id}-${state.revision}`}
            proposal={activeProposal}
            state={state}
            busy={false}
            onConfirm={() => void confirm(activeProposal)}
            onCancel={() => void cancel(activeProposal)}
            onEdit={() => setActivitySelection({kind:"proposal",id:activeProposal.id})}
          />
        ) : null}
        {state && messages.at(-1)?.presentation?.kind === "energy_review" && !busy ? (()=>{const proposal=state.energy_proposals.find(p=>p.id===state.active_energy_proposal_id && p.status === "draft");return proposal ? <EnergySettingsReview current={state.energy_settings} proposed={proposal.proposed_energy_settings} changes={proposal.settings} date={state.planning_date} timezone={state.timezone} reading={proposal.current_battery_reading} updatesReading={proposal.updates_current_battery_reading} busy={Boolean(busy)} confirmDisabled={proposal.base_input_revision !== state.input_revision} onConfirm={()=>void confirmEnergy(proposal)} onCancel={()=>void rejectEnergy(proposal)} onEdit={()=>setEnergySelection({kind:"proposal",id:proposal.id})}/> : null;})() : null}
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
        {state && !busy && !historyLoading && activeProposal && messages.at(-1)?.presentation?.kind !== "activity_review" ? <Button className="draft-shortcut" variant="ghost" onClick={()=>setActivitySelection({kind:"proposal",id:activeProposal.id})}>Review activity draft · {activeProposal.details.name ?? "New activity"}</Button> : null}
        {state && !busy && !historyLoading && state.active_energy_proposal_id && messages.at(-1)?.presentation?.kind !== "energy_review" ? <Button className="draft-shortcut" variant="ghost" onClick={openEnergy}>Review power settings draft</Button> : null}
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
            disabled={!state || Boolean(busy) || narrationPending || historyLoading}
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
              !state || Boolean(busy) || narrationPending || historyLoading || !text.trim()
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
          onActivity={setActivitySelection}
        onAddEquipment={() => setEquipmentOpen(true)}
        />
        <WeatherSection location={state.location} date={state.planning_date} computed={computed} selected={selected} />
        <section
          data-overview-section="energy"
          className="overview-section overview-square"
          aria-labelledby="energy-title"
          tabIndex={0}
        >
          <div className="panel-heading"><h2 id="energy-title">Battery &amp; Energy</h2><Button variant="outline" disabled={Boolean(busy)} onClick={openEnergy}>Power setup</Button></div>
          <div className="overview-square-body">
            {computed && busy ? <p className="panel-footnote" role="status">LifeLine is working. Showing the last verified calculation.</p> : null}
            {computed ? (
              <BatterySummary computed={computed} date={state.planning_date} selected={selected} />
            ) : (
              <p className="panel-lead">Set the power assumptions, then ask LifeLine to check the day’s electricity.</p>
            )}
            <Disclosure title="Battery assumptions" keepMounted={false}>
              <p>{state.current_battery_reading ? `Recorded reading: ${num(state.current_battery_reading.energy_kwh)} kWh at ${new Intl.DateTimeFormat("en",{dateStyle:"medium",timeStyle:"short",timeZone:state.timezone ?? undefined}).format(new Date(state.current_battery_reading.measured_at))}.` : "No current battery reading is recorded."}</p>
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
    {state && energySelection ? <EnergySettingsWorkspace selection={energySelection} state={state} busy={Boolean(busy)} error={session.error} onSave={saveEnergy} onConfirm={confirmEnergy} onReject={rejectEnergy} onClose={()=>setEnergySelection(null)}/> : null}
    {state && activitySelection ? <ActivityWorkspace selection={activitySelection} state={state} busy={Boolean(busy) || narrationPending} error={session.error} onSave={saveActivity} onConfirm={confirm} onReject={cancel} onClose={()=>setActivitySelection(null)} /> : null}
    {state ? <AddEquipment open={equipmentOpen} date={state.planning_date} busy={Boolean(busy)} error={session.error} onClose={() => setEquipmentOpen(false)} onDraft={async details=>{const id=await saveActivity(details,state.revision);if(id){setEquipmentOpen(false);setActivitySelection({kind:"proposal",id});return true;}return false;}} /> : null}
  </>);
}
