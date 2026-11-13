import { useId, useState } from "react";
import { AlertTriangle, CalendarDays, Clock3 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import type {
  ActivityDraft,
  ActivityProposal,
  PlanningState,
} from "../../../../contracts/planning";
import { activityView } from "./activity-view";
import { ActivityEditor, readActivityForm } from "./ActivityEditor";

export function ActivityConfirmation({
  proposal,
  state,
  busy,
  error,
  onSave,
  onConfirm,
  onCancel,
  editInitially = false,
}: {
  proposal: ActivityProposal;
  state: PlanningState;
  busy: boolean;
  error?: string;
  onSave: (details: ActivityDraft) => void;
  onConfirm: () => void;
  onCancel: () => void;
  editInitially?: boolean;
}) {
  const uid = useId();
  const activity = activityView(proposal.id, proposal.details, state, proposal);
  const [editing, setEditing] = useState(
    editInitially || proposal.missing_fields.length > 0,
  );
  return (
    <article
      className="activity-confirmation"
      aria-labelledby={`${uid}-title`}
      data-testid="activity-proposal"
    >
      <div className="proposal-heading">
        <h3 id={`${uid}-title`}>{activity.name}</h3>
        <Badge variant="secondary">Needs your confirmation</Badge>
      </div>
      <dl className="proposal-facts">
        <div>
          <dt>
            <CalendarDays aria-hidden="true" />
            Date
          </dt>
          <dd>{activity.date}</dd>
        </div>
        <div>
          <dt>
            <Clock3 aria-hidden="true" />
            Operating window
          </dt>
          <dd>{activity.operatingWindow}</dd>
        </div>
      </dl>
      {proposal.details.duration_hours != null ? (
        <p>
          Required activity duration: {proposal.details.duration_hours} hours.
          Electrical requirements are listed separately.
        </p>
      ) : null}
      <h4>Equipment needed</h4>
      {activity.equipment.length ? (
        <ul className="proposal-equipment">
          {activity.equipment.map((e) => (
            <li key={e.id}>
              <strong>{e.name}</strong>
              <span>{e.specifications.join(" · ")}</span>
            </li>
          ))}
        </ul>
      ) : (
        <p>
          {proposal.details.equipment_ids == null
            ? "Equipment still needs review."
            : "No existing equipment is linked."}
        </p>
      )}
      {activity.missing.length ? (
        <Alert>
          <AlertTriangle />
          <AlertTitle>Information still needed</AlertTitle>
          <AlertDescription>
            <ul>
              {activity.missing.map((m) => (
                <li key={m}>{m}</li>
              ))}
            </ul>
          </AlertDescription>
        </Alert>
      ) : null}
      {activity.affectedRequirements.length ? (
        <div className="affected-requirements">
          <h4>Existing requirements affected</h4>
          <ul>
            {activity.affectedRequirements.map((a) => (
              <li key={a}>{a}</li>
            ))}
          </ul>
        </div>
      ) : (
        <p className="proposal-note">
          No changes to existing electrical requirements are listed. Referencing
          equipment alone adds no demand.
        </p>
      )}
      {editing ? (
        <form
          onSubmit={(event) => {
            event.preventDefault();
            onSave(
              readActivityForm(
                event.currentTarget,
                proposal.details,
                state.equipment_inventory,
              ),
            );
          }}
        >
          <fieldset disabled={busy}>
            <ActivityEditor
              details={proposal.details}
              inventory={state.equipment_inventory}
              planningDate={state.planning_date}
            />
          </fieldset>
          <Button type="submit" variant="outline" disabled={busy}>
            Save draft for review
          </Button>
        </form>
      ) : null}
      {error ? (
        <Alert variant="destructive" role="alert">
          <AlertTriangle />
          <AlertTitle>Check this proposal</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      ) : null}
      <p className="proposal-note">
        This draft does not affect the active plan. Confirm only after reviewing
        its equipment requirements.
      </p>
      <div className="proposal-actions">
        <Button
          type="button"
          disabled={busy || editing || proposal.missing_fields.length > 0}
          onClick={onConfirm}
        >
          {busy ? "Working…" : "Confirm"}
        </Button>
        {!editing ? (
          <Button
            type="button"
            variant="outline"
            disabled={busy}
            onClick={() => setEditing(true)}
          >
            Edit
          </Button>
        ) : null}
        <Button
          type="button"
          variant="ghost"
          disabled={busy}
          onClick={onCancel}
        >
          Cancel
        </Button>
      </div>
    </article>
  );
}
