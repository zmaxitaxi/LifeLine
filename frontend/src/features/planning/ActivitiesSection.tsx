import type { PlanningState } from "../../../../contracts/planning";
import { Button } from "@/components/ui/button";
import { shortName, num, timeRanges } from "@/lib/clinic";
import { activityView } from "./activity-view";

export function ActivitiesSection({ state, busy, onChat, onAddEquipment }: {
  state: PlanningState; busy: boolean; onChat: (message?: string) => void; onAddEquipment: () => void;
}) {
  const drafts = state.proposals.filter(p => p.status === "draft");
  return <section data-overview-section="activities" className="overview-section overview-square" aria-labelledby="activities-title" tabIndex={0}>
    <h2 id="activities-title">Activities &amp; Equipment</h2>
    <div className="overview-square-body">
      <div className="panel-actions"><Button variant="outline" disabled={busy} onClick={onAddEquipment}>Add equipment</Button><Button variant="ghost" disabled={busy} onClick={() => onChat("Plan a clinic activity: ")}>Add activity</Button></div>
      {state.confirmed_activities.length ? <ul className="activity-quick-list">
        {state.confirmed_activities.map(activity => {
          const view = activityView(activity.id, activity.details, state);
          return <li key={activity.id} data-testid="confirmed-activity"><Button className="activity-chat-line" variant="ghost" disabled={busy} onClick={() => onChat(`Change ${view.name}: `)}><strong>{view.name}</strong><span>{view.operatingWindow}</span></Button></li>;
        })}
      </ul> : null}
      {drafts.length ? <Button className="draft-chat-link" variant="ghost" onClick={() => onChat()}>{drafts.length} {drafts.length === 1 ? "draft" : "drafts"} in chat · review</Button> : null}
      <h3>Equipment <span className="equipment-count">{state.equipment_inventory.length}</span></h3>
      <ul className="equipment-list">
        {state.equipment_inventory.map(e => <li key={e.id}><details className="equipment-item">
          <summary><span><strong>{shortName(e.name)}</strong><small>{e.category === "critical" ? "Essential" : "Can be rescheduled"}</small></span><span>{num((e.category === "critical" ? e.power_kw : e.max_power_kw) * 1000, 0)} W</span></summary>
          <div className="equipment-detail">
            <dl><div><dt>{e.category === "critical" ? "Required hours" : "Allowed hours"}</dt><dd>{timeRanges(e.category === "critical" ? e.required_hours : e.allowed_hours)}</dd></div>
              {e.category === "flexible" ? <><div><dt>Required energy</dt><dd>{num(e.required_energy_kwh)} kWh</dd></div><div><dt>Work can pause and resume</dt><dd>Yes</dd></div></> : null}
            </dl>
            <Button variant="outline" disabled={busy} onClick={() => onChat(`I want to change the requirements for ${e.name}. `)}>Edit in chat</Button>
          </div>
        </details></li>)}
      </ul>
    </div>
  </section>;
}
