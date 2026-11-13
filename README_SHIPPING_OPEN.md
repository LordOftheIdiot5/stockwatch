# Stockwatch shipping: open USDA indices and licensed benchmark separation

## Implemented
- The USDA Agricultural Marketing Service publishes a weekly **Grain Transportation Cost Indicators** dataset. Stockwatch imports its two ocean-going vessel cost indices: US Gulf → Japan and Pacific Northwest → Japan.
- The indices are **2017 = 100**, *not USD/tonne voyage rates*. The documented **2017 base rates** ($39.33/tonne Gulf; $21.05/tonne PNW) explain index construction and are never presented as current freight quotes.
- The importer uses the public, no-key Socrata endpoint `https://agtransport.usda.gov/resource/8uye-ieij.json` with exact documented fields: `date`, `gulf_vessel`, and `pacific_vessel`. It validates numerical values and observation dates; retains the original dates if the upstream feed fails.
- Historical dated index charts appear on Shipping & Freight, separate from the route cards requiring licensed Baltic quotes.
- `data/shipping-open.json` contains the attributed observations, source status and metadata. The official-data workflow refreshes it on weekdays and registers it in the dataset catalog; Data Health reports the upstream status.

## Important limitations
- USDA's GTR dataset page describes underlying index datasets as aggregated from non-confidential, non-copyrighted sources. The AgTransport catalog itself does **not specify a license**. The site therefore attributes the source and does **not** ingest the separate USDA raw quote visualization credited to O'Neil Commodity Consulting.
- Direct Capesize, Newcastlemax, Panamax and tanker route price histories remain unavailable without the proper Baltic Exchange redistribution license. No index chart may be labeled as a route's actual rate in USD/tonne, USD/day or Worldscale.
- The IMF PortWatch, UNCTADstat and Freightos pages are linked as research leads only; no unlicensed dataset is automatically copied. Validate each dataset's redistribution terms before publishing it.

## Sources
- USDA AMS GTR datasets: https://www.ams.usda.gov/services/transportation-analysis/gtr-datasets
- USDA ocean cost indices: https://agtransport.usda.gov/Transportation-Costs/Grain-Transportation-Cost-Indicators/8uye-ieij
- Third-party quote visualization (not ingested): https://agtransport.usda.gov/Bulk/Bulk-Grain-Ocean-Freight-Rates/ehic-wtxb
- Baltic Exchange commercial feed: https://www.balticexchange.com/en/data-services/Methodology/market-data.html

Run locally (requires network):
```
python -m unittest discover -s tests -p 'test_shipping_open.py' -v
python scripts/shipping_open.py
```

## World Bank annual container-port activity (TEU)
- `scripts/shipping_ports.py` fetches World Bank WDI indicator `IS.SHP.GOOD.TU` through the official JSON API, with country-level and World series; this is **container throughput**, not freight prices, vessel earnings or daily port calls.
- World Bank labels this indicator **CC BY 4.0**, sourced from UNCTAD. Each exported series attributes World Bank WDI and UNCTAD, links to the indicator and license terms, and retains original observation years. See https://data.worldbank.org/indicator/IS.SHP.GOOD.TU and https://www.worldbank.org/ext/en/legal/terms-conditions/datasets .
- The importer validates provider indicator, country codes, finite positive TEU observations and annual dates, rejects insufficient coverage, and preserves existing dated observations when the API fails. It writes `data/shipping-ports.json` and updates the dataset catalog.
- The scheduled official-data workflow refreshes the dataset on weekdays. Shipping & Freight shows a separate annual country selection and TEU history; Data Health independently reports World Bank API status.
- **Caveat:** TEUs count transshipments and empty containers; annual totals are not live container throughput, port capacity, or current prices. Do not sum countries with the World aggregate or equate TEU volumes to Baltic freight benchmarks.

Local validation:
```bash
python -m unittest discover -s tests -p 'test_shipping_ports.py' -v
python scripts/shipping_ports.py
```
