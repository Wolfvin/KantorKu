BEGIN;

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

CREATE INDEX IF NOT EXISTS idx_decision_cache_fingerprint ON decision_cache(project_fingerprint);

CREATE TRIGGER IF NOT EXISTS trg_decision_cache_touch_updated_at
AFTER UPDATE ON decision_cache
FOR EACH ROW
BEGIN
  UPDATE decision_cache
  SET updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
  WHERE id = OLD.id;
END;

COMMIT;
