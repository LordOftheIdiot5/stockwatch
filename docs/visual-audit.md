# Stockwatch visual audit

This read-only audit captures actual browser screenshots, not generated mockups.
It serves the exact checked-out site locally and can optionally inspect the public
deployment. Each view records HTTP errors, uncaught JS errors, horizontal overflow,
broken images, headings and map tile counts. External content other than Google
Fonts is blocked to avoid analytics and nondeterministic embeds, so external chart
widgets and external images may be absent. A local pass does not establish public
DNS or TLS connectivity; use the production pass for that.

## Run locally (PowerShell)
```powershell
python -m pip install playwright==1.56.0
python -m playwright install chromium
python scripts/visual_audit.py --output visual-audit/checkout
python scripts/visual_audit.py --base-url https://stocks.nordl.dev/ --output visual-audit/live --pages overview stocks company terminal shipping spreads calendar health
```

The output is an audit.json plus PNG screenshots at desktop 1440×1000 and mobile
390×844 (top, middle, bottom as available, and the stocks heatmap interaction).
The workflow uploads these files as an Actions artifact, including if an audit
fails. It does not publish screenshots as part of the site or modify market data.
Run manually in Actions using Stockwatch visual audit after merging.
