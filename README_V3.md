# Stockwatch research tools — V3 development release

This is an **additive** release based on the published V2 dashboard. It does not replace the hourly scanner, its watchlist, relative-volume logic, notifications, backtests, translations, existing sources or market context.

## Four pages

- `news.html`: persistent news archive, searchable across company name, ticker, sector, event type and published date. The archive starts when the new builder is first enabled; old `data/seen.json` keys cannot reconstruct missing article metadata. Association status is prominently labeled.
- `calendar.html`: results and dividend calendar, populated only by future dated events with original-source links. Strict extraction from filing headlines marks entries as **provisional**; reviewed filings can be entered into `data/events-manual.json` with verified status.
- `compare.html`: select two to four companies; show comparable daily change, excess market move, relative volume, short positions and sourced price history. Historical lines only render where date-aligned daily data exists; **no made-up lines**. Currency conversion, total return and adjustment for splits/dividends are explicitly not implied.
- `health.html`: quote coverage by exchange, missing tickers, scan freshness, commodity-context age and transparency about upstream sources which are **not individually instrumented** yet. A green scanner run alone does not prove data-source health.

## Pipeline

Add this step after the `Scan` step (before the existing `Commit results` step) in `.github/workflows/scan.yml`:

```yaml
      - name: Build research archive and health files
        run: python scripts/build_research_data.py
```

On its first run, this writes `data/news-archive.json`, `data/events.json` and `data/source-health.json`. Subsequent runs deduplicate archive records, retain the latest 180 days (max 20,000), and update health. GitHub's existing `git add data/` includes these files. The input is *only* actual scanner output.

The scanner also installs `source_telemetry` around its existing `_get` function, emitting `data/request-health.json` at the end of each run. The builder merges this with the completeness and freshness health report. Add a tested step after the existing scanner test to run:

```shell
python -m unittest discover -s tests -p test_research_data.py
```

## Deployment

Copy `index.html`, the four HTML pages, `research.js`, `research.css`, `scripts/build_research_data.py`, and `tests/test_research_data.py` into the existing repo. **Do not overwrite** `scan.py` or the scanner's data, backtest, secrets or schedules.

The new index provides navigation to the research pages while continuing to load the existing V2 `app.js` and `style.css`.

## Follow-ups

1. Move archival history out of Git when it grows; consider Cloudflare R2 or a small API if the feed becomes large.
2. Add durable issuer identifiers (LEI/ISIN/FIGI) and source-specific company mapping to tighten news attribution.
3. Obtain licensed corporate financials and historical prices before presenting full multi-year comparisons or valuation ratios.
4. Extend request telemetry with parser-level validity and independent source-freshness checks. HTTP success alone is insufficient.
5. Expand the calendar from official filings or a licensed financial-events feed, with review status for parser-derived dates.
