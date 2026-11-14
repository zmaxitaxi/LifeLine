/** Genuine Haiku browser rehearsal against an ISOLATED persistent demo server.
 * No mocked AI/weather transports. Weather mode must explicitly be demo.
 * Re-run with --restore after restarting that server to verify disk persistence.
 */
import { createRequire } from 'node:module';
import { mkdir,writeFile,readFile } from 'node:fs/promises';
import { join } from 'node:path';
import { tmpdir } from 'node:os';
import { execFileSync } from 'node:child_process';
const require=createRequire(new URL('../frontend/package.json',import.meta.url));
const {chromium,expect}=require('@playwright/test');
const base=process.env.LIFELINE_DEMO_URL??'http://127.0.0.1:8038';
const dir=process.env.LIFELINE_REHEARSAL_OUTPUT??join(tmpdir(),'lifeline-haiku-full-rehearsal');
await mkdir(dir,{recursive:true,mode:0o700});
const reportPath=join(dir,'rehearsal.json');
const browser=await chromium.launch({headless:true});
let report={passed:false,base,implementation_commit:execFileSync('git',['rev-parse','HEAD'],{encoding:'utf8'}).trim(),started_at:new Date().toISOString(),browser_path:'Browser plugin not available; repository Playwright',viewport:{width:1280,height:1000},provider:'Actual Anthropic Claude Haiku',weather:'Explicit synthetic demo weather',steps:[],errors:[]};
const save=()=>writeFile(reportPath,JSON.stringify(report,null,2)+'\n',{mode:0o600});
try{
 const slots=process.argv.includes('--slots');
 const restore=process.argv.includes('--restore')||slots;
 if(restore)report=JSON.parse(await readFile(reportPath,'utf8'));
 const context=await browser.newContext({viewport:{width:1280,height:1000},...(restore?{storageState:join(dir,'browser-state.json')}: {})});
 const page=await context.newPage();page.on('pageerror',e=>report.errors.push(e.message));
 const getState=async()=>{const id=await page.evaluate(()=>localStorage.getItem('lifeline.planning-session.v1'));const r=await page.request.get(`${base}/api/planning/sessions/${id}`);expect(r.ok()).toBe(true);return r.json();};
 const screenshot=name=>page.screenshot({path:join(dir,`${name}.png`),fullPage:false});
 const readOnlyFields=s=>({clinic:s.clinic,energy:s.energy_settings,inventory:s.equipment_inventory,activities:s.confirmed_activities,reading:s.current_battery_reading});
 async function reloadAndVerify(expected,label){await page.reload();await expect(page.getByLabel('Message LifeLine',{exact:true})).toBeEditable();const actual=await getState();expect(actual).toEqual(expected);report.steps.push({name:label,passed:true,revision:actual.revision});await save();return actual;}
 async function say(name,question){
  await page.getByRole('link',{name:'AI Assistant',exact:true}).click();
  await page.getByLabel('Message LifeLine',{exact:true}).fill(question);
  const pending=page.waitForResponse(r=>r.url().endsWith('/agent/stream')&&r.request().method()==='POST',{timeout:120000});
  const started=performance.now();await page.getByRole('button',{name:'Send message',exact:true}).click();
  const response=await pending;expect(response.ok()).toBe(true);
  const events=(await response.text()).split('\n').filter(l=>l.startsWith('data: ')).map(l=>JSON.parse(l.slice(6)));
  const result=events.find(e=>e.type==='result')?.response;
  report.steps.push({name,question,seconds:(performance.now()-started)/1000,passed:result?.mode==='cloud_tool_agent',response:result,stream_error:events.find(e=>e.type==='error')});await save();
  expect(result?.mode,JSON.stringify(result?{mode:result.mode,message:result.message,failure:result.failure,tools:result.tool_calls}:events.at(-1))).toBe('cloud_tool_agent');
  expect(result.model).toBe('claude-haiku-5-5');expect(result.failure).toBeNull();
  await expect(page.getByLabel('Message LifeLine',{exact:true})).toBeEditable();
  await expect(page.locator('.assistant-message').last()).toContainText(result.message);
  console.log(JSON.stringify({name,seconds:report.steps.at(-1).seconds,tools:result.tool_calls,message:result.message}));
  return result.state;
 }
 async function activityReview(){if(!await page.getByTestId('activity-proposal').isVisible())await page.getByRole('button',{name:/Review activity draft/}).click();return page.getByTestId('activity-proposal');}
 async function powerReview(){if(!await page.getByTestId('energy-proposal').isVisible())await page.getByRole('button',{name:'Review power settings draft',exact:true}).click();return page.getByTestId('energy-proposal');}
 await page.goto(base);expect(await page.title()).toContain('LifeLine');expect(await page.locator('vite-error-overlay').count()).toBe(0);
 const status=await(await page.request.get(`${base}/api/agent/status`)).json();expect(status.available).toBe(true);expect(status.model).toBe('claude-haiku-5-5');expect(status.cloud_ai).toBe(true);
 expect((await(await page.request.get(`${base}/api/weather/mode`)).json()).mode).toBe('demo');
 if(restore){
  await expect(page.getByLabel('Message LifeLine',{exact:true})).toBeEditable();
  expect(await getState()).toEqual(report.final_state);
  if(slots){
   const current=await say('explain_laundry_slots','Using the current optimized schedule, what are the auxiliary laundry\'s hourly slots? Use the existing calculation; do not recalculate or change equipment.');
   expect(current).toEqual(report.final_state);
   report.expected_laundry_allocations=current.computed_plan.simulation.optimized.flexible_tasks.find(t=>t.task_id==='auxiliary_laundry').allocations;
   report.final_conversation=await(await page.request.get(`${base}/api/planning/sessions/${current.id}/conversation`)).json();
   await save();console.log(JSON.stringify({passed:true,allocations:report.expected_laundry_allocations,report:reportPath}));
  }else{
  const conversation=await(await page.request.get(`${base}/api/planning/sessions/${report.final_state.id}/conversation`)).json();
  expect(conversation).toEqual(report.final_conversation);
  report.restart_verified=true;report.steps.push({name:'backend_restart_restores_exact_state_and_conversation',passed:true});await save();
  await screenshot('restored-after-backend-restart');console.log(JSON.stringify({passed:true,restart_verified:true,report:reportPath}));
  }
 }else{
  const started=performance.now();
  await page.getByLabel('Clinic name',{exact:true}).fill('Hackathon rehearsal clinic');
  await page.getByLabel('Clinic location',{exact:true}).selectOption('kisumu');
  await page.getByRole('button',{name:'Continue to electrical setup',exact:true}).click();
  await page.getByRole('button',{name:'Autofill demo setup',exact:true}).click();
  await page.getByRole('button',{name:'Review setup',exact:true}).click();
  await page.getByRole('checkbox',{name:'I have reviewed the inputs and model assumptions.',exact:true}).check();
  await page.getByRole('button',{name:'Open the example clinic',exact:true}).click();
  await expect(page.getByLabel('Message LifeLine',{exact:true})).toBeEditable();
  const initial=await getState();report.initial_state=initial;report.steps.push({name:'fresh_clinic_created_through_ui',passed:true,planning_date:initial.planning_date});await save();
  const fridge=initial.equipment_inventory.find(e=>e.name.toLowerCase().includes('refrigerator'));expect(fridge).toBeTruthy();
  let state=await say('vaccination_draft','Please stage a vaccination campaign tomorrow from 10 AM to 3 PM using the existing vaccine refrigerator. Do not change any device operating hours.');
  expect(readOnlyFields(state)).toEqual(readOnlyFields(initial));expect(state.proposals).toHaveLength(1);
  expect(state.proposals[0].missing_fields).toEqual([]);expect(state.proposals[0].details.start_hour).toBe(10);expect(state.proposals[0].details.end_hour).toBe(15);expect(state.proposals[0].details.equipment_ids).toEqual([fridge.id]);
  await reloadAndVerify(state,'unconfirmed_vaccination_draft_survives_reload');
  const review=await activityReview();await screenshot('vaccination-review');
  const confirmResponse=page.waitForResponse(r=>r.url().endsWith('/confirm')&&r.request().method()==='POST');
  await review.getByRole('button',{name:'Confirm',exact:true}).click();const confirmed=await confirmResponse;expect(confirmed.ok()).toBe(true);
  state=await confirmed.json();await expect(page.getByTestId('activity-proposal')).toHaveCount(0);
  expect(state.confirmed_activities).toHaveLength(1);expect(state.equipment_inventory).toEqual(initial.equipment_inventory);expect(state.plan_status).toBe('current');
  expect(state.computed_plan.simulation.equipment.filter(e=>e.id===fridge.id)).toHaveLength(1);
  const critical=initial.equipment_inventory.filter(e=>e.category==='critical').reduce((a,e)=>a+e.power_kw*e.required_hours.length,0);
  expect(state.computed_plan.simulation.baseline.metrics.critical_requested_kwh).toBeCloseTo(critical,8);
  const duplicate=await page.request.post(confirmed.url(),{data:confirmed.request().postDataJSON()});expect(duplicate.ok()).toBe(true);expect(await duplicate.json()).toEqual(state);
  report.steps.push({name:'explicit_confirmation_and_duplicate_receipt_preserve_one_activity_one_fridge',passed:true});
  await reloadAndVerify(state,'confirmed_vaccination_survives_reload');
  await page.getByRole('link',{name:'Clinic Overview',exact:true}).click();await expect(page.locator('.energy-events')).toContainText(/vaccination/i);await screenshot('confirmed-schedule-and-battery');
  report.scheduling_comparison=state.computed_plan.simulation.comparison;
  const confirmedBeforeRevision=state;
  if(!process.argv.includes('--core')){
  state=await say('vaccination_revision_draft','Create a draft revision of the confirmed vaccination campaign: start at 11 AM tomorrow, keep its 3 PM end and the existing refrigerator. Do not confirm it.');
  expect(state.confirmed_activities).toEqual(confirmedBeforeRevision.confirmed_activities);
  expect(state.proposals.find(p=>p.id===state.active_proposal_id).details.start_hour).toBe(11);
  const editReview=await activityReview();await editReview.getByRole('button',{name:'Cancel',exact:true}).click();await expect(page.getByTestId('activity-proposal')).toHaveCount(0);state=await getState();expect(state.confirmed_activities).toEqual(confirmedBeforeRevision.confirmed_activities);
  report.steps.push({name:'unconfirmed_revision_rejected_without_changing_confirmed_activity',passed:true});await save();
  }
  const beforeWeather=readOnlyFields(state);
  state=await say('cloudy_weather_recovery','Test tomorrow with 50% less sunshine and compare recovery options for our confirmed clinic requirements.');
  expect(state.sunshine_factor).toBe(.5);expect(readOnlyFields(state)).toEqual(beforeWeather);expect(state.computed_plan.recovery.options.length).toBeGreaterThan(3);
  const recovery=state.computed_plan.recovery;report.cloudy_recovery=recovery;
  const solar=recovery.options.find(o=>o.kind==='solar'&&o.modeled_all_requirements_met)??recovery.options.find(o=>o.kind==='solar');expect(solar).toBeTruthy();
  await page.getByRole('link',{name:'Clinic Overview',exact:true}).click();await page.getByRole('button',{name:/All calculated plans/}).click();
  await page.locator(`input[name="clinic-plan"][value="${solar.id}"]`).click();
  state=await getState();expect(state.selected_recovery_intervention_id).toBe(solar.id);expect(readOnlyFields(state)).toEqual(beforeWeather);await screenshot('cloudy-recovery-comparisons');
  const beforeExplain=state;
  if(!process.argv.includes('--core')){
  state=await say('explain_selected_recovery','Please explain my exact selected plan against the existing baseline without recalculating or refreshing weather.');
  expect(state).toEqual(beforeExplain);
  }
  const solarKw=solar.config.pv_capacity_kw;report.reviewed_solar_kw=solarKw;
  const beforePower=state;
  state=await say('power_settings_draft',`Create a draft to set solar panel capacity to ${solarKw} kW. Keep all other energy settings and equipment unchanged. Do not confirm it.`);
  expect(readOnlyFields(state)).toEqual(readOnlyFields(beforePower));
  const power=state.energy_proposals.find(p=>p.id===state.active_energy_proposal_id);expect(power.settings).toEqual({pv_capacity_kw:solarKw});
  await reloadAndVerify(state,'unconfirmed_power_draft_survives_reload');
  const powerCard=await powerReview();await screenshot('power-settings-review');
  const powerPending=page.waitForResponse(r=>r.url().includes('/energy-proposals/')&&r.url().endsWith('/confirm')&&r.request().method()==='POST');
  await powerCard.getByRole('button',{name:'Confirm power settings',exact:true}).click();const powerResponse=await powerPending;expect(powerResponse.ok()).toBe(true);state=await powerResponse.json();
  await expect(page.getByTestId('energy-proposal')).toHaveCount(0);
  expect(state.energy_settings.pv_capacity_kw).toBe(solarKw);expect(state.energy_settings.initial_battery_kwh).toBe(initial.energy_settings.initial_battery_kwh);expect(state.current_battery_reading).toBe(initial.current_battery_reading);expect(state.equipment_inventory).toEqual(initial.equipment_inventory);expect(state.confirmed_activities).toEqual(confirmedBeforeRevision.confirmed_activities);expect(state.plan_status).toBe('current');
  await reloadAndVerify(state,'confirmed_power_settings_and_activity_survive_reload');
  report.final_state=state;report.final_conversation=await(await page.request.get(`${base}/api/planning/sessions/${state.id}/conversation`)).json();
  expect(report.errors).toEqual([]);report.total_flow_seconds=(performance.now()-started)/1000;report.passed=true;
  await context.storageState({path:join(dir,'browser-state.json')});await save();await screenshot('final-saved-clinic');
  console.log(JSON.stringify({passed:true,seconds:report.total_flow_seconds,report:reportPath,solar_kw:solarKw,activity_count:state.confirmed_activities.length,model_steps:report.steps.filter(s=>s.question).map(s=>({name:s.name,seconds:s.seconds}))}));
 }
}catch(e){report.passed=false;report.failure=String(e);await save();throw e;}finally{await browser.close();}
