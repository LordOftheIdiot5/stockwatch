# V29f private trade history

The normalized event ledger requires reviewed internal-retention rights, exact
ISIN/MIC-to-listing mappings and a reviewed venue-specific normalizer. It does
not parse raw MMT flags and does not assume that delayed reports are complete.
Keep all inputs, SQLite database and outputs outside the repository.

Run:
`python scripts/private_trade_bars.py --events /private/events.jsonl --manifest /private/review.json --database /private/trades.sqlite --output /private/bars.json`

Manifest: internalRetentionReviewed, normalizedEventsReviewed and
mappingReviewed must be true after actual review. mappings is an array of
objects containing mic, isin, listingId. Each normalized event requires those
identifiers plus sessionDate, tradeId, a nonnegative integer revision, action
(upsert or cancel), explicit eligible boolean, currency, tradeTime and eventTime
(with time zone); upserts additionally require positive price and quantity.
Revision ordering and eligibility must come from a reviewed source-specific
adapter, not an inferred order from ingestion. Changes across session or
instrument keys require explicit cancellation of the old event. Do not mix
multiple vendors in one ledger. Raw archive flags, off-book eligibility,
venue sessions, completeness, and official closing auctions remain unverified.

Identical event replay is idempotent; conflicting revisions fail. Latest
revisions replace or cancel earlier trade state. Observed bars are recomputed
from the retained ledger, not presented as exchange-certified OHLCV. Ambiguous
opening/closing timestamps yield no open/close. This is a local persistent
SQLite implementation; no Cloudflare service or scheduled private collection
has been provisioned. Public publication remains disabled. A provider agreement
or confirmed applicable permission is required for redistribution.
