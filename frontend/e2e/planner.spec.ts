import { test, expect } from "@playwright/test";
import { join } from "node:path";
import { tmpdir } from "node:os";
import { open, seed, read, calculate, say, overview, assistant, weatherFailure } from "./support/planning";
test.beforeEach(() => weatherFailure(false)); test.afterEach(() => weatherFailure(false));

test("the overview puts the decision and next action before energy evidence",async({page,request})=>{
 await page.setViewportSize({width:1280,height:900});await open(page,await calculate(request,await seed(request)));await overview(page).click();
 const outlook=page.getByRole('region',{name:'Will we have enough electricity?',exact:true});const plans=page.getByRole('region',{name:'Plans',exact:true});const energy=page.getByRole('region',{name:'Energy through the day',exact:true});
 for(const element of [outlook,plans,energy])await expect(element).toBeVisible();
 const boxes=await Promise.all([outlook,plans,energy].map(e=>e.boundingBox()));expect(boxes[0]!.y).toBeLessThan(boxes[1]!.y);expect(boxes[1]!.y).toBeLessThan(boxes[2]!.y);
 const chart=await page.locator('.energy-chart-column').boundingBox(),battery=await page.locator('.energy-battery-side').boundingBox();expect(battery!.x).toBeGreaterThan(chart!.x);expect(Math.abs(chart!.y-battery!.y)).toBeLessThan(2);
 await expect(page.getByRole('navigation',{name:'Primary navigation'}).getByRole('link')).toHaveCount(2);await expect(page.getByRole('button',{name:'Add activity',exact:true})).toBeVisible();await expect(page.locator('vite-error-overlay')).toHaveCount(0);
 await page.screenshot({path:join(tmpdir(),'lifeline-decision-first-overview.png')});
});

test("page navigation preserves the conversation and unsent message", async ({ page, request }) => {
  await open(page, await seed(request)); await say(page,"Hello");
  const textbox=page.getByRole("textbox",{name:"Message LifeLine",exact:true}); await textbox.fill("I want to change the clinic work");
  await overview(page).click(); await expect(overview(page)).toHaveAttribute("aria-current","page");
  await expect(page.getByRole("navigation",{name:"Primary navigation"}).getByRole("link")).toHaveCount(2);
  await assistant(page).click(); await expect(assistant(page)).toHaveAttribute("aria-current","page");
  await expect(textbox).toHaveValue("I want to change the clinic work"); await expect(page.locator(".assistant-message")).toContainText("Hello!");
});

test("equipment can be entered and reviewed in Overview without requiring the LLM", async ({ page, request }) => {
  const state=await seed(request); await open(page,state); await overview(page).click(); await expect(overview(page)).toHaveAttribute("aria-current","page");
  await page.getByRole("button",{name:"Add equipment",exact:true}).click(); const dialog=page.getByRole("dialog",{name:"Add clinic equipment",exact:true});
  await dialog.getByRole("textbox",{name:"Equipment name",exact:true}).fill("Campaign light"); await dialog.getByRole("spinbutton",{name:"Power rating on the label (W)",exact:true}).fill("200");
  await dialog.getByRole("combobox",{name:"Does it need protected power?",exact:true}).selectOption("critical"); await dialog.getByRole("combobox",{name:"Start time",exact:true}).selectOption("10"); await dialog.getByRole("combobox",{name:"Finish time",exact:true}).selectOption("12");
  expect((await read(request,state.id)).equipment_inventory).toHaveLength(2);
  let agentCalls=0;page.on('request',r=>{if(r.url().endsWith('/agent'))agentCalls++;});await dialog.getByRole("button",{name:"Review equipment",exact:true}).click();await expect(dialog).not.toBeVisible();expect(agentCalls).toBe(0);
  const draft=page.locator('[data-testid="activity-proposal"]:visible'); await expect(draft).toContainText("Campaign light"); await expect(draft).toContainText("200 W");
  expect((await read(request,state.id)).equipment_inventory).toHaveLength(2);
  await draft.getByRole("button",{name:"Confirm",exact:true}).click(); await expect(page.locator("#chat-input")).toBeEditable();
  const confirmed=await read(request,state.id); expect(confirmed.equipment_inventory).toHaveLength(3); expect(confirmed.computed_plan!.simulation.optimized.metrics.critical_requested_kwh).toBeCloseTo(2.8,8);
});

test("mobile panels stack and equipment form supports keyboard and unknown ratings", async ({ page, request }) => {
  await page.setViewportSize({width:375,height:812}); await open(page,await seed(request)); await overview(page).focus(); await page.keyboard.press("Enter"); await expect(overview(page)).toHaveAttribute("aria-current","page");
  const panels=await page.locator('.overview-context-panels > section').evaluateAll(els=>els.map(el=>{const r=el.getBoundingClientRect();return {x:r.x,y:r.y,width:r.width};}));expect(panels[1].y).toBeGreaterThan(panels[0].y);expect(Math.abs(panels[0].x-panels[1].x)).toBeLessThan(2);
  await page.getByRole("button",{name:"Add equipment",exact:true}).focus(); await page.keyboard.press("Enter"); const dialog=page.getByRole("dialog",{name:"Add clinic equipment",exact:true});
  await expect(dialog.getByRole("textbox",{name:"Equipment name",exact:true})).toBeFocused(); await page.keyboard.press("Escape"); await expect(dialog).toBeHidden(); await expect(page.getByRole("button",{name:"Add equipment",exact:true})).toBeFocused();
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
});

test("equipment is visible, scrollable and opens details without changing the plan",async({page,request})=>{
  const base=(await import('./support/planning')).initial();
  const state=await seed(request,{clinic:{...base.clinic,equipment:[...base.clinic.equipment!,...Array.from({length:18},(_,i)=>({id:`light-${i}`,name:`Clinic light ${i}`,category:'critical' as const,power_kw:.01,required_hours:[9,10]}))]}});
  await open(page,state);await overview(page).click();await expect(overview(page)).toHaveAttribute('aria-current','page');
  const panel=page.getByRole('region',{name:'Activities & Equipment',exact:true});await expect(panel.locator('.equipment-item')).toHaveCount(20);
  const scroll=panel.locator('.overview-square-body');expect(await scroll.evaluate(el=>el.scrollHeight>el.clientHeight)).toBe(true);
  const equipment=panel.locator('.equipment-item').last();await equipment.locator('summary').focus();await page.keyboard.press('Enter');await expect(equipment).toHaveAttribute('open','');await expect(equipment).toContainText('09:00–11:00');await expect(equipment.getByRole('button',{name:'Edit in chat',exact:true})).toBeVisible();
  expect((await read(request,state.id)).revision).toBe(state.revision);expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
});

test("the in-app preview stacks chart and battery without horizontal overflow",async({page,request})=>{
 await page.setViewportSize({width:631,height:955});await open(page,await calculate(request,await seed(request)));await overview(page).click();
 await expect(page.locator('.energy-chart-column')).toBeVisible();
 const chart=await page.locator('.energy-chart-column').boundingBox(),battery=await page.locator('.energy-battery-side').boundingBox();expect(battery!.y).toBeGreaterThan(chart!.y);
 const slider=page.getByRole('slider',{name:'Simulation time',exact:true});await slider.focus();await slider.press('End');await expect(page.getByLabel('Selected simulation time',{exact:true})).toHaveText('24:00');
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);await page.screenshot({path:join(tmpdir(),'lifeline-preview-energy.png')});
});

test("flexible equipment asks for device hours and the backend derives its energy after review",async({page,request})=>{
  const state=await seed(request);await open(page,state);await overview(page).click();await page.getByRole('button',{name:'Add equipment',exact:true}).click();const dialog=page.getByRole('dialog',{name:'Add clinic equipment',exact:true});
  await dialog.getByRole('textbox',{name:'Equipment name',exact:true}).fill('Portable pump');await dialog.getByRole('spinbutton',{name:'Power rating on the label (W)',exact:true}).fill('500');
  await dialog.getByRole('combobox',{name:'Does it need protected power?',exact:true}).selectOption('flexible');await dialog.getByRole('combobox',{name:'Start time',exact:true}).selectOption('10');await dialog.getByRole('combobox',{name:'Finish time',exact:true}).selectOption('14');
  await dialog.getByRole('spinbutton',{name:'How many hours must this device run?',exact:true}).fill('2');await dialog.getByRole('combobox',{name:'Can the work pause and resume?',exact:true}).selectOption('yes');
  await dialog.getByRole('button',{name:'Review equipment',exact:true}).click();const draft=page.locator('[data-testid="activity-proposal"]:visible');await expect(draft.getByRole('button',{name:'Confirm',exact:true})).toBeEnabled();
  expect((await read(request,state.id)).equipment_inventory).toHaveLength(2);await draft.getByRole('button',{name:'Confirm',exact:true}).click();await expect(page.locator('#chat-input')).toBeEditable();
  const next=await read(request,state.id);const equipment=next.equipment_inventory.find(e=>e.name==='Portable pump')!;expect(equipment.category).toBe('flexible');if(equipment.category==='flexible'){expect(equipment.required_energy_kwh).toBe(1);expect(equipment.allowed_hours).toEqual([10,11,12,13]);}
});
