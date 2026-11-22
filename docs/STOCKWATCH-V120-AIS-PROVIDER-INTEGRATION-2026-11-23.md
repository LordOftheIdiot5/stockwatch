# V120 — Rights-verified selectable ships (AIS)

**Initiated:** 23 November 2026. **Release gate:** AIS vessel layer not yet live.
**Baseline:** V119 map-first Shipping, PR #220, merged and deployed with published-file parity verification.
**Goal:** selectable real vessels with actual AIS-reported position, identity, speed/course, reported destination, provenance and timestamps. Verified port/company relationships later. Never invent tracks, cargo, ETA, charter rates or company links.

## Source verification and rights

| Area | Source | Access and licensing | Status |
| --- | --- | --- | --- |
| Finland and Baltic-area receiver coverage | [Fintraffic marine AIS API](https://www.digitraffic.fi/en/marine-traffic/); [location endpoint](https://meri.digitraffic.fi/api/ais/v1/locations) and vessel metadata by MMSI | [CC BY 4.0](https://www.digitraffic.fi/en/terms-of-service/). Attribution, licence link and modifications must be identified. Set a provider-identifying Digitraffic-User header. Observe rate limits and caching. | Actual single-MMSI position and name/destination metadata observed from public API on 22 November 2026 UTC. Read-only adapter and local tests on this draft branch. |
| Finland port calls | Fintraffic marine port call APIs | Confirm field and version details for collection. Port-call events are not AIS position reports. | Discovery only; not connected |
| Norway and Norwegian EEZ | [Kystverket AIS open data](https://www.kystverket.no/en/sea-transport-and-ports/ais/access-to-ais-data/) and [BarentsWatch developer AIS](https://developer.barentswatch.no/docs/AIS/live-ais-api/) | Norwegian public open AIS coverage with category exclusions. BarentsWatch automated access requires an approved API client and OAuth credentials. | No credentials configured; no Stockwatch Norwegian live feed |
| European density backdrop | [EMODnet](https://emodnet.ec.europa.eu/) | Aggregated density and actual vessel positions must be distinguished; check individual-product terms | Candidate context only |

## First delivered part: V120a

- A deliberately narrow one-MMSI Python source adapter, at scripts/fintraffic_ais_v120.py, with private local output only. It is not called from shipping.html.
- Normalize Fintraffic GeoJSON geographic coordinates in longitude/latitude order, with timestampExternal as epoch milliseconds. The different timestamp field is an AIS second-of-minute value and must never be treated as a UTC event time.
- Reject out-of-range coordinates, invalid MMSI, timestamp more than 30 minutes old, future clock drift over two minutes, unknown position, and AIS unavailable speed/course/heading sentinels.
- Join name and self-reported destination only by matching MMSI; keep vessel metadata observation time distinct from movement observation time.
- Preserve original source, licence, attribution and retrieval time. The AIS destination is not independently confirmed arrival, expected route or operator.
- Offline unit tests cover genuine provider response shape, edge cases and fail-closed behavior. The example is a test fixture, not a vessel to place on the live atlas.
- No public exports, live ships, speculative fleet locations, tracks or last-known positions have been added to V119.

## Ordered implementation stages

1. **V120a — Data-contract and source proof:** Finish automated CI for the read-only single-vessel normalizer and source documentation; keep PR draft.
2. **V120b — Reliable centralized collector:** Add a bounded approved Cloudflare Worker scheduled pull or authenticated ingestion path with a provider-side refresh budget (initially at least 60–180 seconds per source snapshot), error/retry and 429 handling, source timestamps, redaction/privacy checks, and permitted R2/D1 retention. Do not have each browser hit a broad source feed. Audit collection/display/storage/export rights separately.
3. **V120c — Real AIS interface:** Add a genuinely selectable vessel layer to the full-screen V119 map. Efficient marker clustering/search, keyboard-accessible table, original timestamps, speed/course/destination qualifiers and port context. Separate source coverage geography and stale last-known markers from observations still within freshness threshold. Never imply globally complete coverage.
4. **V120d — Norway:** Register BarentsWatch API credentials server-side, confirm entitlements, filter small/restricted vessels as required, implement Norwegian area source and quality gates.
5. **V120e — Ports and companies:** Integrate authorized original Norwegian and Finnish port-call data, UN/LOCODE matches, and documented asset-company identity joins. Do not infer ship owner or cargo from a geographic point.
6. **V121+ — Market economics:** Extend independently rights-cleared charter spot rates, fixtures, bunker/port cost and freight prices. Current USDA grain costs and company-reported quarterly dayrates are not broker spot assessments.

## Production acceptance

No launch until source terms and rights are verified, source health is visible, provider rate limits are respected, no synthetic vessels are published, timestamps/age are correct and stale errors are explicit. Require browser audits at 320, 390, 768, 1024, 1440, 1672 and 1920 px in both themes, keyboard and screen reader compatibility, good pan/zoom performance, original 40 port pins and all historical research unchanged, no horizontal overflow, full site regression, and actual Cloudflare published-file parity. Keep the V119 production release unaffected while V120 is in draft.

**Operational rule:** No API key in GitHub or browser JavaScript. No billable data contract without user approval.