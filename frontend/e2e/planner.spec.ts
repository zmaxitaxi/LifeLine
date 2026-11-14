import { test, expect } from "@playwright/test";
import { join } from "node:path";
import { tmpdir } from "node:os";
import { open, seed, read, calculate, say, overview, assistant, weatherFailure } from "./support/planning";
test.beforeEach(() => weatherFailure(false)); test.afterEach(() => weatherFailure(false));

test("the overview fills the workspace with four equal desktop quadrants", async ({ page, request }) => {
  const errors: string[] = [];page.on('pageerror', error => errors.push(error.message));
  await page.setViewportSize({ width:1280,height:900 });
  await open(page, await calculate(request, await seed(request))); await overview(page).click(); await expect(overview(page)).toHaveAttribute("aria-current","page");
  const panels = page.locator(".overview-grid > .overview-square"); await expect(panels).toHaveCount(4);
  const boxes = await panels.evaluateAll(elements => elements.map(e => { const r=e.getBoundingClientRect();return {x:r.x,y:r.y,width:r.width,height:r.height}; }));
  for (const box of boxes) {expect(Math.abs(box.width-boxes[0].width)).toBeLessThan(2);expect(Math.abs(box.height-boxes[0].height)).toBeLessThan(2);}
  const grid=await page.locator('.overview-grid').boundingBox();expect(grid!.width).toBeGreaterThan(1180);expect(boxes[3].y+boxes[3].height).toBeGreaterThan(860);expect(boxes[3].y+boxes[3].height).toBeLessThan(900);
  await expect(page.getByRole('slider',{name:'Simulation time',exact:true})).toBeVisible();await expect(page.getByRole('radio',{name:'Current plan',exact:true})).toBeVisible();
  expect(Math.abs(boxes[0].y-boxes[1].y)).toBeLessThan(2); expect(boxes[2].y).toBeGreaterThan(boxes[0].y); expect(Math.abs(boxes[2].y-boxes[3].y)).toBeLessThan(2);
  for (const name of ["Activities & Equipment","Weather","Battery & Energy","Plans"]) await expect(page.getByRole("heading",{name,exact:true})).toBeVisible();
  await expect(page.getByRole("button",{name:"Add equipment",exact:true})).toBeVisible();
  await expect(page).toHaveTitle('LifeLine — Clinic energy planner');await expect(page.locator('vite-error-overlay')).toHaveCount(0);expect(errors).toEqual([]);
  await page.screenshot({path:join(tmpdir(),"lifeline-four-square-overview.png")});
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
  const boxes=await page.locator(".overview-square").evaluateAll(elements=>elements.map(e=>{const r=e.getBoundingClientRect();return {x:r.x,y:r.y,width:r.width,height:r.height};}));
  for (let index=0;index<boxes.length;index++){expect(boxes[index].height).toBe(520);if(index)expect(boxes[index].y).toBeGreaterThan(boxes[index-1].y);}
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

test("the in-app preview width keeps all four panels in view",async({page,request})=>{
  await page.setViewportSize({width:631,height:955});await open(page,await calculate(request,await seed(request)));await overview(page).click();await expect(overview(page)).toHaveAttribute('aria-current','page');
  const boxes=await page.locator('.overview-square').evaluateAll(els=>els.map(el=>{const r=el.getBoundingClientRect();return {x:r.x,y:r.y,width:r.width,height:r.height};}));
  expect(boxes[1].x).toBeGreaterThan(boxes[0].x);expect(boxes[2].y).toBeGreaterThan(boxes[0].y);expect(boxes[3].y+boxes[3].height).toBeLessThan(955);
  const energy=page.getByRole('region',{name:'Battery & Energy',exact:true});const play=await energy.getByRole('button',{name:'Play battery playback',exact:true}).boundingBox();expect(play!.y+play!.height).toBeLessThan(boxes[2].y+boxes[2].height);
  const ticks=await page.locator('.battery-time-labels span:visible').evaluateAll(els=>els.map(el=>{const r=el.getBoundingClientRect();return {left:r.left,right:r.right};}));for(let i=1;i<ticks.length;i++)expect(ticks[i].left).toBeGreaterThanOrEqual(ticks[i-1].right-1);
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);await page.screenshot({path:join(tmpdir(),'lifeline-preview-four-panels.png')});
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
