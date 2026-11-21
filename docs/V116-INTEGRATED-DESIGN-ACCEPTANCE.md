# V116 — integrated design acceptance and open defects
**State:** V116a measured first-fold implementation and expanded QA in progress. **Not a final owner-accepted design certificate.**
**Approved concept:** [APPROVED-STOCKWATCH-DESIGN-TARGET-V1.md](APPROVED-STOCKWATCH-DESIGN-TARGET-V1.md) / Library `/Stockwatch/Design References/stockwatch-approved-full-width-overview-v1.png`, 1672×941, SHA-256 `df85998bd202dd9e4b3832a85edfaaf9fde78a417af4dcc3c7ced9e076be7b00`.

## Grounded baseline (V115 checkout capture, 21 November 2026)

- [Prior V115 visual audit](https://github.com/LordOftheIdiot5/stockwatch/actions/runs/44943466863) captured 19 desktop (1440px) and 19 phone (390px) pages. All 38 had HTTP 200, zero page-level horizontal overflow, zero JS exceptions and zero failed requests in that capture. This proves baseline stability, **not** complete approval.
- Actual 1440px checkout `overview-desktop-top.png`: first header begins at about y88px; index strip ends near y344px; primary chart/breadth/news begins near y370px. The heatmap and factual exchange-coverage/watchlist row begins **around y878px**, almost entirely below a 900px first screen.
- Approved 1672×941 **concept**: market summary title, four illustrative global-index cards, main analysis row, heatmap/map/watchlist and tools/events are visually grouped on the first screen; the heatmap begins near y595px. **These y values have different source widths and cannot be treated as direct pixel-identical performance targets.**
- Actual 136 heatmap dated-change tiles (baseline screenshot) are legitimate source-backed visualizations, not a licensed exchange index or broad market-cap benchmark. Three Taiwan index cards must remain three properly attributed Taiwan source series until rights-cleared international sources exist. The world silhouette with Europe/Hong Kong venue pins depicts **listing coverage, not returns**. Existing source-health denominators can change after valid scanner refresh; do not hard-code 136/139, 152/500 or exact events as guaranteed production values.
- 19 routes have materially different depth (roughly 1000–10,000px tall), so a screenshot at top alone cannot demonstrate that subpages are polished or navigable.

## V116a change and acceptance scope

**Fix:** Reduce unused vertical space in the source-backed chart controls, metadata row, main news rail and panel gutters without inventing extra index/market data. Preserve:
- original `640×286` macro SVG viewBox, native axes, source/observation date, keyboard crosshair, range/series/view selectors;
- genuine issuer-linked news and narrow bounded scroll region, real breadth and saved watchlist;
- full-width reversible expanded heatmap and non-fabricated world geographic coverage;
- first-screen desktop three-column row and mobile index/chart order.

**Strict first-fold browser gate:** at 1440, 1672 and 1920 widths in both themes, main chart, breadth and news align vertically, secondary heatmap/coverage/watchlist align, no overflow, chart aspect ratio remains honest, source labels and saved empty watchlist are truthful. 1440 heatmap y target ≤855px versus y≈878 baseline, with separate thresholds for wide desktop. These are progress gates, **not** arbitrary pixel-equivalent to the illustrative reference.

**Full audit:** `scripts/visual_acceptance_v116.py` records 19×6×2 = 228 viewport/theme/page combinations (320/390/768/1024/1440/1920; dark/light), 390/1440 screenshots, main-section geometry, broken rendering, missing headings, JS failures, same-origin request failures and page-level overflow. Test a deliberately failed coverage endpoint and prove the UI says unavailable with zero fictitious map pins. Capture a labelled CSS 2× zoom **proxy**. Native 200% browser zoom, screen reader, and human contrast/visual matching still require manual testing.

## Outstanding V116 acceptance defects / blockers

| Priority | Defect or deliberate limitation | Release gate / follow-up |
| --- | --- | --- |
| P0 design | Overview currently begins the heatmap near screen bottom at 1440; approved reference puts chart + map + watchlist in the first-screen story | Test V116a first fold; review new screenshot side-by-side; continue V116b structural grid if too low or small |
| P0 source rights | Broad geographic market index levels/returns and market-cap-weighted local heatmap are not rights-cleared for every requested exchange | **Do not** fill concept's OSEBX/AEX/CAC/S&P price cards, world-return labels or fake holdings; real coverage map remains literal coverage |
| P0 feature truth | No verified upcoming events or populated saved watchlist in default browser | Preserve factual no-data states, implement only after source event evidence and actual consent-based saved settings |
| P1 UX | 19 subpages must preserve working navigation, focus, charts and dated fallback at 320–1920 and 200% zoom | Automated 228-view matrix plus independent keyboard/manual native zoom review |
| P1 reliability | Scanner run success does not equal validated completed-session stock prices | Keep source-comparison counts, status, last-known timestamp and unit visible; monitor #176 |
| P1 commercial | Proposed APIs and samples are metadata-only, no redistribution entitlements | Keep V115 rights-first catalog; no fictional public API or promised paid feed |

## Reviewed CI evidence and V116b follow-up (2026-11-21)
The [V116a visual artifact](https://github.com/LordOftheIdiot5/stockwatch/actions/runs/44947769508) records 228/228 normal viewport tests with zero critical errors. At 1440, 1672 and 1920 widths the actual secondary-row top is about **817px, 855px and 926px**, respectively. The reference 1672px concept depicts the row at about 595px; initial-screen composition **still needs owner-reviewed correction**. The matrix's diagnostic CSS 200% zoom proxy **does overflow** (1622px scrollWidth at a 1440px viewport), so native accessibility zoom is **not accepted**. These precise remaining tasks are filed in [V116b issue #205](https://github.com/LordOftheIdiot5/stockwatch/issues/205). Do not hide this failure behind the green 228 normal-width checks.

## Final certification checklist (do not close before evidence exists)

- [ ] All 19 routes screenshot-reviewed at top/middle/bottom at desktop and phone; 320/768/1024/1920 inspected, dark/light.
- [ ] Approved 1672×941 composition compared against a current 1672×941 source-backed render; remaining differences explicitly accepted or repaired.
- [ ] Native 200% browser zoom and keyboard-only task navigation, including sidebar/menu/search/heatmap/tool disclosures.
- [ ] Offline/stale and no-history scenarios clear and recoverable; tested separately from site deployment.
- [ ] Metadata rights, licensed history, market labels and chart units verified; no invented figures or implied paid feeds.
- [ ] No critical and no major accessibility/function defects; publish release SHA, scanner/Pages source dates, measured screenshots and unclosed issues to #165.
- [ ] **Owner's explicit visual sign-off** before calling Stockwatch's approved design finished.

**Resumption order:** Review `visual-audit/v116/acceptance-report.json` and screenshot artifact, fix failures and geometry; run full release suite + V116 visual audit; verify production file bytes and independent scanner job, then start V116b remaining structural/visual defects. Never infer design acceptance from a green unit-test suite.
