import { useRef, useState } from "react";
import { useReviewedDialog } from "./useReviewedDialog";
import { X } from "lucide-react";
import type { EnergySettingsProposal, PlanningState } from "../../../../contracts/planning";
import { Button } from "@/components/ui/button";
import { EnergySettingsEditor, type EnergyFormValue } from "./EnergySettingsEditor";
import { EnergySettingsReview } from "./EnergySettingsReview";
export type EnergySelection = {kind:"new"}|{kind:"proposal";id:string};
export function EnergySettingsWorkspace({selection,state,busy,error,onSave,onConfirm,onReject,onClose}: {
  selection:EnergySelection;state:PlanningState;busy:boolean;error:string;
  onSave:(value:EnergyFormValue,revision:number,proposalId?:string)=>Promise<string|null>;
  onConfirm:(proposal:EnergySettingsProposal)=>Promise<boolean>;onReject:(proposal:EnergySettingsProposal)=>Promise<boolean>;onClose:()=>void;
}) {
  const dialog=useRef<HTMLDialogElement>(null);
  const [proposalId,setProposalId]=useState(selection.kind === "proposal" ? selection.id : undefined);
  const [editing,setEditing]=useState(selection.kind === "new");const [formVersion,setFormVersion]=useState(0);
  const proposal=state.energy_proposals.find(p=>p.id===proposalId && p.status === "draft");
  const stale=Boolean(proposal && proposal.base_input_revision !== state.input_revision);
  async function save(value:EnergyFormValue,revision:number){
    const combined=stale && proposal ? {settings:{...proposal.settings,...value.settings},reading:value.reading === undefined && proposal.updates_current_battery_reading ? proposal.current_battery_reading : value.reading} : value;
    const id=await onSave(combined,revision,stale ? undefined : proposal?.id);if(id){setProposalId(id);setEditing(false);}
  }
  useReviewedDialog(dialog,editing);
  return <dialog ref={dialog} className="chat-settings energy-workspace" aria-labelledby="energy-workspace-title" onCancel={event=>{if(busy)event.preventDefault();else onClose();}} onClose={onClose}>
    <div className="settings-heading"><div><h2 id="energy-workspace-title" tabIndex={-1}>{editing ? "Clinic power settings" : "Review power settings"}</h2><p>{editing ? "Set the clinic’s power setup and planning assumptions." : "Check what changes before updating the plan."}</p></div><Button variant="ghost" aria-label="Close power settings" disabled={busy} onClick={onClose}><X /></Button></div>
    {error ? <div role="alert" className="editor-error"><p>{error}</p>{editing ? <Button variant="outline" disabled={busy} onClick={()=>setFormVersion(v=>v+1)}>Reload editor from latest details</Button> : null}</div> : null}
    {stale ? <div className="editor-error" role="alert"><p>The clinic inputs changed after this draft. Review a fresh proposal before confirming.</p><Button variant="outline" disabled={busy} onClick={()=>void save({settings:proposal!.settings,reading:proposal!.updates_current_battery_reading ? proposal!.current_battery_reading : undefined},state.revision)}>Start a new review</Button></div> : null}
    {editing ? <EnergySettingsEditor key={`${proposalId ?? "new"}-${formVersion}`} current={proposal?.proposed_energy_settings ?? state.energy_settings} date={state.planning_date} timezone={state.timezone} reading={proposal?.updates_current_battery_reading ? proposal.current_battery_reading : state.current_battery_reading} revision={state.revision} busy={busy} allowUnchanged={Boolean(proposal)} onCancel={onClose} onSave={save}/> : proposal ? <EnergySettingsReview current={state.energy_settings} proposed={proposal.proposed_energy_settings} changes={proposal.settings} date={state.planning_date} timezone={state.timezone} reading={proposal.current_battery_reading} updatesReading={proposal.updates_current_battery_reading} busy={busy} confirmDisabled={stale} onConfirm={()=>void onConfirm(proposal).then(saved=>{if(saved)onClose();})} onCancel={()=>void onReject(proposal).then(saved=>{if(saved)onClose();})} onEdit={()=>setEditing(true)}/> : <p>This draft is no longer open. <Button variant="outline" onClick={onClose}>Close</Button></p>}
  </dialog>;
}
