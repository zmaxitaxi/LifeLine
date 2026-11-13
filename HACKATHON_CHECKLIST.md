# Hackathon submission readiness

## Evidence supplied by the user

The supplied “GM#10 OP HACKATHON!” slide describes practical, human-centered AI agents and LLM-powered tools for social good, and lists accessibility, Berkeley-region sustainability/climate work, and addressing an SDG among its directions. LifeLine targets the SDG direction through energy reliability planning relevant to SDG 7.1 and SDG 3.8. It does not claim a Berkeley deployment or a disability-specific user study.

**Current AI:** LifeLine now uses local Llama 3.1 8B/Ollama to choose validated planning tools. The numerical model and explanation renderer remain deterministic; fallback modes are labeled. Wajo authenticated connectivity was tested separately and is not a dependency. This supplies genuine LLM integration, but the slide still does not establish full eligibility or judging weights; no organizer contact has been made.

The slide is not a complete judging rubric: scoring weights, required submission format, hosted-demo/video requirements, team-size limits, AI-tool disclosure, and deadline/timezone rules are not shown. Saturday November 14, 2026 at 11:59 PM Pacific remains the user-supplied planning deadline, not independently verified from this slide.

## Prepared

- [x] Working configurable application and three-way computed comparisons.
- [x] Shortage diagnosis, Capacity Explorer, public historical irradiance, and explicit provenance.
- [x] Source code, setup instructions, research, data-source notes, product-validation limits, benchmark, and demo script.
- [x] Backend, build, mobile/desktop, failure-recovery, and offline browser checks executed; see the verification documents for actual results.
- [x] UI uses shadcn/ui + Tailwind, Recharts, and Lucide while preserving the working workflow.
- [x] Live Open-Meteo forecast retrieval, timezone/unit conversion, same-input lower-sunshine comparisons, explicit cache/failure behavior, and validated agent-callable tools. See [live weather](LIVE_WEATHER.md).
- [x] Actual local LLM tool selection tested on five targeted questions; strict boundary, missing-input clarification, fixed consecutive-load proposals and capacity search implemented. Guided/offline fallbacks remain explicitly non-LLM.
- [x] Wajo authentication, schemas, read-only listing and isolated no-action greeting verified. Local model selected by the user; no Anthropic key needed.
- [x] Stronger competing-window example and honest comparison with greedy task-order reversal documented.

## Before submission

On November 13, 2026, a public search found the [Open Project club site](https://openprojectberkeley.com/) but no official rules or submission form for this specific event. The team still needs the organizer's instructions to verify the items below.

- [ ] Confirm official eligibility/rubric, especially any mandatory LLM requirement.
- [ ] Reverify fresh forecast retrieval: the latest API connection failed. Earlier actual retrieval and a labeled local-LLM/recorded-weather replay are evidence, not current live data.
- [ ] Verify exact deadline/timezone, team registration, submission form, and required links.
- [ ] Rehearse the two-minute script against the final release; keep the heuristic tie and unavoidable-shortage case visible.
- [ ] If requested by organizers, record a short video of the working release and label it as a recording. No demo video is claimed to have been produced.
- [ ] Confirm whether a public hosted URL is necessary. The current complete app runs locally; GitHub hosts source, not the Python service.
- [ ] Review source/data attribution and any organizer-required coding/AI-assistance disclosures.
- [ ] Complete submission and retain confirmation. No submission has been sent automatically.

Freeze features after the final UI regression checks. Local AI now selects tools without calculating energy or changing medical priorities. See [the final objective checklist](FINAL_CHECKLIST.md). Public searches on November 13 found [the organization's site](https://openprojectberkeley.com/) but no event-specific official rubric or submission form.
