# Architecture Intelligence Engine Contract (V1.1)

## Scope
This contract binds extraction, reusability gate, conflict resolution, lifecycle/versioning, dependency composability, improvement planning, scoring, and cleanup safety to SQLite persistence plus runtime write-path guards.

## Decision Rules -> DB + Runtime Guarantees

### 1. Lifecycle
- Allowed statuses: `active`, `deprecated`, `experimental`.
- Enforced by `features.status` check.
- One active feature per capability lineage via partial unique index:
  - `ux_features_active_capability` on `features(capability_key) WHERE status='active'`.

### 2. Candidate Extraction + Normalization
- Candidates persisted in `feature_candidates` with unique `(ingestion_record_id, capability_key)`.
- Extraction accepts code and non-code sources (design/docs) but output must be normalized feature records, never raw artifacts.
- Normalized fields: dot-notation `name`, canonical `capability_key`, deterministic scores, inferred dependencies.

### 3. Reusability Gate (mandatory)
- Candidate must pass `reusable_across_projects=1` before active promotion.
- Candidate reusability fields persisted:
  - `reusable_score` (0..10)
  - `reusable_across_projects` (0/1)
  - `reusable_reason`
- Failed candidates are blocked from active path and marked `discarded`/`experimental` with auditable reason.

### 4. Conflict Resolution
- Resolver decisions are fixed vocabulary:
  - `replace`
  - `merge_variant`
  - `keep_old`
- Decision logic:
  - `replace` if `score_diff >= threshold_replace`
  - `merge_variant` if `abs(score_diff) <= threshold_merge`
  - `keep_old` otherwise
- Defaults:
  - `threshold_replace = 3`
  - `threshold_merge = 1`

### 5. Replace / Merge / Keep Behavior
- `replace`:
  - snapshot old active to `feature_history`
  - old active -> `deprecated`
  - new feature -> `active`
  - relations `replaces` + `replaced_by` stored.
- `merge_variant`:
  - candidate becomes `experimental` variant
  - relation `variant` stored
  - no second active on original capability key.
- `keep_old`:
  - active unchanged
  - candidate marked `experimental` or `discarded` for traceability.

### 6. Versioning
- Version must be `>= 1`.
- `(capability_key, version)` unique.
- Replacement guard enforces monotonic step:
  - `new.version = old.version + 1`
  - reject if lineage already advanced (`max_version > old.version`).

### 7. Dependency / Composability
- Allowed dependency relation uses `feature_relations.relation_type='depends_on'`.
- Resolver may promote active even if prerequisite missing, but unresolved dependencies must be persisted for planner reporting.
- Self-dependency and duplicate edges are blocked by schema constraints + runtime guard.

### 8. Scoring
- Dimensions: `performance`, `security`, `complexity`.
- Canonical total: `performance + security - complexity` (generated column in DB).
- Default query ranks active features by `score_total DESC`.

### 9. Improvement Planner Contract
- Runtime capability: `improve(project_path, category_filter=None)`.
- Output is JSON-first and must include:
  - `summary`
  - `project_path`
  - `detected_gaps`
  - `recommendations[]`
- Each recommendation must include:
  - `feature`
  - `category`
  - `reason`
  - `priority`
  - `integration_points`
  - `missing_dependencies`

### 10. History Append-Only
- `feature_history` immutable after insert.
- Enforced by triggers:
  - `trg_feature_history_no_update`
  - `trg_feature_history_no_delete`


### 12. Decision Cache + Context Profiling
- Retrieval mode `retrieval` uses local `feature_embeddings` token similarity for semantic candidate selection.
- Hybrid mode escalates from direct to retrieval when recommendation confidence is below threshold.
- Candidate extraction includes reader normalization for non-code text inputs (md/txt/html/json/yaml) before feature classification.
- Improvement candidate selection applies context-aware reranking on top of base score ordering.
- Improvement flow must build `context_profile` (`size`, `type`, `priorities`) before recommendation selection.
- Improvement output includes `cache_hit` and `context_profile`.
- Cache key is derived from project fingerprint + observed categories + category filter + context profile.
- Cached payload is valid only for the same cache key; otherwise recompute and upsert.

### 11. Cleanup Safety
- Ingestion classification enum:
  - `runtime-linked`
  - `non-operational`
  - `standalone-reference`
- Default delete policy:
  - only `non-operational` + `cleanup_decision=delete` can auto-delete.
- `runtime-linked` cannot auto-delete in default path.
- Cleanup execution must persist mode/result/timestamp/error in `ingestion_records`.

## Default Query Contract
- Recommendation reads use active features by default.
- Deprecated/experimental excluded unless explicitly requested.
- DB remains source of truth in V1.1; catalog/export layer is optional and non-authoritative.


## Retrieval Intelligence Lane (Planned, Post-V1.1)

To evolve from rule-centric selection into retrieval-centric selection, the next lane is:

1. Embedding search layer for semantic candidate retrieval (not keyword-only).
2. Reranker layer to choose best candidate per project context profile.
3. Reader/normalization layer for non-code inputs (docs/web) before extraction.
4. Iterative search loop when confidence is low (`search -> rerank -> refine`).

Guardrails:
- Keep DB as source of truth.
- Add retrieval layers incrementally behind feature flags.
- Preserve existing lifecycle/versioning constraints.

## Self-Improvement Loop Lane (V1.2 Target)

This lane formalizes recursive improvement as deterministic architecture decisions, not model desire/intention.

### 1. Evaluation Profile (mandatory)
- Engine must define `evaluation_profile` before generating variants:
  - `tasks`: at least one from `coding|reasoning|planning`
  - `metrics`: include `accuracy|success_rate|cost` (speed optional)
  - `baseline_source`: benchmark or historical run id
- Promotion decisions are invalid without evaluation evidence.

### 2. Weakness Detection Contract
- Each cycle must emit explicit weaknesses from evaluation deltas.
- Weakness output must be bounded, actionable, and mapped to candidate capability categories.

### 3. Variant Policy
- Runtime must generate change candidates as explicit variants (no direct overwrite).
- Variant payload must include:
  - `change_set`
  - `target_capability_key`
  - `risk_level`
  - `expected_metric_gain`

### 4. Selection Policy (promote/revert)
- Candidate variant must pass selection gate:
  - metric gain above configured threshold
  - no lifecycle invariant violation
  - no reusability gate regression
- If gate fails, variant remains non-active and is marked rejected/experimental.
- If gate passes, apply standard replace flow with history snapshot and version increment.

### 5. Meta-Learning Memory Rule
- Only action-verified outcomes are persisted as improvement lessons.
- Inference-only or unexecuted hypotheses are not allowed as durable memory.

### 6. Agent Feature Taxonomy
- Self-improvement target must be represented as reusable architecture features, e.g.:
  - `agent.reasoning.chain`
  - `agent.memory.long_term`
  - `agent.planning.multi_step`
- Raw prompts/notes are intermediate artifacts; normalized feature records remain the only runtime authority.
