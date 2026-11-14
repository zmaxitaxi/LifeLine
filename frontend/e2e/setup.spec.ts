import { test,expect,type Page } from '@playwright/test';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { apiBase,seed,read,say } from './support/planning';

test.beforeEach(async({page})=>{await page.clock.setFixedTime(new Date('2026-11-13T09:00:00Z'));});

async function locationStep(page:Page){
 await page.getByRole('textbox',{name:'Clinic name',exact:true}).fill('Community clinic');
 await page.getByRole('combobox',{name:'Clinic location',exact:true}).selectOption('kisumu');
 await page.getByRole('button',{name:'Continue to electrical setup',exact:true}).click();
}
async function save(page:Page){await page.getByRole('button',{name:'Review setup',exact:true}).click();await page.getByRole('checkbox',{name:'I have reviewed the inputs and model assumptions.',exact:true}).check();}
async function current(page:Page,request:import('@playwright/test').APIRequestContext){const id=await page.evaluate(()=>localStorage.getItem('lifeline.planning-session.v1'));return read(request,id!);}

test('first launch asks for the clinic without creating an example or calling planning tools',async({page})=>{
 let posts=0;page.on('request',r=>{if(r.method()==='POST')posts++;});await page.goto('/');
 await expect(page.getByRole('heading',{name:'First, where is your clinic?',exact:true})).toBeVisible();
 await expect(page.getByRole('textbox',{name:'Clinic name',exact:true})).toHaveValue('');
 await expect(page.getByRole('link',{name:'Skip to clinic setup',exact:true})).toHaveAttribute('href','#setup-name');
 await expect(page.getByRole('combobox',{name:'Clinic location',exact:true})).toHaveValue('');
 await expect(page.locator('input[type=date]')).toHaveCount(0);
 await expect(page.getByText('Battery may run too low',{exact:true})).toHaveCount(0);
 await expect(page.getByTestId('current-plan-summary')).toHaveCount(0);expect(posts).toBe(0);
 await page.screenshot({path:join(tmpdir(),'lifeline-setup-first-launch.png')});
});

test('demo autofill is explicit, editable and reviewed before creating a new clinic',async({page,request})=>{
 await page.goto('/');await locationStep(page);
 await expect(page.getByRole('spinbutton',{name:'Battery storage size (kWh)',exact:true})).toHaveValue('');
 const catalog=await (await request.get(apiBase.replace('/planning/sessions','/scenarios'))).json();const preset=catalog.scenarios.find((s:{id:string})=>s.id==='scheduling');
 await page.getByRole('button',{name:'Autofill demo setup',exact:true}).click();
 await expect(page.getByRole('spinbutton',{name:'Battery storage size (kWh)',exact:true})).toHaveValue(String(preset.defaults.battery_capacity_kwh));
 await expect(page.getByRole('spinbutton',{name:'Total solar panel rating (W)',exact:true})).toHaveValue(String(preset.defaults.pv_capacity_kw*1000));
 await page.getByRole('spinbutton',{name:'Battery storage size (kWh)',exact:true}).fill('16');
 expect(Number(await page.getByLabel('Expected battery charge at the start of the day (%)',{exact:true}).inputValue())).toBeCloseTo(preset.defaults.initial_battery_kwh/16*100,8);
 await page.screenshot({path:join(tmpdir(),'lifeline-setup-demo-autofill.png')});
 expect(await page.evaluate(()=>localStorage.getItem('lifeline.planning-session.v1'))).toBeNull();
 await save(page);await expect(page.getByText('Example equipment',{exact:true})).toBeVisible();await page.getByRole('button',{name:'Open the example clinic',exact:true}).click();
 await expect(page.getByRole('heading',{name:'How can LifeLine help today?',exact:true})).toBeVisible();
 const state=await current(page,request);expect(state.selected_clinic_id).toBe('demo-scheduling');expect(state.energy_settings.battery_capacity_kwh).toBe(16);expect(state.energy_settings.initial_battery_kwh).toBeCloseTo(preset.defaults.initial_battery_kwh,8);expect(state.equipment_inventory).toEqual(preset.equipment);expect(state.computed_plan).toBeNull();expect(state.plan_status).toBe('not_computed');
 await say(page,'We have a vaccination campaign tomorrow from 9 AM to 3 PM.');
 await expect(page.getByTestId('activity-proposal')).toBeVisible();expect((await current(page,request)).confirmed_activities).toHaveLength(0);
});

test('own setup contains no example equipment and starts by asking for real devices',async({page,request})=>{
 await page.goto('/');await locationStep(page);
 await page.getByLabel('Battery storage size (kWh)',{exact:true}).fill('8');await page.getByLabel('Total solar panel rating (W)',{exact:true}).fill('1500');await page.getByLabel('Expected battery charge at the start of the day (%)',{exact:true}).fill('60');await save(page);
 await page.getByRole('button',{name:'Save setup and add equipment',exact:true}).click();
 await expect(page.getByRole('heading',{name:'Which equipment does your clinic use?',exact:true})).toBeVisible();
 const state=await current(page,request);expect(state.equipment_inventory).toEqual([]);expect(state.energy_settings.initial_battery_kwh).toBeCloseTo(4.8,8);expect(state.computed_plan).toBeNull();
 await expect(page.getByText('Add essential equipment to assess power',{exact:true})).toBeVisible();
 await expect(page.getByRole('button',{name:'Plan our electricity',exact:true})).toHaveCount(0);
 await page.getByRole('button',{name:'Add clinic equipment',exact:true}).click();await expect(page.getByRole('dialog',{name:'Add clinic equipment',exact:true})).toBeVisible();
});

test('legacy saved clinic is offered explicitly and changing clinic preserves its state',async({page,request})=>{
 const state=await seed(request);await page.addInitScript(id=>localStorage.setItem('lifeline.planning-session.v1',id),state.id);await page.goto('/');
 await expect(page.getByRole('heading',{name:'First, where is your clinic?',exact:true})).toBeVisible();
 await page.getByRole('button',{name:`Resume ${state.clinic_name}`,exact:true}).click();await expect(page.getByRole('heading',{name:'How can LifeLine help today?',exact:true})).toBeVisible();
 await page.getByRole('button',{name:'Change clinic',exact:true}).click();await expect(page.getByRole('heading',{name:'First, where is your clinic?',exact:true})).toBeVisible();expect(await read(request,state.id)).toEqual(state);
 await page.getByRole('button',{name:`Resume ${state.clinic_name}`,exact:true}).click();await page.reload();await expect(page.getByRole('heading',{name:'How can LifeLine help today?',exact:true})).toBeVisible();
});

test('phone setup supports keyboard navigation and does not overflow',async({page})=>{
 await page.setViewportSize({width:375,height:812});await page.goto('/');await locationStep(page);
 const fill=page.getByRole('button',{name:'Autofill demo setup',exact:true});await fill.focus();await page.keyboard.press('Enter');await expect(page.getByText('Demo setup autofilled.',{exact:false})).toBeVisible();
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);await page.screenshot({path:join(tmpdir(),'lifeline-setup-phone.png')});
});

test('failed setup save preserves entered information for retry',async({page})=>{
 await page.route('**/api/planning/sessions',route=>route.request().method()==='POST'?route.fulfill({status:503,json:{error:{code:'SAVE_FAILED',message:'The local store could not save. Please retry.'}}}):route.continue());
 await page.goto('/');await locationStep(page);await page.getByRole('button',{name:'Autofill demo setup',exact:true}).click();await save(page);await page.getByRole('button',{name:'Open the example clinic',exact:true}).click();
 await expect(page.getByRole('alert')).toContainText('The local store could not save');await expect(page.getByRole('heading',{name:'Check your clinic setup',exact:true})).toBeVisible();expect(await page.evaluate(()=>localStorage.getItem('lifeline.planning-session.v1'))).toBeNull();
});
