import { useId } from "react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import type {
  ActivityProposal,
  PlanningState,
} from "../../../../contracts/planning";
import { activityView } from "./activity-view";

export function ActivityConfirmation({
  proposal,
  state,
  busy,
  onConfirm,
  onCancel,
  onEdit,
}: {
  proposal: ActivityProposal;
  state: PlanningState;
  busy: boolean;
  onConfirm: () => void;
  onCancel: () => void;
  onEdit: () => void;
}) {
  const uid = useId();
  const activity = activityView(proposal.id, proposal.details, state, proposal);
  return (
    <article
      className="activity-confirmation"
      aria-labelledby={`${uid}-title`}
      data-testid="activity-proposal"
    >
      <div className="proposal-heading">
        <h3 id={`${uid}-title`}>{activity.name}</h3>
        <Badge variant="secondary">Draft · review first</Badge>
      </div>
      <p>
        {activity.date} · {activity.operatingWindow}
      </p>
      <ul className="proposal-equipment">
        {activity.equipment.map((e) => (
          <li key={e.id}>
            <strong>{e.name}</strong>
            <span>{e.specifications.join(" · ")}</span>
          </li>
        ))}
      </ul>
      {activity.missing.length ? (
        <div className="proposal-missing">
          <strong>Still needed</strong>
          <ul>
            {activity.missing.map((field) => (
              <li key={field}>{field}</li>
            ))}
          </ul>
          <p>Give LifeLine these details in chat.</p>
        </div>
      ) : null}
      {activity.affectedRequirements.length ? (
        <div>
          <strong>Existing requirements affected</strong>
          <ul>
            {activity.affectedRequirements.map((a) => (
              <li key={a}>{a}</li>
            ))}
          </ul>
        </div>
      ) : null}
      <p className="proposal-note">
        This draft changes the active plan only after you confirm.
      </p>
      <div className="proposal-actions">
        <Button
          disabled={busy || proposal.missing_fields.length > 0}
          onClick={onConfirm}
        >
          Confirm
        </Button>
        <Button variant="outline" disabled={busy} onClick={onEdit}>
          Edit in chat
        </Button>
        <Button variant="ghost" disabled={busy} onClick={onCancel}>
          Cancel
        </Button>
      </div>
    </article>
  );
}
