# V88d: historical driver research

No price histories or benchmark/factor permission are assumed. The UI starts with an explicit coverage gap. Never insert test prices in data/.

## Inputs

The ordinary monitored-equity importer accepts an optional explicit boolean derivedResearchPermitted in the owner-reviewed entitlement manifest. It is false unless explicitly granted. Reference histories are not automatically enabled for this engine; they need exact profile mapping and a separate review.

Expected asset history: exact ticker, adjusted=true (provider describes adjustment method), currency, valid source and licence URLs, redistributionPermitted=true, derivedResearchPermitted=true, positive volume and dated closes.

data/sensitivity-inputs-v1.json lists reviewed exact listing keys. Example schema (not production data):

    {"schemaVersion":1,"listings":{"EXAMPLE":{"identityReviewed":true,"mic":"XOSL","benchmark":{"id":"market_example","path":"data/sensitivity-inputs/market_example.json"},"factors":[{"id":"factor_example","path":"data/sensitivity-inputs/factor_example.json"}]}}}

Each input file requires its exact seriesId, source, sourceUrl, licenseReference, redistributionPermitted=true, derivedResearchPermitted=true, frequency=business_day and observations as date/value pairs. Factor inputs require unit and changeMethod=log_return. The benchmark additionally requires kind=market_benchmark, mic and currency matching the stock and adjusted=true. A reviewed mapping is an explicit policy choice, not proof of economic exposure. No benchmark or factor is currently seeded. Data contracts must be verified before publication. EIA Brent/WTI original-source rights are pending.

## Method

Strictly positive unique closes and volume; exclude current UTC date, invalid dates and duplicate dates. Match both endpoints of successive observed periods, max four calendar days, no fabricated prices. Factor association is Pearson correlation on log price changes with at least 60 matched intervals; two chronological halves of 30+ intervals show directional stability, not predictive validity. No causal or statistical significance claims. Does not account for other common risk factors or asynchronous closes.

Issuer announcement comparison: close before UTC publication date to first close strictly after; same market/currency benchmark, exact matching observed sessions. Exclude overlapping windows and dates with multiple records or tags; only explicitly issuer-confirmed, single classified topic events. Require at least ten qualifying windows per topic. Report median simple stock return minus benchmark return in percentage points, not regression-adjusted abnormal return. The window includes publication-day and next-observed-day movement and is not a pure announcement reaction. Unobserved catalysts and gaps remain possible. No ranking, prediction or investment advice.

This is a client-side research view over existing public-authorized data, not a new private storage or history collector.
