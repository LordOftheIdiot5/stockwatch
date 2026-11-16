# V29g — private exchange archive activation

This is separate from the Stockwatch news D1 database and public website.
It archives actual Euronext report ZIPs and retrieval receipts, **not**
official closing prices. Nasdaq collection remains disabled. A source-specific
normalizer and reviewed price display rights are still required.

## One-time setup

1. Confirm Euronext's applicable internal-use and long-term retention rights,
   including contracted cloud storage. Do not enable collection until reviewed.
2. In Cloudflare R2 create a dedicated Standard bucket named
   `stockwatch-private-market-history`. Keep r2.dev public access disabled,
   no custom domain, no public Worker routes and no public presigned links.
   Review account costs and retention limits before scheduling collection.
3. Create an R2 object read/write API token scoped only to that bucket.
   Never send credentials in chat, source files or workflow logs.
4. In Stockwatch GitHub Settings > Secrets and variables > Actions, add
   repository secrets STOCKWATCH_R2_ACCOUNT_ID, STOCKWATCH_R2_ACCESS_KEY_ID,
   STOCKWATCH_R2_SECRET_ACCESS_KEY. Add repository variable
   STOCKWATCH_R2_BUCKET with the bucket name above. Only after the complete
   review set STOCKWATCH_R2_RETENTION_APPROVED to true.
5. Run the Private exchange archive workflow manually with smoke_only=true
   to test a synthetic marker. Verify the bucket remains private.
6. Run manually with smoke_only=false to collect current and previous Oslo
   trading-day archives. Check successful storage status and R2 privately.
   The weekday schedule runs at 20:30 UTC when the approval variable is true.

The archive uses SHA-256 content keys and create-only conditional writes.
Revised reports create separate objects; identical reports do not duplicate
raw objects. Retrieval receipts record actual fetch times and requested report
windows, which may differ from market session dates. The scheduled job is not
proof of complete trade coverage: exchange holidays, corrections, timeouts,
publication timing and missing reports require additional review.

No archive is uploaded as a CI artifact, committed to Git, returned by the
public Worker, or included in public price metrics. The configured 64 MiB
download bound is inherited from delayed_exchange.py; larger reports fail
closed. Cloudflare retention and storage costs are not assumed to be zero.
Disable scheduling by setting STOCKWATCH_R2_RETENTION_APPROVED=false.
