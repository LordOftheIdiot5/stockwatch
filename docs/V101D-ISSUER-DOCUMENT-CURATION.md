# V101d — Original issuer document triage before permanent storage

**Scope:** down-select original source URLs into reviewable report files, opaque download endpoints and report-specific landing pages. Metadata-only. Follows [V101b collector and archive policy](V101B-ISSUER-IR-DOCUMENT-PIPELINE.md).

## Actual proof input, 21 Nov 2026
[Live successful issuer crawl #44888950720](https://github.com/LordOftheIdiot5/stockwatch/actions/runs/44888950720), artifact `issuer-ir-link-candidates-v101`, returned **175 distinct issuer-link candidates**:
- AUSS.OL: 150 (per-issuer crawl limit); SALM.OL: 18; GJF.OL: 5; ANDF.OL: 2.
- Measured URL structure using actual downloaded metadata artifact (not inspecting report bytes): **79 direct `.pdf` links, 2 structured `.zip` files, 7 `globenewswire.com/Resource/Download/` opaque downloads, 77 annual/quarterly report landing pages, 10 other webpages**.
- Thus **88 likely document-download candidates** (79+2+7), **77 report pages requiring follow-up** and **10 false-positive/non-specific page links**.
- All 175 require final original-document review. PDF extension and opaque URL are evidence only of a *likely file endpoint*; not proof that it returns a valid PDF/ZIP, contains a specific fiscal year, is licensed for archiving, or has been read. The older annual-report index spans many years. The future report parser must not call every landing page a separate report.

## Implementation
- `scripts/issuer_ir_curation_v101.py` reads the source-preserving v101 JSON candidate artifact and vetted four-source registry; rejects unexpected issuer, source landing page, redirect host, secret/private host, false claims that documents were downloaded or rights granted, and oversized inputs.
- Labels `direct_file`, `opaque_download`, `report_landing_page` or `other_page`; keeps original URL, company, filename/type guess and fiscal candidate, **with `verifiedDocument:false` and all storage/public rights false**. Drops other pages from document review queue but counts them in a separate discarded list.
- Manual/controlled `issuer-ir-discovery.yml` workflow now creates **two short-lived 7-day CI artifacts** in one artifact folder: discovery JSON and curated review JSON. Does not add files or extracted facts to GitHub Pages or R2.
- `tests/test_issuer_ir_curation_v101.py` covers direct file, ESEF ZIP, opaque download, landing page, irrelevant news/careers, duplicate URL, unexpected host, false retention and report assertions.

## Next to unlock the user-facing datasets
1. **Prioritize 2026 and 2025 financial reports** per issuer from direct PDF/ZIP/opaque download candidate list; verify exact issuer, document date, fiscal period, MIME, size, checksum and original publication. Opaque download may return PDF/ZIP but requires verified GET/headers, not guessed file type.
2. Check source terms per original issuer and file/product, robots, retention and reproduction scope. Links/issuer-source metadata can remain published when appropriate, but document copying and especially **sale of redistributed report bytes** need a separate review.
3. Store approved original report bytes in **private Cloudflare R2**, content-addressed, size-limited with immutable source URL/date/hash and revision metadata; index document/id/issuer/period in D1, replay and outage fallback.
4. Prefer original machine-readable ESEF/XBRL for facts; validate taxonomy, units, signed values, consolidated entity, periods and revisions. For PDF, manually inspect table/page structure then implement bounded text/table extraction; no whole article/report republishing. Every published finance data point must cite source file, page or XBRL tag and clear period.
5. Display source-linked report list, actual (not guessed) annual and quarterly statements, verified future results dates and corrections in company pages; report **coverage per issuer/500 listing IDs** and distinguish original issuer facts from editorial research.

**Never infer document publication date from a link's filename or a year in the menu heading.** A downloadable report is not an automatic licensed public data product.

**Release regression note:** The unrelated V99 saved-watchlist browser test was corrected on `main` in [PR #191](https://github.com/LordOftheIdiot5/stockwatch/pull/191), after it assumed all quotes must say `Last saved` even when newer genuine quotes say `Reported`. The curated metadata workflow retains full release checks and must still pass before merge.
