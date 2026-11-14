import { useRef, useState } from "react";
import { useReviewedDialog } from "./useReviewedDialog";
import { X } from "lucide-react";
import type { ActivityDraft, ActivityProposal, PlanningState } from "../../../../contracts/planning";
import { Button } from "@/components/ui/button";
import { ActivityEditor } from "./ActivityEditor";
import { ActivityConfirmation } from "./ActivityConfirmation";

export type ActivitySelection = {kind:"new"} | {kind:"activity" | "proposal";id:string};
export function ActivityWorkspace({selection,state,busy,error,onSave,onConfirm,onReject,onClose}: {
  selection:ActivitySelection; state:PlanningState; busy:boolean; error:string;
  onSave:(details:ActivityDraft,revision:number,proposalId?:string,targetId?:string)=>Promise<string|null>;
  onConfirm:(proposal:ActivityProposal)=>Promise<boolean>;onReject:(proposal:ActivityProposal)=>Promise<boolean>;onClose:()=>void;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  const [proposalId,setProposalId]=useState(selection.kind === "proposal" ? selection.id : undefined);
  const [formVersion,setFormVersion]=useState(0);
  const [editing,setEditing]=useState(selection.kind !== "proposal");
  const proposal = state.proposals.find(p=>p.id===proposalId && p.status === "draft");
  const initial = proposal?.details ?? (selection.kind === "activity" ? state.confirmed_activities.find(a=>a.id===selection.id)?.details : undefined);
  useReviewedDialog(dialog,editing);
  return <dialog ref={dialog} className="chat-settings activity-workspace" aria-labelledby="activity-workspace-title" onCancel={event=>{if(busy)event.preventDefault();else onClose();}} onClose={onClose}>
    <div className="settings-heading"><div><h2 id="activity-workspace-title" tabIndex={-1}>{editing ? selection.kind === "new" && !proposal ? "Add clinic activity" : "Edit clinic activity" : "Review clinic activity"}</h2><p>{editing ? "Tell us when the activity happens and what it needs." : "Check these details before changing the clinic plan."}</p></div><Button variant="ghost" aria-label="Close activity editor" disabled={busy} onClick={onClose}><X /></Button></div>
    {error ? <div role="alert" className="editor-error"><p>{error}</p>{editing ? <Button variant="outline" disabled={busy} onClick={()=>setFormVersion(value=>value+1)}>Reload editor from latest details</Button> : null}</div> : null}
    {editing ? <ActivityEditor key={`${proposalId ?? (selection.kind === "activity" ? selection.id : "new")}-${formVersion}`} state={state} initial={initial} busy={busy} onCancel={onClose} onSave={async(details,revision)=>{const id=await onSave(details,revision,proposal?.id,selection.kind === "activity" ? selection.id : undefined);if(id){setProposalId(id);setEditing(false);}}}/> : proposal ? <ActivityConfirmation proposal={proposal} state={state} busy={busy} onConfirm={()=>void onConfirm(proposal).then(saved=>{if(saved)onClose();})} onCancel={()=>void onReject(proposal).then(saved=>{if(saved)onClose();})} onEdit={()=>setEditing(true)} editLabel="Edit details"/> : <p>This draft is no longer open. <Button variant="outline" onClick={onClose}>Close</Button></p>}
  </dialog>;
}
