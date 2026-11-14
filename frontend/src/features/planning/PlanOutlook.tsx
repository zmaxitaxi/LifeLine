import type { ComputedPlan,PlanningState } from "../../../../contracts/planning";
import { num } from "@/lib/clinic";
export function PlanOutlook({state,computed}:{state:PlanningState;computed:ComputedPlan|null}){
 const m=computed?.simulation.baseline.metrics;
 const reserve=computed?.simulation.effective_config.reserve_kwh;
 const unknown=!m||m.critical_requested_kwh<=1e-6;
 const shortage=m&&m.critical_unserved_kwh>1e-6;
 const low=m&&reserve!=null&&m.min_soc_kwh<reserve-1e-6;
 const source=computed?.weather_mode==='demo'?'Sample weather · simulated result':state.forecast_reference?.source??'No calculated forecast yet';
 return <section className="plan-outlook" aria-labelledby="outlook-title"><p className="panel-footnote">{state.planning_date} · {source}</p><h2 id="outlook-title">Will we have enough electricity?</h2>
 <p className="outlook-answer">{!computed?'Add your requirements, then ask LifeLine to check the day.':unknown?'Add essential equipment before assessing reliability.':shortage?'Essential equipment may lose power.':low?'Essential needs are covered, but the battery may run too low.':m!.flexible_deferred_kwh>1e-6?'Essential needs are covered. Some other work is unfinished.':'The model covers the day’s requested electricity.'}</p>
 {m?<dl className="outlook-facts"><div><dt>Essential equipment</dt><dd>{unknown?'Requirements incomplete':shortage?`${num(m.critical_unserved_kwh)} kWh short`:'Modeled needs covered'}</dd></div><div><dt>Battery reserve</dt><dd>{unknown?'Not a reliability assessment':low?`${num(reserve!-m.min_soc_kwh)} kWh below target`:'Target met'}</dd></div><div><dt>Other work</dt><dd>{m.flexible_requested_kwh<=1e-6?'No flexible work requested':m.flexible_deferred_kwh>1e-6?`${num(m.flexible_deferred_kwh)} kWh unfinished`:'Modeled work has power'}</dd></div></dl>:null}
 </section>;
}
