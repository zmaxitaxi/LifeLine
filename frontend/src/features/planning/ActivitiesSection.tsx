import type { PlanningState } from "../../../../contracts/planning";
import { Button } from "@/components/ui/button";
import { shortName, num, timeRanges } from "@/lib/clinic";
import type { ActivitySelection } from "./ActivityWorkspace";
import { currentPlan } from "./planning-api";
import { activityView } from "./activity-view";

export function ActivitiesSection({ state, busy, onChat, onAddEquipment, onActivity }: {
  state: PlanningState; busy: boolean; onChat: (message?: string) => void; onAddEquipment: () => void; onActivity:(selection:ActivitySelection)=>void;
}) {
  const calculated=currentPlan(state,false);
  const inventory=calculated?.simulation.equipment ?? state.equipment_inventory;
  const drafts = state.proposals.filter(p => p.status === "draft");
  return <section data-overview-section="activities" className="overview-section overview-square" aria-labelledby="activities-title" tabIndex={0}>
    <h2 id="activities-title">Activities &amp; Equipment</h2>
    <div className="overview-square-body">
      <div className="panel-actions"><Button variant="outline" disabled={busy} onClick={onAddEquipment}>Add equipment</Button><Button variant="ghost" disabled={busy} onClick={() => onActivity({kind:"new"})}>Add activity</Button></div>
      {state.confirmed_activities.length ? <ul className="activity-quick-list">
        {state.confirmed_activities.map(activity => {
          const view = activityView(activity.id, activity.details, state);
          return <li key={activity.id} data-testid="confirmed-activity"><Button className="activity-chat-line" variant="ghost" disabled={busy} onClick={() => onActivity({kind:"activity",id:activity.id})}><strong>{view.name}</strong><span>{view.operatingWindow}</span></Button></li>;
        })}
      </ul> : null}
      {drafts.length ? <ul className="activity-drafts" aria-label="Activity drafts">{drafts.map(draft=><li key={draft.id}><Button variant="ghost" disabled={busy} onClick={()=>onActivity({kind:"proposal",id:draft.id})}>{draft.details.name ?? "New activity"} · draft · review</Button></li>)}</ul> : null}
      <h3>Equipment <span className="equipment-count">{inventory.length}</span></h3>
      <ul className="equipment-list">
        {inventory.map(e => <li key={e.id}><details className="equipment-item">
          <summary><span><strong>{shortName(e.name)}</strong><small>{e.category === "critical" ? "Essential" : "Can be rescheduled"}</small></span><span>{num((e.category === "critical" ? e.power_kw : e.max_power_kw) * 1000, 0)} W</span></summary>
          <div className="equipment-detail">
            <dl><div><dt>{e.category === "critical" ? calculated ? "Required hours" : "Base required hours" : calculated ? "Allowed hours" : "Base allowed hours"}</dt><dd>{timeRanges(e.category === "critical" ? e.required_hours : e.allowed_hours)}</dd></div>
              {e.category === "flexible" ? <><div><dt>{calculated ? "Daily work requirement" : "Base work requirement"}</dt><dd>{num(e.required_energy_kwh)} kWh</dd></div><div><dt>Work can pause and resume</dt><dd>Yes</dd></div></> : null}
            </dl>
            {state.confirmed_activities.flatMap(activity=>(activity.details.equipment_constraints ?? []).filter(c=>c.equipment_id===e.id).map((c,index)=><p className="panel-footnote" key={`${activity.id}-${index}`}>{activity.details.name}: {c.required_duration_hours != null ? `at least ${c.required_duration_hours} total daily operating hours. ` : ""}{c.required_hours ? `Additional required hours: ${timeRanges(c.required_hours)}. ` : ""}{c.allowed_hours ? `Allowed during ${timeRanges(c.allowed_hours)}.` : ""}</p>))}
            {!calculated ? <p className="panel-footnote">The base requirements above also have these confirmed activity requirements. A current energy calculation is not available.</p> : null}
            <Button variant="outline" disabled={busy} onClick={() => onChat(`I want to change the requirements for ${e.name}. `)}>Edit in chat</Button>
          </div>
        </details></li>)}
      </ul>
    </div>
  </section>;
}
