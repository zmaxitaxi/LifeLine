import { test, expect } from "@playwright/test";
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { apiBase, open, seed, read, calculate, overview, assistant, say } from "./support/planning";

async function addActivity(page:import('@playwright/test').Page,name="Vaccination campaign") {
  await overview(page).click();await page.getByRole('button',{name:'Add activity',exact:true}).click();
  const editor=page.getByRole('dialog',{name:'Add clinic activity',exact:true});
  await editor.getByRole('textbox',{name:'Activity name',exact:true}).fill(name);
  await editor.getByRole('combobox',{name:'Start time',exact:true}).selectOption('9');
  await editor.getByRole('combobox',{name:'Finish time',exact:true}).selectOption('15');
  await editor.getByRole('checkbox',{name:'Vaccine refrigerator · 100 W',exact:true}).check();
  await editor.getByRole('button',{name:'Review activity',exact:true}).click();
  return page.getByRole('dialog',{name:'Review clinic activity',exact:true});
}

test('Overview creates and edits an activity without requiring Llama or applying an unconfirmed draft',async({page,request})=>{
  const initial=await calculate(request,await seed(request));await open(page,initial);let agentCalls=0;page.on('request',r=>{if(r.url().endsWith('/agent'))agentCalls++;});
  const review=await addActivity(page);await expect(overview(page)).toHaveAttribute('aria-current','page');
  await page.screenshot({path:join(tmpdir(),'lifeline-activity-review-final.png')});
  await expect(review).toContainText('09:00–15:00');await expect(review.getByRole('button',{name:'Confirm',exact:true})).toBeEnabled();
  const draft=await read(request,initial.id);expect(draft.confirmed_activities).toHaveLength(0);expect(draft.input_revision).toBe(initial.input_revision);expect(draft.computed_plan!.generation).toBe(initial.computed_plan!.generation);
  await review.getByRole('button',{name:'Confirm',exact:true}).click();await expect(review).toBeHidden();
  const after=await read(request,initial.id);expect(after.confirmed_activities).toHaveLength(1);expect(after.input_revision).toBeGreaterThan(initial.input_revision);expect(after.computed_plan!.generation).toBeGreaterThan(initial.computed_plan!.generation);
  const activity=page.getByTestId('confirmed-activity');await expect(activity).toContainText('Vaccination campaign');await activity.getByRole('button').click();
  const editor=page.getByRole('dialog',{name:'Edit clinic activity',exact:true});await editor.getByRole('combobox',{name:'Start time',exact:true}).selectOption('10');await editor.getByRole('button',{name:'Review activity',exact:true}).click();
  expect((await read(request,initial.id)).confirmed_activities[0].details.start_hour).toBe(9);
  await page.getByRole('dialog',{name:'Review clinic activity',exact:true}).getByRole('button',{name:'Confirm',exact:true}).click();await expect(page.getByRole('dialog')).toHaveCount(0);
  const updated=await read(request,initial.id);expect(updated.confirmed_activities).toHaveLength(1);expect(updated.confirmed_activities[0].details.start_hour).toBe(10);expect(updated.computed_plan!.simulation.optimized.metrics.critical_requested_kwh).toBeCloseTo(2.4,8);expect(agentCalls).toBe(0);
  await assistant(page).click();await expect(page.locator('.chat-transcript')).toContainText('Activity confirmed.');await expect(page.getByTestId('current-plan-summary')).toHaveCount(1);
  await say(page,'What are the confirmed activities?');await expect(page.locator('.assistant-message').last()).toContainText('Vaccination campaign');expect((await read(request,initial.id)).computed_plan!.generation).toBe(updated.computed_plan!.generation);
});

test('a staged Overview activity can be edited or rejected from either page',async({page,request})=>{
  const initial=await seed(request);await open(page,initial);const review=await addActivity(page,'Outreach day');
  await review.getByRole('button',{name:'Close activity editor',exact:true}).click();await expect(page.getByRole('button',{name:'Outreach day · draft · review',exact:true})).toBeVisible();
  await assistant(page).click();await page.getByRole('button',{name:'Review activity draft · Outreach day',exact:true}).click();
  const editor=page.getByRole('dialog',{name:'Review clinic activity',exact:true});await editor.getByRole('button',{name:'Edit details',exact:true}).click();
  await page.getByRole('dialog',{name:'Edit clinic activity',exact:true}).getByRole('textbox',{name:'Activity name',exact:true}).fill('Community outreach');await page.getByRole('button',{name:'Review activity',exact:true}).click();
  const newReview=page.getByRole('dialog',{name:'Review clinic activity',exact:true});await expect(newReview).toContainText('Community outreach');await newReview.getByRole('button',{name:'Cancel',exact:true}).click();await expect(page.getByRole('dialog')).toHaveCount(0);
  const state=await read(request,initial.id);expect(state.confirmed_activities).toHaveLength(0);expect(state.proposals[0].status).toBe('rejected');
});

test('concurrent changes require reloading the manual editor rather than replaying an edit',async({page,request})=>{
  const state=await seed(request);await open(page,state);await overview(page).click();await page.getByRole('button',{name:'Add activity',exact:true}).click();
  const editor=page.getByRole('dialog',{name:'Add clinic activity',exact:true});await editor.getByRole('textbox',{name:'Activity name',exact:true}).fill('Unsaved manual activity');
  const external=await request.post(`${apiBase}/${state.id}/proposals`,{data:{expected_revision:state.revision,details:{name:'Another operator draft'}}});expect(external.ok()).toBe(true);
  await editor.getByRole('button',{name:'Review activity',exact:true}).click();await expect(editor.getByRole('alert')).toContainText('changed elsewhere');expect((await read(request,state.id)).proposals).toHaveLength(1);
  await editor.getByRole('button',{name:'Reload editor from latest details',exact:true}).click();await expect(editor.getByRole('textbox',{name:'Activity name',exact:true})).toHaveValue('');
});

test('editing an activity changes the real daily pump work budget without duplicating equipment',async({page,request})=>{
  const state=await seed(request);await open(page,state);await overview(page).click();await page.getByRole('button',{name:'Add activity',exact:true}).click();
  const editor=page.getByRole('dialog',{name:'Add clinic activity',exact:true});await editor.getByRole('textbox',{name:'Activity name',exact:true}).fill('Water preparation');await editor.getByRole('combobox',{name:'Start time',exact:true}).selectOption('8');await editor.getByRole('combobox',{name:'Finish time',exact:true}).selectOption('16');
  await editor.getByRole('checkbox',{name:'Water pump · up to 500 W',exact:true}).check();await editor.getByRole('spinbutton',{name:'Water pump: required daily operating hours',exact:true}).fill('3');await editor.getByRole('button',{name:'Review activity',exact:true}).click();
  await page.getByRole('dialog',{name:'Review clinic activity',exact:true}).getByRole('button',{name:'Confirm',exact:true}).click();await expect(page.getByRole('dialog')).toHaveCount(0);
  const after=await read(request,state.id);expect(after.equipment_inventory).toHaveLength(2);expect(after.computed_plan!.simulation.optimized.metrics.flexible_requested_kwh).toBe(1.5);expect(after.computed_plan!.simulation.optimized.metrics.critical_requested_kwh).toBeCloseTo(2.4,8);
  const pump=page.locator('.equipment-item').filter({hasText:'Water pump'});await pump.locator('summary').click();await expect(pump).toContainText('1.500 kWh');await expect(pump).toContainText('3 total daily operating hours');
});

test('an incomplete equipment draft can be completed manually before confirmation',async({page,request})=>{
  const state=await seed(request);await open(page,state);await overview(page).click();await page.getByRole('button',{name:'Add equipment',exact:true}).click();
  const equipment=page.getByRole('dialog',{name:'Add clinic equipment',exact:true});await equipment.getByRole('textbox',{name:'Equipment name',exact:true}).fill('Portable light');await equipment.getByRole('button',{name:'Review equipment',exact:true}).click();
  const review=page.getByRole('dialog',{name:'Review clinic activity',exact:true});await expect(review.getByRole('button',{name:'Confirm',exact:true})).toBeDisabled();await review.getByRole('button',{name:'Edit details',exact:true}).click();
  const editor=page.getByRole('dialog',{name:'Edit clinic activity',exact:true});await editor.getByRole('combobox',{name:'Start time',exact:true}).selectOption('10');await editor.getByRole('combobox',{name:'Finish time',exact:true}).selectOption('12');await editor.getByRole('combobox',{name:'Does Portable light need protected power?',exact:true}).selectOption('critical');await editor.getByRole('spinbutton',{name:'Portable light power rating (W)',exact:true}).fill('200');await editor.getByRole('checkbox',{name:'Require this device throughout the activity’s hours',exact:true}).check();
  await editor.getByRole('button',{name:'Review activity',exact:true}).click();await expect(review.getByRole('button',{name:'Confirm',exact:true})).toBeEnabled();await review.getByRole('button',{name:'Confirm',exact:true}).click();await expect(page.getByRole('dialog')).toHaveCount(0);
  const after=await read(request,state.id);expect(after.equipment_inventory).toHaveLength(3);expect(after.computed_plan!.simulation.optimized.metrics.critical_requested_kwh).toBeCloseTo(2.8,8);
});
