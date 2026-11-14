import { test, expect } from "@playwright/test";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { open, seed, calculate, read, say, readyDraft, confirm, proposal, weatherFailure } from "./support/planning";
test.beforeEach(()=>weatherFailure(false));test.afterEach(()=>weatherFailure(false));

test("hello displays the model-authored reply without overlapping the author or resurfacing a plan",async({page,request})=>{
  const state=await calculate(request,await seed(request)); await open(page,state); await say(page,"Hello");
  const message=page.locator(".assistant-message").last(); await expect(message).toContainText("Hello! I’m here to help with your clinic’s day.");
  const author=await message.locator(".message-author").boundingBox(); const reply=await message.locator(".assistant-text").boundingBox(); expect(reply!.y).toBeGreaterThanOrEqual(author!.y+author!.height+5);
  await expect(page.getByTestId("current-plan-summary")).toHaveCount(0); await expect(page.getByRole("button",{name:"Explore plan",exact:true})).toHaveCount(0);
  expect((await read(request,state.id)).computed_plan!.generation).toBe(state.computed_plan!.generation);
  await page.screenshot({path:join(tmpdir(),"lifeline-chat-greeting.png")});
});

test("planning stays focused and alternatives appear only when the model explicitly presents a comparison",async({page,request})=>{
  await open(page,await seed(request)); let direct=0; page.on("request",r=>{if(r.url().endsWith("/recompute"))direct++;});
  await page.getByRole("button",{name:"Plan our electricity",exact:true}).click(); await expect(page.getByTestId("current-plan-summary")).toBeVisible();
  await expect(page.locator(".inline-alternative")).toHaveCount(0);expect(direct).toBe(0);
  await say(page,"Compare the calculated recovery alternatives.");await expect(page.locator(".inline-alternative")).toHaveCount(3); await expect(page.locator(".assistant-message").last()).toContainText("Here is my review for clinic staff");
  await expect(page.getByText("UNVERIFIED RAW MODEL TEXT",{exact:false})).toHaveCount(0);
});

test("no tool result is shown before the final model response",async({page,request})=>{
  const initial=await seed(request); await open(page,initial); const computed=await calculate(request,initial);
  await page.route("**/api/planning/sessions/*/agent/stream",async route=>{await new Promise(resolve=>setTimeout(resolve,700));await route.fulfill({json:{mode:"local_tool_agent",model:"llama3.1:8b",message:"Here is the plan I reviewed for your clinic. Please review the equipment times and the calculated alternatives below.",needs_clarification:false,clarification_fields:[],tool_calls:["recompute_clinic_plan"],presentation:{kind:"calculation",input_revision:computed.input_revision,generation:computed.computed_plan!.generation,option_ids:[],show_schedule:true},message_id:null,user_message_id:null,state:computed}});});
  await page.getByRole("textbox",{name:"Message LifeLine",exact:true}).fill("Plan our electricity"); await page.getByRole("button",{name:"Send message",exact:true}).click();
  await expect(page.locator(".live-activity")).toContainText("preparing your response"); await expect(page.getByTestId("current-plan-summary")).toHaveCount(0); await expect(page.getByRole("button",{name:"What LifeLine checked",exact:true})).toHaveCount(0);
  await expect(page.locator(".assistant-message")).toContainText("Here is the plan I reviewed"); await expect(page.getByTestId("current-plan-summary")).toBeVisible();
});

test("later calculations preserve earlier plans in labeled conversation history",async({page,request})=>{
  await open(page,await seed(request)); await say(page,"Plan the clinic electricity and compare recovery options."); const first=await page.getByTestId("current-plan-summary").getAttribute("data-generation");
  await say(page,"Compare plans with 50% less sunshine."); const second=await page.getByTestId("current-plan-summary").getAttribute("data-generation");expect(first).not.toBe(second);
  const history=page.getByRole("button",{name:/Earlier plan/}); await expect(history).toHaveCount(1); await history.click(); await expect(page.getByTestId("historical-plan")).toBeVisible(); await expect(page.getByTestId("historical-plan")).toHaveAttribute("data-generation",first!);
});

test("model failure offers retry and never substitutes deterministic planning replies",async({page,request})=>{
  const state=await seed(request); await open(page,state); let direct=0;page.on("request",r=>{if(r.url().endsWith("/recompute"))direct++;});
  await page.route("**/api/planning/sessions/*/agent/stream",route=>route.fulfill({json:{mode:"local_agent_unavailable",model:null,message:"Internal provider detail",needs_clarification:true,clarification_fields:[],tool_calls:[],state}}));
  await page.getByRole("button",{name:"Plan our electricity",exact:true}).click(); await expect(page.getByRole("button",{name:"Retry reply",exact:true})).toBeVisible(); await expect(page.getByTestId("current-plan-summary")).toHaveCount(0);expect(direct).toBe(0);
  await expect(page.getByText("Internal provider detail",{exact:true})).toHaveCount(0);
});

test("activity clarification and confirmation remain canonical while Llama explains the result",async({page,request})=>{
  const state=await seed(request);await open(page,state);await readyDraft(page);const draft=await read(request,state.id);expect(draft.confirmed_activities).toHaveLength(0);
  await say(page,"Actually start at 10 AM.");expect((await read(request,state.id)).active_proposal_id).toBe(draft.active_proposal_id);
  await confirm(page);const updated=await read(request,state.id);expect(updated.confirmed_activities).toHaveLength(1);expect(updated.confirmed_activities[0].details.start_hour).toBe(10);await expect(page.getByTestId("current-plan-summary")).toBeVisible();
});

test("draft rejection does not change confirmed electricity requirements",async({page,request})=>{
  const state=await seed(request);await open(page,state);await readyDraft(page);await proposal(page).getByRole("button",{name:"Cancel",exact:true}).click();await expect(proposal(page)).toHaveCount(0);const next=await read(request,state.id);expect(next.confirmed_activities).toHaveLength(0);expect(next.proposals[0].status).toBe("rejected");
});

test("a selected alternative can be explained in chat without resetting its energy calculation",async({page,request})=>{
  const state=await calculate(request,await seed(request));await open(page,state);await page.getByRole('link',{name:'Clinic Overview',exact:true}).click();
  await page.getByRole('button',{name:/All calculated plans/}).click();
  const chosen=state.computed_plan!.recovery!.options.filter(o=>o.kind==='output').at(-1)!;
  await page.locator(`input[name="clinic-plan"][value="${chosen.id}"]`).click();await expect(page.locator(`input[name="clinic-plan"][value="${chosen.id}"]`)).toBeChecked();
  await page.getByRole('button',{name:'Ask LifeLine about this plan',exact:true}).click();await expect(page.getByTestId('current-plan-summary')).toHaveAttribute('data-selection-id',chosen.id);await expect(page.locator('.inline-alternative')).toHaveCount(0);
  const after=await read(request,state.id);expect(after.selected_recovery_intervention_id).toBe(chosen.id);expect(after.computed_plan!.generation).toBe(state.computed_plan!.generation);
});

test("long model replies keep author text separate on a phone",async({page,request})=>{
  await page.setViewportSize({width:375,height:812});const state=await seed(request);await open(page,state);
  const message='Let’s review what you need for your clinic day. '.repeat(12);
  await page.route('**/api/planning/sessions/*/agent/stream',route=>route.fulfill({json:{mode:'local_tool_agent',model:'llama3.1:8b',message,needs_clarification:false,clarification_fields:[],tool_calls:['conversational_reply'],state}}));
  await say(page,'Hello');const answer=page.locator('.assistant-message').last();await expect(answer.locator('.assistant-text')).toHaveText(message.trim());
  const author=await answer.locator('.message-author').boundingBox();const prose=await answer.locator('.assistant-text').boundingBox();expect(prose!.y).toBeGreaterThan(author!.y+author!.height);expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
});

test('ordinary brainstorming does not calculate or display plans and chat restores after reload',async({page,request})=>{
  const state=await calculate(request,await seed(request));await open(page,state);await say(page,'Brainstorm ideas for the clinic power setup.');
  await expect(page.locator('.assistant-message')).toContainText('have not been evaluated yet');await expect(page.getByTestId('current-plan-summary')).toHaveCount(0);
  const after=await read(request,state.id);expect(after.revision).toBe(state.revision);expect(after.input_revision).toBe(state.input_revision);expect(after.computed_plan!.generation).toBe(state.computed_plan!.generation);
  await page.reload();await expect(page.locator('.assistant-message')).toContainText('have not been evaluated yet');await expect(page.locator('.user-message')).toHaveCount(1);await expect(page.locator('.assistant-message')).toHaveCount(1);
});

test('Llama can stage and clarify power settings while current readings remain distinct from midnight assumptions',async({page,request})=>{
  const state=await seed(request);await open(page,state);await say(page,'Set battery capacity to 8 kWh and the starting charge to 75% and the current reading is 50%.');
  const proposal=page.getByTestId('energy-proposal');await expect(proposal).toContainText('6.000 kWh stored (75.0%)');await expect(proposal).toContainText('New current reading: 4.000 kWh');
  let after=await read(request,state.id);expect(after.energy_settings.battery_capacity_kwh).toBe(4);expect(after.current_battery_reading).toBeNull();
  await say(page,'Set the starting charge to 50%.');await expect(proposal).toContainText('4.000 kWh stored (50.0%)');after=await read(request,state.id);expect(after.energy_proposals).toHaveLength(1);
  await proposal.getByRole('button',{name:'Confirm power settings',exact:true}).click();await expect(proposal).toHaveCount(0);after=await read(request,state.id);expect(after.energy_settings.initial_battery_kwh).toBe(4);expect(after.current_battery_reading!.energy_kwh).toBe(4);
});

test('a read-only conversation preserves the battery timeline and selected comparison',async({page,request})=>{
  const state=await calculate(request,await seed(request));await open(page,state);await page.getByRole('link',{name:'Clinic Overview',exact:true}).click();const slider=page.getByRole('slider',{name:'Simulation time',exact:true});await slider.focus();await slider.press('Home');for(let i=0;i<6;i++)await slider.press('ArrowRight');await expect(slider).toHaveAttribute('aria-valuenow','6');
  await page.getByRole('link',{name:'AI Assistant',exact:true}).click();await say(page,'Hello');await page.getByRole('link',{name:'Clinic Overview',exact:true}).click();await expect(slider).toHaveAttribute('aria-valuenow','6');expect((await read(request,state.id)).computed_plan!.generation).toBe(state.computed_plan!.generation);
});
