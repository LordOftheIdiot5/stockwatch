# N04 archive integration — private admission pilot
Status: planned envelope only; no Cloudflare writes, migrations or production credentials.
The source registry must be operator-controlled; never trust rights flags from incoming source data.
1. Require separately reviewed collection and retention permissions. Existing V122 pilot policies remain retention-unreviewed; no real records admitted by this change.
2. Preserve stable logical observation IDs, immutable revisions, and separately hashed retrieval receipts. Repeated retrieval of the same revision does not duplicate the revision object. A correction does not overwrite an earlier revision.
3. Reuse existing domain-specific private R2 buckets and D1 infrastructure where operational. Raw source snapshot bytes and their checksums remain separate from normalized revision objects. Link raw provenance before production admission.
4. Next: implement trusted policy registry and D1 migration in a private test namespace; validate object/receipt checksum, conditional writes, atomic index admission after successful object writes, replay, interruption recovery, deletion/retention obligations and restore. Do not use a public Pages directory or upload real records to CI artifacts.
5. Measure actual writes and read-back; no claim of production archival from envelope unit tests. Existing source collectors remain unchanged.
6. Source discovery N09 continues: audit existing coverage and review rights before any new collection; retain eligible original data and every meaningful revision.
