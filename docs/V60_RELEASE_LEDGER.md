# V60 candidate release ledger — 2026-11-17
This is a milestone candidate, not a declaration of full completion. The locked roadmap remains authoritative.

| Version | PR | Evidence before V60 |
|---|---|---|
| V47 | #59 | Initial browser matrix passed; deployed |
| V48 | #60 | Pagination tests passed; deployed; full mobile density audit open |
| V49 | #61 | Native chart tests passed; deployed; touch/drawing persistence open |
| V50 | #62 | Company browser tests passed; deployed |
| V51 | #63 | Screener tests passed; deployed |
| V52 | #64 | Synchronized official chart tests passed; deployed; licensed equity panes open |
| V53 | #65 | Unit/automated checks passed; deployed; verified cross-listing registry and UI open |
| V54 | #66 | Warehouse tests passed; deployed code; no persistent production database |
| V55 | #67 | Automated checks passed; deployed; dedicated visual checks open |
| V56 | #68 | Automated checks passed; maps and freight licences open |
| V57 | #69 | Automated checks passed; exact dataset/route deep links and browser checks open |
| V58 | #70 | Product catalog implementation committed; commercial API delivery not enabled |
| V59 | #71 | Local workspaces implementation committed; browser checks required |
| V60 | candidate | Full combined audit implementation; results pending |

Candidate tests: 19 pages × four resolutions × two themes (152 cases), local link/asset checks, theme and overflow checks, uncaught errors, image alt attributes, timings, five dedicated interactions and prior regression scripts. This is not a full WCAG certification or a live network performance measurement. Candidate snapshots deliberately do not fetch external providers; 404s for optional absent histories are recorded and distinguished from missing scripts/styles/images. Review screenshots and repeat actual production verification before release acceptance.

Outstanding rights and product blockers: provider licensing and 138-stock EOD recovery; #57 listing migration; reviewed cross-market relationships; durable private warehouse hosting; multi-equity chart panes; persistent drawings and touch testing; verified geographic route maps; commercial data delivery agreement and API; exact dataset deep links; comprehensive accessibility/performance audit and mobile before/after heights. Github Pages currently uploads the repository tree; audit public output and tighten deployment allowlist independently before storing any sensitive data. No secrets or warehouse files intentionally added.

V60 includes the approved Nordl artwork files from production commit ee2ffa42db074887d513a47e760c31829e66e514 so the combined candidate reflects current branding. Do not overwrite current production-generated data with old branch snapshots.

## First audit and corrective increment
Run 44153845989: 152/152 page cases and 3/5 interaction cases passed. Search assertion used SalMar while actual record says Salmar; industry assertion did not await detail content. Correct assertions without dropping behavioral checks. Contain mobile heatmap/screener and attention list height, remove duplicate news, compact module artwork, refresh principal entry point assets. Retest and visual acceptance pending. No new functionality.

## Price-first presentation and shipping coverage
Default stock screener is monitored listings; searches and explicit universe controls preserve access to discovery records. Keep dated latest reported values visible without treating a mixed session as comparable. Terminal excludes bare reference records by default unless searched or pinned; show dates. Heatmap remains neutral outside eligible session; reference records remain explorable. Shipping prioritizes existing official dated series over unpriced Baltic route definitions; adds official monthly BLS deep-sea freight PPI via existing FRED collector (first successful refresh pending), https://fred.stlouisfed.org/series/PCU483111483111. No new entitlement or subscription; public price-feed rights still require resolution. Candidate checks pending.
