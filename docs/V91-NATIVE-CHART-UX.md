# Stockwatch V91 UX-S4 — Native chart visual and control improvements
2026-11-21. Stacked on V90 layout PR #168; master design issue #165.

Adds a strictly presentation-only native-chart-ux-v91.css to terminal.html and stocks.html *after* their existing CSS. It does not replace native-chart.js, change chart observations, generate candles, alter data rights, or introduce external dependencies. Improves label contrast/readability, chart toolbar spacing, minimum control targets (38px desktop/44px mobile), clearly visible active buttons, stronger crosshair, responsive drawing-rail sizing, numeric inspector and keyboard focus.

The source already supports line/candles (only when genuine OHLC), SMA/EMA/RSI, pan/zoom, keyboard inspection, source links and dated event markers. Retain those; do not invent data to fill empty charts or enable disabled controls.

Source tests: python -m unittest discover -s tests -p test_native_chart_ux_v91.py -v
Legacy regression: node --test tests/test_native_chart_v49.mjs tests/test_chart_v25.mjs tests/test_chart_display_v30b.mjs
Browser QA: run scripts/visual_audit.py --output visual-audit/v91 --pages stocks terminal --devices desktop mobile small-mobile tablet wide; capture dark and light theme separately through browser_check_overview_layout_v90.py (overview) and existing stock/terminal checks. Verify chart controls with authorized available history; where no history is legally available, the insufficient-data state must remain intact. Include keyboard tab/slider/arrow focus, long labels, no right-hand axis clipping and 320px overflow.

Status: code authored; tests, screenshot comparison and live deployment not verified. No market-data source was changed.
