# Architecture Intelligence Engine (V1.1)

Backend-first decision engine for architecture feature extraction, reusability gating, conflict resolution, dependency linking, improvement planning, and safe cleanup.

## Current Scope
- SQLite schema + migration runner (`schema_migrations`)
- Candidate extraction pipeline (`evolve.extract`) with deterministic heuristic scoring
- Reusability gate (`reusable_score`, `reusable_across_projects`, rejection reason)
- Conflict resolver with decisions: `replace | merge_variant | keep_old`
- Dependency/composability support via `depends_on` relations
- Improvement planner (`improve`) with JSON recommendations + decision cache/context profile
- Lifecycle/versioning transitions with history snapshots
- Cleanup command with policy enforcement (`delete` default only for `non-operational`)
- Query endpoint for best active features (deprecated excluded by default)

## Run

```bash
python3 .codex/apps/arch-engine/cli.py init
python3 .codex/apps/arch-engine/cli.py ingest --source .codex --dry-run --apply-candidates
python3 .codex/apps/arch-engine/cli.py resolve --threshold-replace 3 --threshold-merge 1
python3 .codex/apps/arch-engine/cli.py query
python3 .codex/apps/arch-engine/cli.py improve --project-path . --retrieval-mode hybrid --min-confidence 0.6
python3 .codex/apps/arch-engine/cli.py cleanup --ingestion-id 1
```

## Test

```bash
PYTHONPATH=.codex/apps/arch-engine/src python3 -m unittest discover -s .codex/apps/arch-engine/tests -v
```

## CLI Surface
- `init`
- `ingest --source ... [--dry-run] [--apply-candidates]`
- `resolve [--threshold-replace N] [--threshold-merge N] [--ingestion-id ID]`
- `query [--category ...] [--include-deprecated]`
- `improve --project-path ... [--category ...] [--retrieval-mode direct|hybrid|retrieval] [--min-confidence N]`
- `cleanup --ingestion-id ID [--apply] [--force]`

All commands return structured JSON output for agent integration.

`improve` response now includes `cache_hit` and `context_profile`.

## Notes
- Scoring and reusability are deterministic heuristic only (no LLM dependency).
- `score_total` is computed by DB: `performance + security - complexity`.
- `keep_old` and failed reusability candidates remain traceable through candidate state.
- DB is the only runtime source of truth in v1.1.
- Retrieval mode now supports lightweight local semantic matching via `feature_embeddings` (token-based).

## Next Lane (V1.2)
- Add deterministic self-improvement loop:
  - `evaluate -> detect_weakness -> generate_variant -> test -> promote_or_revert`
- Keep promotion evidence-based through evaluation profile and selection gate.
- Keep lifecycle/reusability invariants unchanged while evolving agent-oriented capabilities.
