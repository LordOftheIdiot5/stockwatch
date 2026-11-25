# Official delayed exchange access

No API key or subscription is required to access the two official portals.
Euronext permits internal use; commercial-benefit distribution requires an
agreement. Nasdaq's equity report page states other than non-commercial usage
may incur fees. Do not treat public download availability as redistribution
permission.

Run the official Oslo schema probe:
    python scripts/delayed_exchange.py --market OSL

For authorized internal Euronext research, preserve the original archive on
a persistent private disk outside the repository:
    python scripts/delayed_exchange.py --market OSL --private-archive "/private/exchange-data"

Available market codes: OSL, PAR, AMS, BRU, DUB, LIS, MIL. The download URL
pattern is based on the public exchange download service; validate live.
Nasdaq scheduled report discovery does not download trade files. Nasdaq European
Data confirmed private non-commercial use of downloadable files on 2026-11-25.
Public value-added display, polling cadence and long-term retention remain
separate review gates. Euronext contact: databyeuronext@euronext.com.

The scheduled workflow probes endpoints and validates the Euronext archive
header without publishing or persisting records. It is not a historical
collection job. No quote price, trade row, or raw archive enters GitHub Pages,
CI artifacts or Leivro exports. Persistent private storage and trade
normalization (including corrections, cancellations, market sessions, exact
ISIN/MIC mappings and currency) are separate implementation steps.

## Identity reconciliation (V29e)

Use `python scripts/exchange_identity.py --market OSL` with the existing
STOCKWATCH_OPENFIGI_KEY environment variable. For authorized persistent internal
research, pass `--archive /private/exchange-data/euronext/archive.zip` and
`--private-output /private/exchange-data/identity-audit.json`. No data is written
to the repository. Only the exact MIC and checksum-valid ISIN are submitted to
OpenFIGI; no prices, quantities or trade timestamps are submitted. A unique
instrument FIGI must match a unique existing listing at that MIC. Duplicate
FIGIs, multiple observed ISINs for one record and conflicting known ISINs are
rejected. A successful join remains a candidate for human review, not verified
active-listing status or permission to publish. Segment MICs are not silently
mapped to operating MICs. CI reports a whole-universe count and validation
status, not the exchange-derived records. Do not publish the private output.

## N09a Nasdaq private CSV pilot (25 November 2026)

Official report pages: https://tradereports.nasdaq.com/shares/trade-reports/post-trade
and https://tradereports.nasdaq.com/baltic-trade-reports/equity/post-trade . Files
are delayed 15 minutes, generated every minute in market hours and available
online for 48 hours. The portal currently returned no file links in our
external inspection. When an actual CSV is available, download one via the
official report page to a private location outside the repository and run:

    python scripts/nasdaq_private_csv_probe.py --csv /private/sample.csv --private-noncommercial

The local probe is bounded to 8 MiB and 100,000 rows; UTF-8 CSV only. It reports
candidate column roles and counts, not raw header values, trade rows, prices,
identities or source file paths. Unknown schemas fail closed. Candidate field
aliases are not an assertion about the actual Nasdaq CSV format. No network
polling or archive is added; delete temporary sample after the review unless
retention is authorized. Do not upload CSVs or include them in CI artifacts.
Run fixture tests with python -m unittest discover -s tests -p test_nasdaq_private_csv_probe.py -v .
Next validate actual provider format, timestamp semantics, correction flags,
units and exact MIC/ISIN joins before any price normalization or publication.
Any future authorized public display must say "Data Delayed 15 minutes".
