#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parent
SRC_ROOT = APP_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from arch_engine.db import DB_PATH, init_db
from arch_engine.repository import ArchEngineRepository


def _repo(db_path: str | None) -> ArchEngineRepository:
    return ArchEngineRepository(Path(db_path).resolve() if db_path else DB_PATH)


def cmd_init(args: argparse.Namespace) -> int:
    db_path = Path(args.db_path).resolve() if args.db_path else DB_PATH
    path = init_db(db_path)
    print(json.dumps({"status": "ok", "db_path": str(path)}, indent=2))
    return 0


def cmd_ingest(args: argparse.Namespace) -> int:
    repo = _repo(args.db_path)
    result = repo.ingest_source(
        Path(args.source),
        dry_run=args.dry_run,
        apply_candidates=args.apply_candidates,
    )
    print(json.dumps(result.__dict__, indent=2))
    return 0


def cmd_resolve(args: argparse.Namespace) -> int:
    repo = _repo(args.db_path)
    result = repo.resolve(
        threshold_replace=args.threshold_replace,
        threshold_merge=args.threshold_merge,
        ingestion_id=args.ingestion_id,
    )
    print(json.dumps(result, indent=2))
    return 0


def cmd_query(args: argparse.Namespace) -> int:
    repo = _repo(args.db_path)
    rows = repo.query_best(category=args.category, include_deprecated=args.include_deprecated)
    print(json.dumps({"count": len(rows), "items": rows}, indent=2))
    return 0


def cmd_improve(args: argparse.Namespace) -> int:
    repo = _repo(args.db_path)
    result = repo.improve(
        project_path=Path(args.project_path),
        category_filter=args.category,
        retrieval_mode=args.retrieval_mode,
        min_confidence=args.min_confidence,
    )
    print(json.dumps(result, indent=2))
    return 0


def cmd_cleanup(args: argparse.Namespace) -> int:
    repo = _repo(args.db_path)
    result = repo.cleanup(ingestion_id=args.ingestion_id, apply=args.apply, force=args.force)
    print(json.dumps(result, indent=2))
    if result.get("result") == "failed":
        return 1
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="arch-engine", description="Architecture Intelligence Engine CLI")
    p.add_argument("--db-path", help="Override SQLite DB path")

    sub = p.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser("init", help="Initialize SQLite schema")
    p_init.set_defaults(func=cmd_init)

    p_ingest = sub.add_parser("ingest", help="Ingest source and optionally persist candidates")
    p_ingest.add_argument("--source", required=True, help="Source folder path")
    p_ingest.add_argument("--dry-run", action="store_true", help="Record ingest without destructive cleanup")
    p_ingest.add_argument(
        "--apply-candidates",
        action="store_true",
        help="Persist extracted candidates into feature_candidates",
    )
    p_ingest.set_defaults(func=cmd_ingest)

    p_resolve = sub.add_parser("resolve", help="Run conflict resolver over pending candidates")
    p_resolve.add_argument("--threshold-replace", type=int, default=3, help="score_diff threshold for replace")
    p_resolve.add_argument("--threshold-merge", type=int, default=1, help="abs(score_diff) threshold for merge")
    p_resolve.add_argument("--ingestion-id", type=int, help="Restrict resolving to one ingestion record")
    p_resolve.set_defaults(func=cmd_resolve)

    p_query = sub.add_parser("query", help="Query features ranked by score")
    p_query.add_argument("--category", help="Optional category filter")
    p_query.add_argument("--include-deprecated", action="store_true", help="Include deprecated/experimental rows")
    p_query.set_defaults(func=cmd_query)

    p_improve = sub.add_parser("improve", help="Generate improvement plan from active architecture features")
    p_improve.add_argument("--project-path", required=True, help="Target project path to analyze")
    p_improve.add_argument("--category", help="Optional category focus")
    p_improve.add_argument(
        "--retrieval-mode",
        choices=["direct", "hybrid", "retrieval"],
        default="hybrid",
        help="Recommendation strategy: fast direct, forced retrieval, or hybrid escalation",
    )
    p_improve.add_argument(
        "--min-confidence",
        type=float,
        default=0.6,
        help="Hybrid mode escalation threshold (0.0-1.0)",
    )
    p_improve.set_defaults(func=cmd_improve)

    p_cleanup = sub.add_parser("cleanup", help="Run cleanup policy for one ingestion record")
    p_cleanup.add_argument("--ingestion-id", required=True, type=int)
    p_cleanup.add_argument("--apply", action="store_true", help="Apply cleanup. Default is dry-run")
    p_cleanup.add_argument("--force", action="store_true", help="Allow forced-delete except runtime-linked sources")
    p_cleanup.set_defaults(func=cmd_cleanup)

    return p


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
