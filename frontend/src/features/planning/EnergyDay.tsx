import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Disclosure } from "@/components/Disclosure";
import type { PlanningState, ComputedPlan } from "../../../../contracts/planning";
import type { RecoveryOption } from "../../../../contracts/recovery";
import { BatterySummary } from "./BatterySummary";
import { num } from "@/lib/clinic";
import { recoveryTitle } from "./plan-language";

const clock=(h:number)=>`${String(h).padStart(2,'0')}:00`;
export function EnergyDay({state,computed,selected,busy,onSettings}:{state:PlanningState;computed:ComputedPlan|null;selected?:RecoveryOption;busy:boolean;onSettings:()=>void}){
 const [hour,setHour]=useState(0);
 const [seek,setSeek]=useState<{hour:number}>();
 const plan=selected?.plan??computed?.simulation.baseline;
 const rows=plan?.hourly??[];
 const row=rows[Math.min(hour,23)];
 const events=state.confirmed_activities.filter(a=>a.details.planning_date===state.planning_date&&a.details.start_hour!=null&&a.details.end_hour!=null);
 const max=Math.max(.1,...rows.map(r=>Math.max(r.pv_kwh,r.critical_served_kwh+r.flexible_served_kwh+r.critical_unserved_kwh+r.flexible_unserved_kwh)));
 const scale=104/max,zero=140,left=42,slot=29;
 const inspect=(h:number)=>setSeek({hour:h});
 return <section className="energy-day overview-section" data-overview-section="energy" aria-labelledby="energy-title">
  <div className="panel-heading"><h2 id="energy-title">Energy through the day</h2><Button variant="outline" disabled={busy} onClick={onSettings}>Power setup</Button></div>
  {!computed||!plan?<p className="panel-lead">{state.equipment_inventory.length?'Ask LifeLine to calculate the day’s electricity, then inspect its hourly results here.':'Add equipment requirements before assessing electricity.'}</p>:<>
   <p className="panel-footnote">{state.planning_date} · {computed.simulation.timezone} · {computed.weather_mode==='demo'?'Simulated with sample weather':'Forecast-based simulation'} · {selected?.kind==='existing'||!selected?'Current plan':`Selected comparison: ${recoveryTitle(selected.kind)}`}</p>
   {busy?<p role="status" className="panel-footnote">LifeLine is working. Showing the last verified calculation.</p>:null}
   <div className="energy-day-layout">
    <div className="energy-chart-column">
     <figure className="energy-day-chart" aria-label="Hourly solar and equipment energy">
      <figcaption><span>+ Solar available</span><span>− Equipment supplied</span><span>▧ Power missing</span></figcaption>
      <svg viewBox="0 0 760 284" role="img" aria-label="Electricity available from solar and supplied to equipment each hour, in kWh">
       <defs><pattern id="missing-energy" patternUnits="userSpaceOnUse" width="5" height="5"><path d="M0 5L5 0" stroke="#993b2d" strokeWidth="1.5"/></pattern></defs>
       {[1,0,-1].map(t=><g key={t}><line x1={left} y1={zero-t*104} x2="738" y2={zero-t*104} stroke="#dce5de"/><text x="2" y={zero-t*104+4} fontSize="12" fill="#566c61">{t===0?'0':`${t>0?'+':'−'}${max.toFixed(1)}`}</text></g>)}
       <text x="4" y="16" fontSize="12" fill="#566c61">kWh / hour</text>
       {rows.map(r=>{const used=r.critical_served_kwh+r.flexible_served_kwh;const missing=r.critical_unserved_kwh+r.flexible_unserved_kwh;const x=left+r.hour*slot;return <g key={r.hour}>
        {hour===r.hour?<rect x={x-2} y="24" width={slot} height="232" fill="#edf4ef"/>:null}
        <rect data-testid={`solar-hour-${r.hour}`} data-kwh={r.pv_kwh} x={x+3} y={zero-r.pv_kwh*scale} width="19" height={r.pv_kwh*scale} fill="#117457"/>
        <rect data-testid={`used-hour-${r.hour}`} data-kwh={used} x={x+3} y={zero} width="19" height={used*scale} fill="#566c61"/>
        {missing>1e-6?<rect data-testid={`missing-hour-${r.hour}`} data-kwh={missing} x={x+3} y={zero+used*scale} width="19" height={missing*scale} fill="url(#missing-energy)" stroke="#993b2d"/>:null}
        <title>{clock(r.hour)}: solar {num(r.pv_kwh)} kWh; equipment supplied {num(used)} kWh; power missing {num(missing)} kWh</title>
       </g>;})}
       {events.map((a,i)=><g key={a.id}><line x1={left+a.details.start_hour!*slot+slot/2} x2={left+a.details.start_hour!*slot+slot/2} y1="28" y2="252" stroke="#273743" strokeDasharray="4 4"/><circle cx={left+a.details.start_hour!*slot+slot/2} cy="22" r="10" fill="white" stroke="#117457"/><text x={left+a.details.start_hour!*slot+slot/2} y="26" textAnchor="middle" fontSize="12">{i+1}</text><title>{a.details.name} begins at {clock(a.details.start_hour!)}</title></g>)}
       {[0,6,12,18,24].map(h=><text key={h} x={left+h*slot} y="275" textAnchor={h===24?'end':'middle'} fontSize="12" fill="#566c61">{clock(h)}</text>)}
      </svg>
     </figure>
     <div className="energy-hour-picker" role="group" aria-label="Inspect an energy hour">{Array.from({length:25},(_,h)=><button key={h} type="button" aria-pressed={hour===h} onClick={()=>inspect(h)}>{clock(h)}</button>)}</div>
     <div className="energy-hour-readout" aria-live="polite"><strong>{hour===24?'End of day':`${clock(hour)}–${clock(hour+1)}`}</strong>{hour<24&&row?<dl><div><dt>Solar available</dt><dd data-testid="day-solar">{num(row.pv_kwh)} kWh</dd></div><div><dt>Equipment supplied</dt><dd data-testid="day-used">{num(row.critical_served_kwh+row.flexible_served_kwh)} kWh</dd></div><div><dt>Power missing</dt><dd data-testid="day-missing">{num(row.critical_unserved_kwh+row.flexible_unserved_kwh)} kWh</dd></div></dl>:<p>The battery shows the final calculated stored energy.</p>}</div>
     {events.length?<div className="energy-events"><h3>Clinic activities</h3>{events.map((a,i)=><button type="button" key={a.id} onClick={()=>inspect(a.details.start_hour!)}><strong>{i+1}. {a.details.name}</strong><span>{clock(a.details.start_hour!)}–{clock(a.details.end_hour!)}</span></button>)}<p className="panel-footnote">Numbered markers show confirmed activity starts. Shared equipment is counted once in the energy calculation.</p></div>:null}
     <Disclosure title="Equipment requested or scheduled at this hour" keepMounted={false}>{hour===24?<p>The simulated day has ended.</p>:<ul>{(selected?.simulation.equipment??computed.simulation.equipment).filter(e=>e.category==='critical'?e.required_hours.includes(hour):plan.flexible_tasks.some(t=>t.task_id===e.id&&t.allocations.some(a=>a.hour===hour&&a.served_kwh>1e-6))).map(e=><li key={e.id}>{e.name} · {e.category==='critical'?'Essential requirement':'Scheduled work'}</li>)}</ul>}</Disclosure>
     <p className="panel-footnote">Hourly model values. Solar shown may include unused energy; power missing is not supplied. Activity times do not imply a verified medical procedure.</p>
    </div>
    <aside className="energy-battery-side" role="region" aria-label="Battery & Energy"><BatterySummary computed={computed} date={state.planning_date} selected={selected} onHourChange={setHour} seekRequest={seek}/><Disclosure title="Battery assumptions" keepMounted={false}><p>Assumed midnight stored energy: {num(computed.simulation.effective_config.initial_battery_kwh)} kWh. Not a current measurement.</p><p>{state.current_battery_reading?`Recorded reading: ${num(state.current_battery_reading.energy_kwh)} kWh at ${state.current_battery_reading.measured_at}.`:'No current battery reading recorded.'}</p></Disclosure></aside>
   </div>
  </>}
 </section>;
}
