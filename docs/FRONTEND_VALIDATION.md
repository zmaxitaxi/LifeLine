# Interactive application verification

The tested flow is: configure clinic → calculate actual schedules → compare outcomes → edit equipment → test adverse weather → explore capacity.

## Environment and results

- Local macOS; Python 3.12.5; Node 25.9.0. CI also targets Python 3.11/3.12 and Node 22 on Linux.
- Browser plugin unavailable; regular Playwright Chromium was used.
- Development URL: `http://127.0.0.1:5173/`; built application and API: `http://127.0.0.1:8000/`.
- Desktop inspected at 1440×1000; mobile at 375×812.
- 194 backend tests pass. Seven end-to-end browser tests pass. TypeScript and production build pass.

| Check | Observed result |
|---|---|
| Page identity / nonblank | LifeLine title and meaningful application content rendered at the expected URL |
| Framework overlay | None observed |
| Console health | No errors/warnings on the final production navigation; an initial missing favicon was fixed |
| Real interaction | Unknown auxiliary pump added at 470.5 W / 2.3 h; returned 1.082 kWh (display rounded) requirement/completion visible; removal recalculated |
| Capacity Explorer | Larger battery alone retained the high-demand power shortfall; higher output limit eliminated that modeled shortfall |
| Weather/provenance | Historical Kisumu selection recalculated with NASA attribution; weather-only adverse test preserved other inputs |
| Invalid inputs / recovery | Incompatible battery settings produced an error; reset/retry recovered; late requests could not overwrite a newer selection |
| Offline | Browser blocked external requests while the application and historical weather calculations continued using bundled assets/data |
| Production path | Built frontend served by FastAPI at port 8000 and computed real results without a Vite proxy |
| Responsive / keyboard | No horizontal page overflow at 375 px; battery result appears in the initial mobile viewport; configuration, detailed analysis, hour checkboxes, and weather controls work with the keyboard |

## Visual review and repairs

The implemented design preserves the dark green identity band, off-white background, white cards, dark slate typography, narrow desktop inspector, and restrained emerald accents. Official shadcn/ui components now compose the interface. The measured midnight battery gain is the primary result, followed by smaller supporting metrics and a simple Before → After schedule. The hero shows the actual baseline and optimized stored energy; unequal work completion and critical shortages change its message and color. No results are hardcoded.

The full 24-hour timeline, battery/demand charts, and three-way comparison remain available under the initially collapsed Detailed analysis section. Sunshine-first equality is disclosed in the primary result as well as the detailed table. Advanced power/efficiency settings start collapsed. On mobile, clinic configuration starts collapsed so users can see the recommendation first; its controls remain available. The scheduling model and API are unchanged by this presentation rebuild.

Inspected typography hierarchy, input spacing, schedule alignment, status colors, table density, chart labels, stale/error states, and mobile wrapping. Fixed favicon loading, split chart code from the initial bundle, added a mobile horizontal-scroll cue, and kept change descriptions readable at narrow widths. Small labels, comparison headers, and chart legend text were darkened after contrast checks. Checked both viewport and schedule screenshots with `view_image`; no blocking clipping/overlap remained. The detailed mobile timeline intentionally scrolls horizontally to preserve hour readability. Motion is limited to state/width transitions and respects reduced-motion preferences.

The rendered contrast check composites computed text/background colors and applies 4.5:1 to normal text and 3:1 to large text. Initial failures in chart legends, comparison headers, and the Remove button were repaired. This is a targeted contrast check, not a full accessibility certification. Visual inspection also caught and fixed the registry slider's orientation selectors for the installed Base UI version, and a CSS rule that exposed the mobile-only configuration trigger on desktop. The slider uses center alignment so an initially hidden configuration panel does not leave its thumb waiting for an initial width measurement. Browser regressions cover the visible slider track, keyboard slider adjustment after opening configuration, and responsive trigger behavior.

Screenshots are local QA artifacts under ignored `.playwright-mcp/`, not fabricated source images or committed product assets. The current desktop and mobile screenshots were inspected after a real API calculation. No reference-image fidelity claim is applicable: this is the implemented app design, not a clone.

## Commands

```bash
python -m pytest backend/tests -q
npm --prefix frontend run build
cd frontend
npx playwright install chromium
npm run test:e2e
```

Browser tests cover custom equipment, capacity exploration, historical selection, validation/reset, rapid scenario switching, mobile/keyboard use, backend failure recovery, offline assets/data, and the production one-server path. They also verify default-collapsed detail/advanced settings, primary Before → After rows, keyboard disclosure activation, keyboard hour-checkbox editing, the mobile hero in the initial viewport, and honest shortage/work-difference messaging. The automated weather assertion checks actual returned solar energy; it does not assume every metric changes monotonically with sunshine. Identical battery differences can arise from different work-completion tradeoffs.

Remaining limitations: only Chromium and two viewport sizes were tested; no formal accessibility audit, field usability study, full installation certification, or clinical validation. Data/weather uncertainty and real appliance cycle behavior are outside this model. Browser drafts are memory-only. The default API explorer's CDN assets require internet; the actual built application does not.

Frontend implementation uses official shadcn/ui source components (Base UI primitives), Tailwind CSS, Recharts, and Lucide React. Cards, fields, inputs, selects, hour checkboxes, sunshine slider, buttons, disclosures, status badges, and comparison table share this foundation. See [hackathon submission checklist](../HACKATHON_CHECKLIST.md) for the remaining eligibility/submission questions from the user-supplied event slide.
