PRAGMA foreign_keys = ON;

BEGIN;

CREATE TABLE IF NOT EXISTS ingestion_records (
  id INTEGER PRIMARY KEY,
  source_path TEXT NOT NULL,
  source_type TEXT NOT NULL CHECK (source_type IN ('runtime-linked', 'non-operational', 'standalone-reference')),
  dry_run INTEGER NOT NULL DEFAULT 1 CHECK (dry_run IN (0, 1)),
  cleanup_decision TEXT NOT NULL CHECK (cleanup_decision IN ('delete', 'keep', 'skip')),
  cleanup_mode TEXT NOT NULL DEFAULT 'default' CHECK (cleanup_mode IN ('default', 'forced-delete', 'forced-keep')),
  cleanup_requested INTEGER NOT NULL DEFAULT 0 CHECK (cleanup_requested IN (0, 1)),
  cleanup_executed_at TEXT,
  cleanup_result TEXT CHECK (cleanup_result IN ('pending', 'success', 'failed', 'skipped')),
  cleanup_error TEXT,
  extraction_summary TEXT,
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
  updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
  CHECK (
    (cleanup_result IS NULL AND cleanup_executed_at IS NULL)
    OR (cleanup_result = 'pending' AND cleanup_executed_at IS NULL)
    OR (cleanup_result IN ('success', 'failed', 'skipped') AND cleanup_executed_at IS NOT NULL)
  )
);

CREATE TABLE IF NOT EXISTS features (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL UNIQUE,
  capability_key TEXT NOT NULL,
  category TEXT NOT NULL,
  description TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('active', 'deprecated', 'experimental')),
  version INTEGER NOT NULL CHECK (version >= 1),
  source_ref TEXT,
  ingestion_record_id INTEGER,
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
  updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
  FOREIGN KEY (ingestion_record_id) REFERENCES ingestion_records(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS feature_candidates (
  id INTEGER PRIMARY KEY,
  ingestion_record_id INTEGER NOT NULL,
  name TEXT NOT NULL,
  capability_key TEXT NOT NULL,
  category TEXT NOT NULL,
  description TEXT NOT NULL,
  source_ref TEXT NOT NULL,
  fingerprint TEXT NOT NULL,
  performance INTEGER NOT NULL,
  security INTEGER NOT NULL,
  complexity INTEGER NOT NULL,
  score_total INTEGER GENERATED ALWAYS AS (performance + security - complexity) STORED,
  reusable_score INTEGER NOT NULL DEFAULT 0 CHECK (reusable_score BETWEEN 0 AND 10),
  reusable_across_projects INTEGER NOT NULL DEFAULT 0 CHECK (reusable_across_projects IN (0, 1)),
  reusable_reason TEXT,
  inferred_dependencies TEXT NOT NULL DEFAULT '[]',
  unresolved_dependencies TEXT NOT NULL DEFAULT '[]',
  candidate_status TEXT NOT NULL DEFAULT 'candidate' CHECK (candidate_status IN ('candidate', 'resolved', 'merged_variant', 'experimental', 'discarded')),
  resolver_decision TEXT CHECK (resolver_decision IN ('replace', 'merge_variant', 'keep_old')),
  resolved_feature_id INTEGER,
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
  updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
  FOREIGN KEY (ingestion_record_id) REFERENCES ingestion_records(id) ON DELETE CASCADE,
  FOREIGN KEY (resolved_feature_id) REFERENCES features(id) ON DELETE SET NULL,
  UNIQUE (ingestion_record_id, capability_key)
);

CREATE TABLE IF NOT EXISTS feature_scores (
  feature_id INTEGER PRIMARY KEY,
  performance INTEGER NOT NULL DEFAULT 0,
  security INTEGER NOT NULL DEFAULT 0,
  complexity INTEGER NOT NULL DEFAULT 0,
  score_total INTEGER GENERATED ALWAYS AS (performance + security - complexity) STORED,
  score_model TEXT NOT NULL DEFAULT 'v1',
  computed_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
  FOREIGN KEY (feature_id) REFERENCES features(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS feature_embeddings (
  feature_id INTEGER PRIMARY KEY,
  embedding_tokens TEXT NOT NULL,
  model TEXT NOT NULL DEFAULT 'lite-token-v1',
  updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
  FOREIGN KEY (feature_id) REFERENCES features(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS feature_relations (
  id INTEGER PRIMARY KEY,
  from_feature_id INTEGER NOT NULL,
  to_feature_id INTEGER NOT NULL,
  relation_type TEXT NOT NULL CHECK (relation_type IN ('replaces', 'replaced_by', 'variant', 'depends_on')),
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
  FOREIGN KEY (from_feature_id) REFERENCES features(id) ON DELETE CASCADE,
  FOREIGN KEY (to_feature_id) REFERENCES features(id) ON DELETE CASCADE,
  CHECK (from_feature_id <> to_feature_id),
  UNIQUE (from_feature_id, to_feature_id, relation_type)
);

CREATE TABLE IF NOT EXISTS feature_history (
  id INTEGER PRIMARY KEY,
  feature_id INTEGER NOT NULL,
  lineage_key TEXT NOT NULL,
  name TEXT NOT NULL,
  capability_key TEXT NOT NULL,
  category TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('active', 'deprecated', 'experimental')),
  version INTEGER NOT NULL CHECK (version >= 1),
  description TEXT NOT NULL,
  score_performance INTEGER NOT NULL DEFAULT 0,
  score_security INTEGER NOT NULL DEFAULT 0,
  score_complexity INTEGER NOT NULL DEFAULT 0,
  score_total INTEGER NOT NULL,
  ingestion_record_id INTEGER,
  reason TEXT,
  snapshot_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
  FOREIGN KEY (feature_id) REFERENCES features(id) ON DELETE RESTRICT,
  FOREIGN KEY (ingestion_record_id) REFERENCES ingestion_records(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS decision_cache (
  id INTEGER PRIMARY KEY,
  cache_key TEXT NOT NULL UNIQUE,
  project_fingerprint TEXT NOT NULL,
  category_filter TEXT,
  context_profile TEXT NOT NULL,
  result_payload TEXT NOT NULL,
  hit_count INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
  updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_features_capability_key ON features(capability_key);
CREATE INDEX IF NOT EXISTS idx_features_category_status ON features(category, status);
CREATE INDEX IF NOT EXISTS idx_features_status ON features(status);
CREATE INDEX IF NOT EXISTS idx_features_source_ref ON features(source_ref);

CREATE INDEX IF NOT EXISTS idx_feature_candidates_ingestion_status
  ON feature_candidates(ingestion_record_id, candidate_status);
CREATE INDEX IF NOT EXISTS idx_feature_candidates_capability_score
  ON feature_candidates(capability_key, score_total DESC);
CREATE INDEX IF NOT EXISTS idx_feature_candidates_reusable
  ON feature_candidates(reusable_across_projects, reusable_score DESC);

CREATE INDEX IF NOT EXISTS idx_feature_scores_total ON feature_scores(score_total DESC);
CREATE INDEX IF NOT EXISTS idx_feature_scores_model_total ON feature_scores(score_model, score_total DESC);
CREATE INDEX IF NOT EXISTS idx_feature_embeddings_model ON feature_embeddings(model);

CREATE INDEX IF NOT EXISTS idx_feature_relations_from_type ON feature_relations(from_feature_id, relation_type);
CREATE INDEX IF NOT EXISTS idx_feature_relations_to_type ON feature_relations(to_feature_id, relation_type);

CREATE INDEX IF NOT EXISTS idx_feature_history_lineage_version ON feature_history(lineage_key, version DESC);
CREATE INDEX IF NOT EXISTS idx_feature_history_feature_snapshot ON feature_history(feature_id, snapshot_at DESC);

CREATE INDEX IF NOT EXISTS idx_ingestion_records_source_path ON ingestion_records(source_path);
CREATE INDEX IF NOT EXISTS idx_ingestion_records_cleanup_result ON ingestion_records(cleanup_result);
CREATE INDEX IF NOT EXISTS idx_decision_cache_fingerprint ON decision_cache(project_fingerprint);

CREATE UNIQUE INDEX IF NOT EXISTS ux_features_active_capability
  ON features(capability_key)
  WHERE status = 'active';

CREATE UNIQUE INDEX IF NOT EXISTS ux_features_lineage_version
  ON features(capability_key, version);

CREATE TRIGGER IF NOT EXISTS trg_features_touch_updated_at
AFTER UPDATE ON features
FOR EACH ROW
BEGIN
  UPDATE features
  SET updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
  WHERE id = OLD.id;
END;

CREATE TRIGGER IF NOT EXISTS trg_feature_candidates_touch_updated_at
AFTER UPDATE ON feature_candidates
FOR EACH ROW
BEGIN
  UPDATE feature_candidates
  SET updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
  WHERE id = OLD.id;
END;

CREATE TRIGGER IF NOT EXISTS trg_ingestion_records_touch_updated_at
AFTER UPDATE ON ingestion_records
FOR EACH ROW
BEGIN
  UPDATE ingestion_records
  SET updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
  WHERE id = OLD.id;
END;

CREATE TRIGGER IF NOT EXISTS trg_decision_cache_touch_updated_at
AFTER UPDATE ON decision_cache
FOR EACH ROW
BEGIN
  UPDATE decision_cache
  SET updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
  WHERE id = OLD.id;
END;

CREATE TRIGGER IF NOT EXISTS trg_feature_history_no_update
BEFORE UPDATE ON feature_history
BEGIN
  SELECT RAISE(ABORT, 'feature_history is append-only');
END;

CREATE TRIGGER IF NOT EXISTS trg_feature_history_no_delete
BEFORE DELETE ON feature_history
BEGIN
  SELECT RAISE(ABORT, 'feature_history is append-only');
END;

CREATE VIEW IF NOT EXISTS active_feature_best_scores AS
SELECT
  f.id,
  f.name,
  f.capability_key,
  f.category,
  f.status,
  f.version,
  s.performance,
  s.security,
  s.complexity,
  s.score_total
FROM features f
JOIN feature_scores s ON s.feature_id = f.id
WHERE f.status = 'active';

COMMIT;
