import type { RecoveryOption } from "../../../../contracts/recovery";
import type { ComputedPlan } from "../../../../contracts/planning";
import { Button } from "@/components/ui/button";
import { Disclosure } from "@/components/Disclosure";
import { shortName, timeRanges, num } from "@/lib/clinic";
import { recoveryTitle } from "./plan-language";

const partNames={pv_capacity_kw:'Solar panels',battery_capacity_kwh:'Battery size',max_discharge_kw:'Battery output limit'};
const hours=(task:{allocations:{hour:number;served_kwh:number}[]}|undefined)=>timeRanges(task?.allocations.filter(a=>a.served_kwh>1e-6).map(a=>a.hour)??[])||'Not scheduled';
function Tradeoffs({option}:{option:RecoveryOption}){
 const m=option.metrics;const benefits:string[]=[],limits:string[]=[];
 if(m.essential_requested_kwh<=1e-6)limits.push('Essential equipment requirements are incomplete.');
 else if(m.essential_unserved_kwh<=1e-6)benefits.push('Essential equipment needs covered in the model.');
 else limits.push(`${num(m.essential_unserved_kwh)} kWh of essential power still missing.`);
 if(m.reserve_shortfall_kwh<=1e-6)benefits.push('Battery stays at or above its reserve target.');else limits.push(`Battery still falls ${num(m.reserve_shortfall_kwh)} kWh below reserve.`);
 if(m.flexible_unfinished_kwh<=1e-6)benefits.push('All requested work has power in the model.');else limits.push(`${num(m.flexible_unfinished_kwh)} kWh of original work remains unfinished.`);
 if(option.infrastructure_changes.length)limits.push('Requires a technical review; hardware changes are hypothetical.');
 return <div className="plan-tradeoffs"><div><h4>Benefits</h4><ul>{benefits.length?benefits.map(s=><li key={s}>{s}</li>):<li>No complete resolution in this result.</li>}</ul></div><div><h4>Limits</h4><ul>{limits.length?limits.map(s=><li key={s}>{s}</li>):<li>Depends on the weather and equipment assumptions.</li>}</ul></div></div>;
}
function WorkChanges({option}:{option:RecoveryOption}){
 const missed=option.plan.flexible_tasks.filter(t=>t.deferred_kwh>1e-6);
 return <div className="plan-work-changes"><h4>What will not run?</h4>{!option.work_changes.some(w=>w.explicitly_postponed_kwh>1e-6)&&!missed.length?<p>No requested flexible work is removed or left unsupplied.</p>:<ul>{option.work_changes.filter(w=>w.explicitly_postponed_kwh>1e-6).map(w=><li key={w.equipment_id}><strong>{shortName(w.name)}:</strong> {num(w.explicitly_postponed_kwh)} kWh of its original {num(w.original_required_kwh)} kWh requirement postponed.</li>)}{missed.map(t=><li key={t.task_id}><strong>{shortName(option.simulation.equipment.find(e=>e.id===t.task_id)?.name??t.task_id)}:</strong> {num(t.deferred_kwh)} kWh of the tested request is not supplied.</li>)}</ul>}</div>;
}
function Cost({option}:{option:RecoveryOption}){return <div className="plan-cost" data-cost-status={option.parts_cost?.status??'not_estimated'}><p><strong>Parts cost:</strong> {option.infrastructure_changes.length?'Quote needed — no price estimate is available.':'No new parts proposed. Operating costs are not estimated.'}</p>{option.infrastructure_changes.length&&option.parts_cost?<p>{option.parts_cost.explanation}</p>:null}</div>;}

export function SolutionsSection({computed,busy,onChat,selected,onSelect}:{computed:ComputedPlan|null;busy:boolean;onChat:(question:string)=>void;selected?:RecoveryOption;onSelect:(id:string)=>void}){
 const recovery=computed?.recovery;
 const recommended=recovery?[recovery.existing,...recovery.options].find(o=>o.id===recovery.recommended_option_id):undefined;
 const before=computed?.simulation.baseline;
 const currentMeets=Boolean(before&&before.metrics.critical_requested_kwh>1e-6&&before.metrics.critical_unserved_kwh<=1e-6&&before.metrics.flexible_deferred_kwh<=1e-6&&before.metrics.min_soc_kwh>=computed!.simulation.effective_config.reserve_kwh-1e-6);
 const focus=selected&&selected.kind!=='existing'?selected:currentMeets?recovery?.existing:recommended;
 const after=focus?.plan??computed?.simulation.optimized;
 const gear=focus?.simulation.equipment??computed?.simulation.equipment??[];
 const changed=after?.flexible_tasks.filter(t=>hours(t)!==hours(before?.flexible_tasks.find(b=>b.task_id===t.task_id)))??[];
 const actions=[...(focus?.infrastructure_changes.map(c=>`${partNames[c.field]}: ${num(c.before)} → ${num(c.after)} ${c.unit}. Review this hypothetical change with a technician.`)??[]),...changed.map(t=>`${shortName(gear.find(e=>e.id===t.task_id)?.name??t.task_id)} work window: ${hours(before?.flexible_tasks.find(b=>b.task_id===t.task_id))} → ${hours(t)}.`),...(focus?.work_changes.filter(w=>w.explicitly_postponed_kwh>1e-6).map(w=>`Postpone ${num(w.explicitly_postponed_kwh)} kWh of ${shortName(w.name)} work.`)??[])];
 return <section data-overview-section="solutions" className="overview-section overview-plans" aria-label="Plans" tabIndex={0}>
  <h2 id="solutions-title">Plans &amp; next steps</h2>
  {computed&&before&&after?<>
   <div className="recommended-plan"><div><p className="plan-kicker">{focus?.kind==='existing'&&currentMeets?'No change needed under these assumptions':focus?.id===recovery?.recommended_option_id?'Recommended option':'Selected comparison'}</p><h3>{focus?recoveryTitle(focus.kind):'Use the calculated equipment schedule'}</h3><p className="panel-footnote">A proposed plan, not a physical change to the clinic.</p></div>{focus&&focus.id!==selected?.id?<Button variant="outline" disabled={busy} onClick={()=>onSelect(focus.id)}>Compare recommended plan</Button>:null}</div>
   {actions.length?<ol className="recommended-actions">{actions.slice(0,3).map(a=><li key={a}>{a}</li>)}</ol>:<p className="panel-footnote">No equipment-time or hardware changes in this result.</p>}
   <table className="plan-outcomes"><caption>Current plan compared with {focus?recoveryTitle(focus.kind).toLowerCase():'the calculated schedule'}</caption><thead><tr><th scope="col">Daily outcome</th><th scope="col">Current</th><th scope="col">Proposed</th></tr></thead><tbody>
    <tr><th scope="row">Essential power</th>{[before.metrics,after.metrics].map((m,i)=><td key={i}>{m.critical_requested_kwh<=1e-6?'Not configured':m.critical_unserved_kwh>1e-6?`${num(m.critical_unserved_kwh)} kWh short`:'Needs covered'}</td>)}</tr>
    <tr><th scope="row">Battery reserve</th><td>{before.metrics.min_soc_kwh<computed.simulation.effective_config.reserve_kwh-1e-6?'Below target':'Target met'}</td><td>{after.metrics.min_soc_kwh<(focus?.config.reserve_kwh??computed.simulation.effective_config.reserve_kwh)-1e-6?'Below target':'Target met'}</td></tr>
    <tr><th scope="row">Unfinished work</th><td>{num(before.metrics.flexible_deferred_kwh)} kWh</td><td>{num(focus?.metrics.flexible_unfinished_kwh??after.metrics.flexible_deferred_kwh)} kWh</td></tr>
   </tbody></table>
   {focus?<><WorkChanges option={focus}/>{focus.infrastructure_changes.length?<Cost option={focus}/>:null}</>:null}
   <Disclosure title="Equipment times in this plan" keepMounted={false}><ul>{after.flexible_tasks.map(t=><li key={t.task_id}><strong>{shortName(gear.find(e=>e.id===t.task_id)?.name??t.task_id)}:</strong> {hours(t)} · {num(t.served_kwh)} kWh supplied.</li>)}</ul></Disclosure>
   {recovery?<Disclosure title={`All calculated plans (${recovery.options.length+1})`} keepMounted={false}><fieldset className="plan-choices"><legend>Choose a calculated comparison</legend><div className="plan-options-grid">{[recovery.existing,...recovery.options].map(option=><article key={option.id} className="plan-option" data-option-id={option.id} data-selected={selected?.id===option.id}>
    <label className="plan-option-choice"><input type="radio" name="clinic-plan" value={option.id} checked={selected?.id===option.id} disabled={busy} onChange={()=>onSelect(option.id)} aria-label={`${option.kind==='existing'?'Current plan':recoveryTitle(option.kind)}${option.infrastructure_changes.length?` · ${option.infrastructure_changes.map(c=>`${c.after} ${c.unit}`).join(', ')}`:''}`}/><strong>{option.kind==='existing'?'Current plan':recoveryTitle(option.kind)}</strong>{option.id===recovery.recommended_option_id?<small>Recommended</small>:null}</label>
    {option.infrastructure_changes.map(c=><p key={c.field}>{partNames[c.field]}: {num(c.before)} → {num(c.after)} {c.unit}</p>)}
    <Tradeoffs option={option}/><WorkChanges option={option}/><Cost option={option}/>
    <Disclosure title="Exact results and remaining constraints" keepMounted={false}><p>Essential power missing: {num(option.metrics.essential_unserved_kwh)} kWh. Minimum stored energy: {num(option.metrics.minimum_battery_kwh)} kWh. Reserve shortfall: {num(option.metrics.reserve_shortfall_kwh)} kWh.</p><ul>{option.remaining_constraints.map(s=><li key={s}>{s}</li>)}</ul></Disclosure>
   </article>)}</div></fieldset></Disclosure>:null}
  </>:<p className="panel-lead">{computed?'Essential requirements need review.':'Confirm your equipment and activities, then ask LifeLine to assess electricity.'}</p>}
  <Button variant="outline" disabled={busy} onClick={()=>onChat(computed?'Explain the selected plan and the most relevant next action in plain English. Use the existing calculated result; do not recalculate.':'Assess the clinic electricity requirements and recommend what to do next.')}>{computed?'Ask LifeLine about this plan':'Ask LifeLine to check the day'}</Button>
  {computed&&!recovery?<Button variant="outline" disabled={busy} onClick={()=>onChat('Compare recovery options for our confirmed clinic requirements and recommend the most useful next action.')}>Compare recovery options</Button>:null}
 </section>;
}
