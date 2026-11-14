import { test,expect } from '@playwright/test';
import { apiBase,seed,calculate,open,overview,read,say,initial } from './support/planning';
test('hourly chart, shared timeline and selected comparison use actual backend values',async({page,request})=>{
 const state=await calculate(request,await seed(request));await open(page,state);await overview(page).click();const chart=page.getByRole('region',{name:'Energy through the day',exact:true});
 for(const r of state.computed_plan!.simulation.baseline.hourly){expect(Number(await page.getByTestId(`solar-hour-${r.hour}`).getAttribute('data-kwh'))).toBeCloseTo(r.pv_kwh,9);expect(Number(await page.getByTestId(`used-hour-${r.hour}`).getAttribute('data-kwh'))).toBeCloseTo(r.critical_served_kwh+r.flexible_served_kwh,9);}
 await chart.getByRole('group',{name:'Inspect an energy hour'}).getByRole('button',{name:'10:00',exact:true}).click();await expect(page.getByLabel('Selected simulation time',{exact:true})).toHaveText('10:00');
 await expect(page.getByTestId('day-solar')).toHaveText(`${state.computed_plan!.simulation.baseline.hourly[10].pv_kwh.toFixed(3)} kWh`);
 expect(Number(await page.getByTestId('existing-battery').getAttribute('data-energy-kwh'))).toBeCloseTo(state.computed_plan!.simulation.baseline.hourly[10].soc_start_kwh,9);
 await page.getByRole('button',{name:/All calculated plans/}).click();const option=state.computed_plan!.recovery!.options.find(o=>o.kind==='solar')!;await page.locator(`input[name=clinic-plan][value="${option.id}"]`).click();
 await expect(page.getByLabel('Selected simulation time',{exact:true})).toHaveText('00:00');expect(Number(await page.getByTestId('solar-hour-12').getAttribute('data-kwh'))).toBeCloseTo(option.plan.hourly[12].pv_kwh,9);expect((await read(request,state.id)).computed_plan!.generation).toBe(state.computed_plan!.generation);
 await chart.screenshot({path:'/private/tmp/lifeline-energy-day-evidence.png'});
});

test('only confirmed activities become chart markers and shared devices are not counted twice',async({page,request})=>{
 let state=await seed(request);let response=await request.post(`${apiBase}/${state.id}/proposals`,{data:{expected_revision:state.revision,details:{name:'Vaccination clinic',planning_date:state.planning_date,start_hour:10,end_hour:15,equipment_ids:['fridge']}}});expect(response.ok()).toBe(true);state=await response.json();
 response=await request.post(`${apiBase}/${state.id}/proposals/${state.active_proposal_id}/confirm`,{data:{expected_revision:state.revision,idempotency_key:'chart-vaccination'}});expect(response.ok()).toBe(true);state=await response.json();state=await calculate(request,state);
 expect(state.computed_plan!.simulation.baseline.metrics.critical_requested_kwh).toBeCloseTo(2.4,9);
 await open(page,state);await overview(page).click();const event=page.locator('.energy-events').getByRole('button',{name:'1. Vaccination clinic 10:00–15:00',exact:true});await event.click();await expect(page.getByLabel('Selected simulation time',{exact:true})).toHaveText('10:00');await expect(page.locator('.energy-events')).toContainText('Shared equipment is counted once');
});

test('plans show computed tradeoffs, exactly postponed work and unknown prices',async({page,request})=>{
 const state=await calculate(request,await seed(request));await open(page,state);await overview(page).click();await page.getByRole('button',{name:/All calculated plans/}).click();
 for(const option of [state.computed_plan!.recovery!.existing,...state.computed_plan!.recovery!.options]){const card=page.locator(`.plan-option[data-option-id="${option.id}"]`);await expect(card.getByRole('heading',{name:'Benefits',exact:true})).toBeVisible();await expect(card.getByRole('heading',{name:'Limits',exact:true})).toBeVisible();await expect(card.locator('[data-cost-status]')).toHaveAttribute('data-cost-status','not_estimated');for(const change of option.work_changes.filter(w=>w.explicitly_postponed_kwh>1e-6))await expect(card).toContainText(`${change.explicitly_postponed_kwh.toFixed(3)} kWh`);if(option.infrastructure_changes.length)await expect(card).toContainText('Quote needed');}
});

test('empty electrical requirements never produce a safe overview assessment',async({page,request})=>{
 const base=initial();const state=await calculate(request,await seed(request,{clinic:{...base.clinic,equipment:[]}}));expect(state.computed_plan!.simulation.baseline.metrics.critical_coverage_pct).toBeNull();await open(page,state);await overview(page).click();
 const outlook=page.getByRole('region',{name:'Will we have enough electricity?',exact:true});await expect(outlook).toContainText('Add essential equipment before assessing reliability');await expect(outlook).not.toContainText('Modeled needs covered');await expect(page.getByRole('region',{name:'Plans',exact:true})).toContainText('Not configured');
 await page.getByRole('button',{name:/All calculated plans/}).click();await expect(page.locator('.plan-options-grid')).not.toContainText('Other requested work has power');await expect(page.locator('.plan-options-grid')).not.toContainText('Battery stays at or above');
});

test('public progress arrives before the verified reply and browser commit timing is observable',async({page,request})=>{
 await open(page,await seed(request));let calls=0;page.on('request',r=>{if(r.url().endsWith('/agent/stream'))calls++;});await page.getByLabel('Message LifeLine',{exact:true}).fill('Observe streamed progress for the clinic.');await page.getByRole('button',{name:'Send message',exact:true}).click();
 await expect(page.locator('.chat-weather')).toContainText(/Request received\. Preparing the assistant|The assistant is preparing a reply/);await expect(page.getByTestId('current-plan-summary')).toHaveCount(0);await expect(page.getByLabel('Message LifeLine',{exact:true})).toBeEditable();
 const measures=await page.evaluate(()=>performance.getEntriesByType('measure').map(e=>({name:e.name,duration:e.duration})));const first=measures.find(m=>m.name==='lifeline.first_progress_commit')!,final=measures.find(m=>m.name==='lifeline.answer_commit')!;expect(first.duration).toBeLessThan(final.duration);expect(calls).toBe(1);await expect(page.locator('.chat-transcript')).not.toContainText('UNVERIFIED RAW MODEL TEXT');
});

test('date clarification survives reload without offering a blind retry',async({page,request})=>{
 const state=await seed(request);const failure={code:'DATE_MISMATCH',retryable:false,suggested_action:'review_date',selected_date:'2026-11-14',requested_date:'2026-11-13'};
 await page.route(`**/api/planning/sessions/${state.id}/conversation`,route=>route.fulfill({json:{session_id:state.id,messages:[{id:'date-user',role:'user',content:'Vaccination today at 10',created_at:'2026-11-13T12:00:00Z',mode:null,imported:false,presentation:null},{id:'date-notice',role:'assistant',content:'Different planning day',created_at:'2026-11-13T12:00:01Z',mode:'local_agent_unavailable',failure,imported:false,presentation:null}]}}));
 await open(page,state);await expect(page.locator('.chat-transcript')).toContainText('2026-11-14');await expect(page.locator('.chat-transcript')).toContainText('2026-11-13');await expect(page.getByRole('button',{name:'Retry reply',exact:true})).toHaveCount(0);await page.reload();await expect(page.getByRole('button',{name:'Retry reply',exact:true})).toHaveCount(0);
});

test('an interrupted stream is not retried automatically or treated as a verified result',async({page,request})=>{
 const state=await seed(request);let calls=0;await page.route(`**/api/planning/sessions/${state.id}/agent/stream`,route=>{calls++;return route.fulfill({contentType:'text/event-stream',body:'data: {"type":"progress","stage":"weather","status":"running","elapsed_seconds":0.01}\n\n'});});
 await open(page,state);await say(page,'Check our electricity.');await expect(page.getByRole('alert')).toContainText('before a verified reply arrived');await expect(page.getByTestId('current-plan-summary')).toHaveCount(0);expect(calls).toBe(1);expect((await read(request,state.id)).computed_plan).toBeNull();
});

test('provider status and a verified cloud reply are displayed without calling it local',async({page,request})=>{
 const state=await seed(request);
 await page.route('**/api/agent/status',route=>route.fulfill({json:{mode:'cloud_tool_agent',available:true,model:'verified-cloud-test',provider:'Anthropic Claude API',cloud_ai:true,note:'Fixture status'}}));
 await page.route(`**/api/planning/sessions/${state.id}/agent/stream`,route=>route.fulfill({json:{mode:'cloud_tool_agent',model:'verified-cloud-test',message:'Hello! How can I help with the clinic?',needs_clarification:false,clarification_fields:[],tool_calls:[],presentation:{kind:'conversation',input_revision:null,generation:null,option_ids:[],show_schedule:false},state,message_id:null,user_message_id:null,failure:null,timings:null}}));
 await open(page,state);await say(page,'Hello');await expect(page.locator('.assistant-message')).toContainText('Hello! How can I help with the clinic?');await expect(page.locator('.model-status')).toContainText('Anthropic Claude API');await expect(page.locator('.model-status')).not.toContainText('Local model');await expect(page.getByTestId('current-plan-summary')).toHaveCount(0);
});

test('a schedule-only result offers recovery evaluation without calculating it automatically',async({page,request})=>{
 let state=await seed(request);const result=await request.post(`${apiBase}/${state.id}/recompute`,{data:{expected_revision:state.revision,include_recovery:false}});expect(result.ok()).toBe(true);state=await result.json();expect(state.computed_plan!.recovery).toBeNull();
 await open(page,state);await overview(page).click();await expect(page.getByRole('button',{name:'Compare recovery options',exact:true})).toBeVisible();expect((await read(request,state.id)).computed_plan!.recovery).toBeNull();
 await page.getByRole('button',{name:'Compare recovery options',exact:true}).click();await expect(page.locator('.assistant-message').last()).toBeVisible();expect((await read(request,state.id)).computed_plan!.recovery).not.toBeNull();
});

test('the top outlook makes unconfirmed requirements explicitly excluded',async({page,request})=>{
 let state=await calculate(request,await seed(request));const generation=state.computed_plan!.generation;const response=await request.post(`${apiBase}/${state.id}/proposals`,{data:{expected_revision:state.revision,details:{name:'Outreach draft',planning_date:state.planning_date,start_hour:10,end_hour:15,equipment_ids:['fridge']}}});expect(response.ok()).toBe(true);state=await response.json();await open(page,state);await overview(page).click();
 await expect(page.getByRole('region',{name:'Will we have enough electricity?',exact:true})).toContainText('Results include confirmed requirements only');expect((await read(request,state.id)).computed_plan!.generation).toBe(generation);expect(state.confirmed_activities).toHaveLength(0);
});
