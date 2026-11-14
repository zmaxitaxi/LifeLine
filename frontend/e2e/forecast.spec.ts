import { test, expect } from "@playwright/test";
import { join } from "node:path";
import { tmpdir } from "node:os";
import { apiBase, open, seed, calculate, read, say, overview, weatherFailure } from "./support/planning";
test.beforeEach(()=>weatherFailure(false));test.afterEach(()=>weatherFailure(false));
async function showOverview(page: import('@playwright/test').Page){await overview(page).click();await expect(overview(page)).toHaveAttribute('aria-current','page');}

test("weather shows actual current conditions and seven daily forecasts",async({page,request})=>{
  await open(page,await seed(request));await showOverview(page);const panel=page.getByRole('region',{name:'Weather',exact:true});
  await expect(panel.locator('.current-weather')).toContainText('19°');await expect(panel.locator('.current-weather')).toContainText('Partly cloudy');await expect(panel.locator('.weather-day')).toHaveCount(7);
  await panel.getByRole('button',{name:'Weather details',exact:true}).click();await expect(panel).toContainText('Open-Meteo');await expect(panel).toContainText('2026-11-19');
});

test("missing temperatures remain unavailable rather than becoming zero",async({page,request})=>{
  await page.route('**/api/weather/outlook?**',async route=>{const response=await route.fetch();const data=await response.json();data.current.temperature_c=null;data.days[0].temperature_max_c=null;await route.fulfill({json:data});});
  await open(page,await seed(request));await showOverview(page);await expect(page.locator('.current-weather strong')).toContainText('—');await expect(page.locator('.weather-day').first()).toContainText('—');
});

test("weather outages are brief and retry restores the real weekly feed",async({page,request})=>{
  const state=await seed(request);weatherFailure(true);await open(page,state);await showOverview(page);const panel=page.getByRole('region',{name:'Weather',exact:true});
  await expect(panel).toContainText('Weather is unavailable.');await expect(panel.locator('.weather-day')).toHaveCount(0);await expect(panel.getByText('Injected browser-test weather outage',{exact:false})).not.toBeVisible();
  weatherFailure(false);await panel.getByRole('button',{name:'Retry weather',exact:true}).click();await expect(panel.locator('.weather-day')).toHaveCount(7);
});

test("selecting a calculated plan updates both energy and changed assumptions without new simulation",async({page,request})=>{
  const state=await calculate(request,await seed(request));await open(page,state);await showOverview(page);
  await expect(page.locator('input[name="clinic-plan"][value="existing"]')).toBeChecked();await expect(page.getByTestId('optimized-battery')).toHaveCount(0);
  const solar=state.computed_plan!.recovery!.options.find(o=>o.kind==='solar')!;await page.locator(`input[name="clinic-plan"][value="${solar.id}"]`).click();await expect(page.getByTestId('optimized-battery')).toHaveAttribute('data-energy-kwh',String(solar.plan.hourly[0].soc_start_kwh));
  const next=await read(request,state.id);expect(next.selected_recovery_intervention_id).toBe(solar.id);expect(next.computed_plan!.generation).toBe(state.computed_plan!.generation);
  await expect(page.getByRole('region',{name:'Plans',exact:true})).toContainText(`${solar.infrastructure_changes[0].after.toFixed(3)} kW`);
});

test("the selected battery scenario uses its own capacity at all hourly boundaries",async({page,request})=>{
  const state=await calculate(request,await seed(request));await open(page,state);await showOverview(page);const option=state.computed_plan!.recovery!.options.find(o=>o.kind==='battery')!;
  await page.locator(`input[name="clinic-plan"][value="${option.id}"]`).click();
  const slider=page.getByRole('slider',{name:'Simulation time',exact:true});await slider.focus();await slider.press('Home');
  for(let hour=0;hour<=24;hour++){
    if(hour)await slider.press('ArrowRight');await expect(page.getByLabel('Selected simulation time',{exact:true})).toHaveText(`${String(hour).padStart(2,'0')}:00`);
    for(const [id,plan,config] of [['existing-battery',state.computed_plan!.simulation.baseline,state.computed_plan!.simulation.effective_config],['optimized-battery',option.plan,option.config]] as const){
      const element=page.getByTestId(id);const energy=hour===24?plan.hourly[23].soc_end_kwh:plan.hourly[hour].soc_start_kwh;
      expect(Number(await element.getAttribute('data-energy-kwh'))).toBeCloseTo(energy,8);expect(Number(await element.getAttribute('data-percentage'))).toBeCloseTo(energy/config.battery_capacity_kwh*100,8);
      expect(await element.locator('.battery-warning').filter({hasText:'Below reserve'}).count()).toBe(energy<config.reserve_kwh-1e-6?1:0);
    }
  }
  await slider.press('Home');expect(await page.getByTestId('existing-battery').getAttribute('data-energy-kwh')).toBe(await page.getByTestId('optimized-battery').getAttribute('data-energy-kwh'));
  await page.getByRole('button',{name:'Play battery playback',exact:true}).click();await expect(page.getByLabel('Selected simulation time',{exact:true})).not.toHaveText('00:00');await page.getByRole('button',{name:'Pause battery playback',exact:true}).click();
  const paused=await slider.getAttribute('aria-valuenow');await page.waitForTimeout(350);await expect(slider).toHaveAttribute('aria-valuenow',paused!);
  const other=state.computed_plan!.recovery!.options.find(o=>o.kind==='solar')!;await page.locator(`input[name="clinic-plan"][value="${other.id}"]`).click();await expect(page.getByLabel('Selected simulation time',{exact:true})).toHaveText('00:00');
});

test("a failed new calculation clears old plan evidence and retry goes through the LLM",async({page,request})=>{
  const state=await seed(request);await open(page,state);await say(page,'Calculate recovery plans for the clinic.');await expect(page.getByTestId('current-plan-summary')).toBeVisible();
  weatherFailure(true);await say(page,'Calculate recovery plans again.');await expect(page.getByTestId('current-plan-summary')).toHaveCount(0);expect((await read(request,state.id)).computed_plan).toBeNull();
  weatherFailure(false);await page.getByRole('button',{name:'Retry with LifeLine',exact:true}).click();await expect(page.getByTestId('current-plan-summary')).toBeVisible();
});

test("empty energy is distinct from reserve risk and reduced motion disables fill transitions",async({page,request})=>{
  const state=await calculate(request,await seed(request,{midnight_battery_kwh:0}));expect(state.computed_plan!.simulation.baseline.metrics.critical_unserved_kwh).toBeGreaterThan(0);await page.emulateMedia({reducedMotion:'reduce'});await open(page,state);await showOverview(page);
  await expect(page.getByRole('region',{name:'Plans',exact:true})).toContainText('Essential equipment may lose power');await expect(page.getByTestId('existing-battery')).toContainText('Essential equipment is short');
  expect((await page.locator('.battery-fill').evaluateAll(els=>els.map(el=>getComputedStyle(el).transitionDuration))).every(value=>value==='0s')).toBe(true);
});

test("mobile overview stays within the viewport and exposes the exact timeline accessibly",async({page,request})=>{
  await page.setViewportSize({width:375,height:812});await open(page,await calculate(request,await seed(request)));await showOverview(page);
  const energy=page.getByRole('region',{name:'Battery & Energy',exact:true});await energy.focus();
  const slider=page.getByRole('slider',{name:'Simulation time',exact:true});await slider.focus();await slider.press('End');await expect(page.getByLabel('Selected simulation time',{exact:true})).toHaveText('24:00');
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);await energy.evaluate(el=>{const root=el.closest('.overview-page')!;root.scrollTop+=el.getBoundingClientRect().top-root.getBoundingClientRect().top;});await page.screenshot({path:join(tmpdir(),'lifeline-square-mobile.png')});
});

test("weather date and hour selections show actual computed solar and do not invent another day's plan",async({page,request})=>{
  const state=await calculate(request,await seed(request));await open(page,state);await showOverview(page);
  const weather=page.getByRole('region',{name:'Weather',exact:true});await expect(weather.getByTestId('weather-energy')).toBeVisible();
  for(const hour of [0,9,12,18,23]) {
    await weather.getByRole('button',{name:`${String(hour).padStart(2,'0')}:00`,exact:true}).click();
    await expect(weather.getByTestId('weather-solar')).toHaveText(`${state.computed_plan!.simulation.baseline.hourly[hour].pv_kwh.toFixed(3)} kWh`);
  }
  const solar=state.computed_plan!.recovery!.options.find(o=>o.kind==='solar')!;
  await page.locator(`input[name="clinic-plan"][value="${solar.id}"]`).click();
  await weather.getByRole('button',{name:'12:00',exact:true}).click();await expect(weather.getByTestId('weather-solar')).toHaveText(`${state.computed_plan!.simulation.baseline.hourly[12].pv_kwh.toFixed(3)} kWh → ${solar.plan.hourly[12].pv_kwh.toFixed(3)} kWh selected`);
  await weather.locator('.weather-day').last().click();await expect(weather).toContainText('No clinic energy calculation for this date.');await expect(weather.getByTestId('weather-solar')).toHaveCount(0);
  const after=await read(request,state.id);expect(after.computed_plan!.generation).toBe(state.computed_plan!.generation);expect(after.planning_date).toBe(state.planning_date);
});
