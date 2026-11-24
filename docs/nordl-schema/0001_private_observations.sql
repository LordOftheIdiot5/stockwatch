-- N04c candidate, SQLite/D1 compatible; NOT applied to production.
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS nordl_observation_revisions (
 revision_id TEXT PRIMARY KEY CHECK(length(revision_id)=64),
 logical_id TEXT NOT NULL CHECK(length(logical_id)=64),
 source_id TEXT NOT NULL,
 series_id TEXT NOT NULL,
 entity_id TEXT NOT NULL,
 metric TEXT NOT NULL,
 unit TEXT NOT NULL,
 period_end TEXT NOT NULL,
 value REAL NOT NULL,
 published_at TEXT,
 object_sha256 TEXT NOT NULL UNIQUE CHECK(length(object_sha256)=64),
 object_key TEXT NOT NULL UNIQUE
);
CREATE INDEX IF NOT EXISTS nordl_revision_series_period ON nordl_observation_revisions(source_id,series_id,entity_id,period_end);
CREATE INDEX IF NOT EXISTS nordl_revision_logical ON nordl_observation_revisions(logical_id);
CREATE TABLE IF NOT EXISTS nordl_retrieval_receipts (
 receipt_id TEXT PRIMARY KEY CHECK(length(receipt_id)=64),
 revision_id TEXT NOT NULL REFERENCES nordl_observation_revisions(revision_id),
 retrieved_at TEXT NOT NULL,
 policy_id TEXT NOT NULL,
 receipt_key TEXT NOT NULL UNIQUE
);
CREATE INDEX IF NOT EXISTS nordl_receipt_vintage ON nordl_retrieval_receipts(revision_id,retrieved_at);
-- No public projection. Require validated raw source lineage and R2 read-back before admission.
