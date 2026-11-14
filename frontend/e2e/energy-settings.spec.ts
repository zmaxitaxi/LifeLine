import { test, expect } from '@playwright/test';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { open, seed, calculate, read, overview, weatherFailure } from './support/planning';
test.beforeEach(()=>weatherFailure(false));test.afterEach(()=>weatherFailure(false));
async function powerEditor(page:import('@playwright/test').Page){await overview(page).click();await page.getByRole('button',{name:'Power setup',exact:true}).click();return page.getByRole('dialog',{name:'Clinic power settings',exact:true});}

test('reviewed battery and solar settings genuinely recalculate without calling the model',async({page,request})=>{
  const state=await calculate(request,await seed(request));await open(page,state);let calls=0;page.on('request',r=>{if(r.url().endsWith('/agent'))calls++;});
  const editor=await powerEditor(page);await editor.getByRole('spinbutton',{name:'Planning start charge (%)',exact:true}).fill('25');await editor.getByRole('spinbutton',{name:'Solar panel capacity (kW)',exact:true}).fill('2');
  await editor.getByRole('button',{name:'Review power settings',exact:true}).click();const review=page.getByRole('dialog',{name:'Review power settings',exact:true});await expect(review).toContainText('1.000 kWh stored (25.0%)');
  await page.screenshot({path:join(tmpdir(),'lifeline-power-review-final.png')});
  const draft=await read(request,state.id);expect(draft.energy_settings.initial_battery_kwh).toBe(2);expect(draft.computed_plan!.generation).toBe(state.computed_plan!.generation);
  await review.getByRole('button',{name:'Confirm power settings',exact:true}).click();await expect(review).toBeHidden();
  const updated=await read(request,state.id);expect(updated.energy_settings.initial_battery_kwh).toBe(1);expect(updated.energy_settings.pv_capacity_kw).toBe(2);expect(updated.computed_plan!.generation).toBeGreaterThan(state.computed_plan!.generation);
  expect(updated.computed_plan!.simulation.baseline.hourly[0].soc_start_kwh).toBe(1);expect(updated.computed_plan!.simulation.baseline.metrics.total_solar_kwh).toBeCloseTo(state.computed_plan!.simulation.baseline.metrics.total_solar_kwh*2,8);expect(calls).toBe(0);
  await expect(page.getByTestId('existing-battery')).toHaveAttribute('data-energy-kwh','1');
});

test('capacity edits preserve actual starting energy and a recorded current reading stays separate',async({page,request})=>{
  const state=await seed(request);await open(page,state);const editor=await powerEditor(page);
  await editor.getByRole('spinbutton',{name:'Battery size (kWh)',exact:true}).fill('8');await expect(editor.getByRole('spinbutton',{name:'Planning start charge (%)',exact:true})).toHaveValue('25');
  await editor.getByRole('button',{name:'Record a current battery reading',exact:true}).click();await editor.getByRole('combobox',{name:'Battery reading',exact:true}).selectOption('replace');await editor.getByRole('spinbutton',{name:'Charge shown on the battery display (%)',exact:true}).fill('75');
  await editor.getByRole('button',{name:'Review power settings',exact:true}).click();const review=page.getByRole('dialog',{name:'Review power settings',exact:true});await expect(review).toContainText('starting stored energy stays at 2.000 kWh');await expect(review).toContainText('New current reading: 6.000 kWh');
  await review.getByRole('button',{name:'Confirm power settings',exact:true}).click();await expect(review).toBeHidden();const after=await read(request,state.id);
  expect(after.energy_settings.battery_capacity_kwh).toBe(8);expect(after.energy_settings.initial_battery_kwh).toBe(2);expect(after.current_battery_reading!.energy_kwh).toBe(6);expect(after.computed_plan!.simulation.baseline.hourly[0].soc_start_kwh).toBe(2);
});

test('invalid energy settings are explained and cancelling a draft preserves the current plan',async({page,request})=>{
  const state=await calculate(request,await seed(request));await open(page,state);const editor=await powerEditor(page);await editor.getByRole('spinbutton',{name:'Battery size (kWh)',exact:true}).fill('1');await editor.getByRole('button',{name:'Review power settings',exact:true}).click();await expect(editor.getByRole('alert')).toContainText('large enough');expect((await read(request,state.id)).energy_proposals).toHaveLength(0);
  await editor.getByRole('spinbutton',{name:'Battery size (kWh)',exact:true}).fill('8');await editor.getByRole('button',{name:'Review power settings',exact:true}).click();const review=page.getByRole('dialog',{name:'Review power settings',exact:true});await review.getByRole('button',{name:'Cancel',exact:true}).click();await expect(review).toBeHidden();const after=await read(request,state.id);expect(after.energy_settings).toEqual(state.energy_settings);expect(after.computed_plan!.generation).toBe(state.computed_plan!.generation);
});

test('a confirmed setting survives a forecast failure while stale battery evidence is removed',async({page,request})=>{
  const state=await calculate(request,await seed(request));await open(page,state);const editor=await powerEditor(page);await editor.getByRole('spinbutton',{name:'Planning start charge (%)',exact:true}).fill('10');await editor.getByRole('button',{name:'Review power settings',exact:true}).click();weatherFailure(true);
  await page.getByRole('dialog',{name:'Review power settings',exact:true}).getByRole('button',{name:'Confirm power settings',exact:true}).click();await expect(page.getByRole('dialog')).toHaveCount(0);
  const after=await read(request,state.id);expect(after.energy_settings.initial_battery_kwh).toBeCloseTo(.4,8);expect(after.plan_status).toBe('failed');expect(after.computed_plan).toBeNull();await expect(page.getByTestId('battery-playback')).toHaveCount(0);
});

test('power settings dialog is keyboard accessible on a phone',async({page,request})=>{
  await page.setViewportSize({width:375,height:812});await open(page,await seed(request));await overview(page).click();const trigger=page.getByRole('button',{name:'Power setup',exact:true});await trigger.focus();await page.keyboard.press('Enter');
  const editor=page.getByRole('dialog',{name:'Clinic power settings',exact:true});await expect(editor.getByRole('spinbutton',{name:'Battery size (kWh)',exact:true})).toBeFocused();await page.screenshot({path:join(tmpdir(),'lifeline-power-editor-mobile-final.png')});expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  await page.keyboard.press('Escape');await expect(editor).toBeHidden();await expect(trigger).toBeFocused();
});
