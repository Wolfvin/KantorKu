BEGIN;

CREATE TABLE IF NOT EXISTS feature_embeddings (
  feature_id INTEGER PRIMARY KEY,
  embedding_tokens TEXT NOT NULL,
  model TEXT NOT NULL DEFAULT 'lite-token-v1',
  updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
  FOREIGN KEY (feature_id) REFERENCES features(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_feature_embeddings_model ON feature_embeddings(model);

COMMIT;
