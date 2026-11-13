import type {
  Activity,
  ActivityDraft,
  ActivityProposal,
  PlanningState,
} from "../../../../contracts/planning";
import { Button } from "@/components/ui/button";
import { Disclosure } from "@/components/Disclosure";
import { ActivityConfirmation } from "./ActivityConfirmation";
import { activityView } from "./activity-view";
import { num, shortName, timeRanges } from "@/lib/clinic";

export function ActivitiesSection({
  state,
  busy,
  editingId,
  error,
  onAdd,
  onEdit,
  onSave,
  onConfirm,
  onCancel,
}: {
  state: PlanningState;
  busy: boolean;
  editingId: string | null;
  error: string;
  onAdd: () => void;
  onEdit: (activity: Activity) => void;
  onSave: (proposal: ActivityProposal, details: ActivityDraft) => void;
  onConfirm: (proposal: ActivityProposal) => void;
  onCancel: (proposal: ActivityProposal) => void;
}) {
  return (
    <section
      data-overview-section="activities"
      className="overview-section"
      aria-labelledby="activities-title"
    >
      <div className="section-heading">
        <h2 id="activities-title">Activities &amp; Equipment</h2>
        <Button variant="outline" disabled={busy} onClick={onAdd}>
          Add activity manually
        </Button>
      </div>
      <h3>Confirmed daily activities</h3>
      {state.confirmed_activities.length ? (
        <ul className="confirmed-activities">
          {state.confirmed_activities.map((activity) => {
            const view = activityView(activity.id, activity.details, state);
            return (
              <li key={activity.id} data-testid="confirmed-activity">
                <div>
                  <h4>{view.name}</h4>
                  <p>
                    {view.date} · {view.operatingWindow}
                    {activity.details.duration_hours != null
                      ? ` · ${activity.details.duration_hours} hours required`
                      : ""}
                  </p>
                  <ul>
                    {view.equipment.map((e) => (
                      <li key={e.id}>
                        <strong>{e.name}: </strong>
                        {e.specifications.join(" · ")}
                      </li>
                    ))}
                  </ul>
                </div>
                <Button
                  variant="outline"
                  disabled={busy}
                  onClick={() => onEdit(activity)}
                >
                  Edit activity
                </Button>
              </li>
            );
          })}
        </ul>
      ) : (
        <p>
          No daily activities have been confirmed. The base clinic equipment
          requirements still apply.
        </p>
      )}
      <h3>Draft activities</h3>
      {state.proposals
        .filter((p) => p.status === "draft")
        .map((proposal) => (
          <ActivityConfirmation
            key={`${proposal.id}-${state.revision}`}
            proposal={proposal}
            state={state}
            busy={busy}
            error={error}
            editInitially={proposal.id === editingId}
            onSave={(details) => onSave(proposal, details)}
            onConfirm={() => onConfirm(proposal)}
            onCancel={() => onCancel(proposal)}
          />
        ))}
      {!state.proposals.some((p) => p.status === "draft") ? (
        <p>No drafts waiting for review.</p>
      ) : (
        <p className="proposal-note">
          Drafts are excluded from the active energy plan until confirmed.
        </p>
      )}
      <Disclosure
        title="Clinic equipment ratings and requirements"
        keepMounted={false}
      >
        <ul className="inventory-list">
          {state.equipment_inventory.map((e) => (
            <li key={e.id}>
              <strong>{shortName(e.name)}</strong>
              <p>
                {e.category === "critical"
                  ? `${num(e.power_kw * 1000, 0)} W · essential · ${timeRanges(e.required_hours)}`
                  : `Up to ${num(e.max_power_kw * 1000, 0)} W · ${num(e.required_energy_kwh)} kWh required · available ${timeRanges(e.allowed_hours)}`}
              </p>
            </li>
          ))}
        </ul>
        <p>
          Ratings come from the configured clinic inventory. Activities link
          existing devices once; extra operating hours must be explicitly
          reviewed. Whole-hour energy checks cannot validate medical cycles.
        </p>
      </Disclosure>
    </section>
  );
}
