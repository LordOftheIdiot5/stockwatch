-- Candidate private index guards. Identical replay permitted, conflicting rows rejected.
CREATE TRIGGER IF NOT EXISTS nordl_revision_conflict BEFORE INSERT ON nordl_observation_revisions
WHEN EXISTS (SELECT 1 FROM nordl_observation_revisions r WHERE r.revision_id=NEW.revision_id AND NOT (
 r.logical_id IS NEW.logical_id AND r.source_id IS NEW.source_id AND r.series_id IS NEW.series_id AND r.entity_id IS NEW.entity_id AND r.metric IS NEW.metric AND r.unit IS NEW.unit AND r.period_end IS NEW.period_end AND r.value IS NEW.value AND r.published_at IS NEW.published_at AND r.object_sha256 IS NEW.object_sha256 AND r.object_key IS NEW.object_key))
BEGIN SELECT RAISE(ABORT,'revision conflict'); END;
CREATE TRIGGER IF NOT EXISTS nordl_receipt_conflict BEFORE INSERT ON nordl_retrieval_receipts
WHEN EXISTS (SELECT 1 FROM nordl_retrieval_receipts r WHERE r.receipt_id=NEW.receipt_id AND NOT (r.revision_id IS NEW.revision_id AND r.retrieved_at IS NEW.retrieved_at AND r.policy_id IS NEW.policy_id AND r.receipt_key IS NEW.receipt_key))
BEGIN SELECT RAISE(ABORT,'receipt conflict'); END;
CREATE TRIGGER IF NOT EXISTS nordl_lineage_conflict BEFORE INSERT ON nordl_receipt_raw_lineage
WHEN EXISTS (SELECT 1 FROM nordl_receipt_raw_lineage r WHERE r.receipt_id=NEW.receipt_id AND NOT (r.source_receipt_id IS NEW.source_receipt_id AND r.raw_sha256 IS NEW.raw_sha256 AND r.raw_object_key IS NEW.raw_object_key))
BEGIN SELECT RAISE(ABORT,'lineage conflict'); END;
