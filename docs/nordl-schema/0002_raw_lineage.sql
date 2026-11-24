-- Candidate extension; apply only in private namespace after deployment review.
CREATE TABLE IF NOT EXISTS nordl_receipt_raw_lineage (
 receipt_id TEXT PRIMARY KEY REFERENCES nordl_retrieval_receipts(receipt_id),
 source_receipt_id TEXT NOT NULL,
 raw_sha256 TEXT NOT NULL CHECK(length(raw_sha256)=64),
 raw_object_key TEXT NOT NULL
);
