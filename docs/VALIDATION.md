# Validation and project history

These results measure simulation and integration behavior. The sample clinic uses illustrative equipment and energy inputs.

## Computed scheduling results

The current **sample-weather presentation** uses Kisumu, 1.5 kW PV, 8 kWh storage, 6 kWh assumed midnight starting energy and a 4.8 kWh reserve target. Every method serves all 5.34 kWh of essential demand and completes all 2.100 kWh of flexible work under identical conditions.

| Stored energy at midnight | Existing | Sunshine-first | MILP |
|---|---:|---:|---:|
| Sample-weather presentation | 4.585 kWh | 5.682 kWh | 5.700 kWh |

MILP preserves **1.115 kWh** at midnight relative to the existing schedule, raises the daily minimum by **0.368 kWh**, and removes the modeled reserve breach. The heuristic nearly matches MILP. With 50% less sunshine, the existing schedule drops to an approximately **1.961 kWh** minimum while still serving essential demand. A tested 3.5 kW solar alternative and optimized schedule raise the minimum to approximately **4.975 kWh**, with all original work complete. [Sample proof](evidence/demo-weather-scheduling-proof.json), [rehearsed workflow](DEMO.md)

Other reproducible cases demonstrate different effects:

| Case | Result under the stated assumptions |
|---|---|
| Original synthetic `scheduling` preset | Both sunshine-first and MILP complete the same 2.100 kWh of flexible work as the existing schedule. They preserve 2.211 kWh at midnight, improve the daily minimum by 0.368 kWh and reduce conversion loss by 0.111 kWh. |
| Competing windows, historical Kisumu radiation | With 0.4 kW battery output and a restricted transfer window, MILP completes 3.800 kWh, versus 3.470 kWh for sunshine-first and 2.770 kWh for the existing schedule. All maintain essential coverage and the same 5.774 kWh minimum. Reversing the greedy task order closes the completion gap. |
| Storm and High Demand | Storm still has reserve risk. High Demand has 1.320 kWh of modeled essential shortfall at the original output limit. Battery improvements that come with deferred work are unequal-work comparisons. |
| Historical recovery sensitivity | A hypothetical change from 4 to 5 kW of battery output removes the 1.320 kWh essential shortfall and serves all 2.100 kWh of flexible work. More storage alone leaves the output bottleneck. |

Recompute the preset benchmarks with `python scripts/benchmark.py` and the historical recovery comparison with `python scripts/run_recovery_demo.py`. In **Detailed mode**, load the competing-window example to calculate its schedules from the checked-in inputs. [Full benchmark metrics](evidence/final-benchmark.json), [competing-window allocations](evidence/competing-windows.json), [historical recovery](evidence/recovery-historical-demo.json)

## Assistant and browser verification

- The verified integration ran **525 backend and 56 browser checks**. The browser suite uses the actual API, simulator and MILP with injected test weather and model transport. It exercises the reviewed workflow, keyboard and mobile interactions, and failure handling. [CI run](https://github.com/zmaxitaxi/LifeLine/actions/runs/43576764265)
- Real Haiku passed **6 of 7** targeted checks in the final batch. A source-verification correction made the recovery check pass in a targeted rerun. A separate genuine browser run passed greeting and assessment in 2.272s and 6.685s using labeled sample weather. Timing is an observation for those runs. [Seven-case batch](evidence/pipeline-claude-final.json), [recovery rerun](evidence/pipeline-claude-shared-outcome-check.json), [browser evidence](evidence/claude-genuine-browser.json)
- Genuine presentation rehearsals exercised vaccination drafting and confirmation, cloudy recovery, tested-plan selection, energy-setting confirmation, exact equipment-slot explanation, reload and backend restart with isolated persistent state. The three-prompt path took 21.0s and the five-prompt path 30.1s in automation, excluding narration. The walkthrough includes recovery steps for model or network failure. [Exact prompts and replay commands](DEMO.md)
- The earlier **87.5/100 local Llama** evaluation, up from 70.0/100, applies to the previous tool set and its recorded fixtures. Multi-turn continuity and impossible-request coverage were partial results. Wajo was explored through authenticated discovery and a no-action greeting. It is outside the current workflow. [Local evaluation report](https://github.com/zmaxitaxi/LifeLine/blob/7605ce892450dc34c8fc807b80a77a1de57ae6a4/LLM_EVALUATION.md), [raw local evaluation](evidence/LLM_EVALUATION_RESULTS.json), [Wajo evidence](evidence/wajo-investigation.json)

To run a genuine provider batch locally, configure the server's Anthropic key and run the command below. It makes billed requests on isolated inputs. Fixture tests do not require live provider access.

```bash
.venv/bin/python scripts/benchmark_session_pipeline.py --provider claude \
  --cases conversation,assessment,vaccination,proposal,recovery,followup,history \
  --output /tmp/lifeline-haiku-check.json
```

Treat first public progress, completed model content and browser response time as different measurements. Exact tool trajectories, provider failures, historical releases and recorded weather replays are preserved under [evidence](evidence).

## Practical limits

The [WHO-led Energizing Health report](https://www.who.int/publications/i/item/9789240066960/) describes the need for facility-level demand assessment and reliable electricity service. [SEforALL/CLASP appliance research](https://www.seforall.org/publications/medical-appliances-for-resource-constrained-settings) provides published context and ratings. LifeLine has no practitioner interviews, clinic pilot, calibrated local load trace, measured energy savings or health-outcome results. Flexible workflow and operator usefulness remain hypotheses.

A facility energy technician and manager would need to verify usable battery capacity, installation and output limits, actual equipment demand, essential hours and genuinely interruptible work. Compare shadow recommendations with permitted generation, load and battery logs over multiple weather conditions before considering operational use. This single-day simulator does not address power quality, starting surges, appliance-cycle continuity, refrigeration temperatures or equipment control.

## Project and submission record

The supplied hackathon slide emphasized practical human-centered AI for social good. LifeLine addresses the SDG direction with energy-planning assistance. The slide did not establish official scoring weights, eligibility, submission format, hosting, AI attribution or registration requirements. The November 14, 2026 deadline was supplied by the team. This repository records the technical deliverables and rehearsal, with no submission confirmation or hosted application claimed.

The original briefs, teammate handoffs, submission draft, research and incident investigations are available at their previous paths in Git history. [Repository snapshot](https://github.com/zmaxitaxi/LifeLine/tree/7605ce892450dc34c8fc807b80a77a1de57ae6a4), [original source briefs](https://github.com/zmaxitaxi/LifeLine/tree/7605ce892450dc34c8fc807b80a77a1de57ae6a4/docs/source), [submission draft](https://github.com/zmaxitaxi/LifeLine/blob/7605ce892450dc34c8fc807b80a77a1de57ae6a4/SUBMISSION.md)
