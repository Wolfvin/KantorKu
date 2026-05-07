from __future__ import annotations

import hashlib
import json
import re
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .db import DB_PATH, get_connection

WORD_RE = re.compile(r"[a-z0-9]+")
HTML_TAG_RE = re.compile(r"<[^>]+>")
IGNORED_SUFFIXES = {".pyc", ".db", ".sqlite", ".sqlite3"}
IGNORED_NAMES = {".gitkeep"}
IGNORED_PARTS = {"__pycache__", ".git"}

CATEGORY_RULES: list[tuple[str, tuple[str, ...]]] = [
    ("security", ("auth", "security", "token", "jwt", "encrypt", "acl", "permission")),
    ("network", ("network", "socket", "http", "https", "dns", "proxy", "gateway")),
    ("storage", ("storage", "database", "db", "sqlite", "postgres", "redis", "cache")),
    ("api", ("api", "endpoint", "route", "rest", "graphql", "controller")),
    ("design", ("design", "ui", "ux", "theme", "layout", "css", "html")),
    ("runtime", ("runtime", "executor", "worker", "queue", "scheduler", "process")),
    ("tooling", ("script", "tool", "cli", "build", "lint", "test", "ci")),
]

BASE_SCORES: dict[str, tuple[int, int, int]] = {
    "security": (6, 8, 4),
    "network": (7, 5, 5),
    "storage": (7, 6, 5),
    "api": (6, 5, 4),
    "design": (5, 4, 4),
    "runtime": (8, 6, 6),
    "tooling": (6, 4, 3),
    "general": (5, 5, 4),
}

CATEGORY_DEPENDENCIES: dict[str, list[str]] = {
    "api": ["security", "network"],
    "runtime": ["storage"],
    "design": ["api"],
    "tooling": ["runtime"],
}

CATEGORY_INTEGRATION_POINTS: dict[str, list[str]] = {
    "security": ["middleware", "auth module", "access policy layer"],
    "network": ["transport adapter", "gateway/proxy config"],
    "storage": ["repository layer", "persistence config"],
    "api": ["route/controller layer", "public interface boundary"],
    "design": ["UI theme layer", "component styling entrypoint"],
    "runtime": ["executor/bootstrap flow", "background worker registration"],
    "tooling": ["build/test pipeline", "developer scripts"],
    "general": ["core module boundary"],
}


@dataclass
class ResolverThresholds:
    threshold_replace: int = 3
    threshold_merge: int = 1


@dataclass
class CandidateFeature:
    ingestion_record_id: int
    name: str
    capability_key: str
    category: str
    description: str
    source_ref: str
    fingerprint: str
    performance: int
    security: int
    complexity: int
    reusable_score: int
    reusable_across_projects: bool
    reusable_reason: str
    inferred_dependencies: list[str]

    @property
    def score_total(self) -> int:
        return self.performance + self.security - self.complexity


@dataclass
class ResolverDecision:
    candidate_id: int
    capability_key: str
    decision: str
    old_feature_id: int | None
    new_feature_id: int | None
    score_diff: int | None


@dataclass
class LifecycleTransition:
    action: str
    old_status: str | None
    new_status: str
    old_version: int | None
    new_version: int | None


@dataclass
class IngestResult:
    ingestion_id: int
    source_path: str
    source_type: str
    dry_run: bool
    cleanup_decision: str
    extraction_summary: dict[str, Any]
    candidates: list[dict[str, Any]]


class ArchEngineRepository:
    def __init__(self, db_path: Path | None = None) -> None:
        self.db_path = db_path or DB_PATH

    def classify_source(self, source_path: Path) -> str:
        normalized = str(source_path).lower()
        if "/.codex/archive" in normalized or "/.tmp" in normalized:
            return "non-operational"
        if "standalone" in normalized:
            return "standalone-reference"
        return "runtime-linked"

    def ingest_source(self, source_path: Path, dry_run: bool = True, apply_candidates: bool = False) -> IngestResult:
        source_path = source_path.resolve()
        source_type = self.classify_source(source_path)
        cleanup_decision = "delete" if source_type == "non-operational" else "keep"

        files = [p for p in source_path.rglob("*") if p.is_file()] if source_path.exists() else []
        candidates = self._extract_candidates(source_path, files)

        extraction_summary = {
            "file_count": len(files),
            "candidate_count": len(candidates),
            "exists": source_path.exists(),
            "applied_candidates": bool(apply_candidates),
            "scoring_mode": "heuristic-deterministic-v1",
        }

        with get_connection(self.db_path) as conn:
            cur = conn.execute(
                """
                INSERT INTO ingestion_records (
                    source_path, source_type, dry_run, cleanup_decision,
                    cleanup_mode, cleanup_requested, extraction_summary, cleanup_result
                ) VALUES (?, ?, ?, ?, 'default', 0, ?, 'pending')
                """,
                (
                    str(source_path),
                    source_type,
                    1 if dry_run else 0,
                    cleanup_decision,
                    json.dumps(extraction_summary, ensure_ascii=True),
                ),
            )
            ingestion_id = int(cur.lastrowid)

            if apply_candidates:
                self._upsert_candidates(conn, ingestion_id, candidates)
            conn.commit()

        result_candidates: list[dict[str, Any]] = []
        for c in candidates:
            payload = asdict(c)
            payload["ingestion_record_id"] = ingestion_id
            result_candidates.append(payload)

        return IngestResult(
            ingestion_id=ingestion_id,
            source_path=str(source_path),
            source_type=source_type,
            dry_run=dry_run,
            cleanup_decision=cleanup_decision,
            extraction_summary=extraction_summary,
            candidates=result_candidates,
        )

    def resolve(
        self,
        threshold_replace: int = 3,
        threshold_merge: int = 1,
        ingestion_id: int | None = None,
    ) -> dict[str, Any]:
        thresholds = ResolverThresholds(threshold_replace=threshold_replace, threshold_merge=threshold_merge)
        decisions: list[ResolverDecision] = []
        transitions: list[LifecycleTransition] = []
        rejection_reasons: dict[str, int] = {}
        accepted = 0
        rejected = 0

        with get_connection(self.db_path) as conn:
            sql = """
                SELECT * FROM feature_candidates
                WHERE candidate_status = 'candidate'
            """
            params: tuple[Any, ...] = ()
            if ingestion_id is not None:
                sql += " AND ingestion_record_id = ?"
                params = (ingestion_id,)
            sql += " ORDER BY id ASC"

            rows = conn.execute(sql, params).fetchall()

            for row in rows:
                if int(row["reusable_across_projects"]) != 1:
                    reason = row["reusable_reason"] or "failed_reusability_gate"
                    rejection_reasons[reason] = rejection_reasons.get(reason, 0) + 1
                    rejected += 1
                    conn.execute(
                        """
                        UPDATE feature_candidates
                        SET candidate_status='discarded', resolver_decision='keep_old',
                            unresolved_dependencies=COALESCE(unresolved_dependencies, '[]')
                        WHERE id=?
                        """,
                        (row["id"],),
                    )
                    decisions.append(
                        ResolverDecision(
                            candidate_id=row["id"],
                            capability_key=row["capability_key"],
                            decision="keep_old",
                            old_feature_id=None,
                            new_feature_id=None,
                            score_diff=None,
                        )
                    )
                    continue

                old = conn.execute(
                    """
                    SELECT f.*, s.performance, s.security, s.complexity, s.score_total
                    FROM features f
                    JOIN feature_scores s ON s.feature_id = f.id
                    WHERE f.capability_key = ? AND f.status = 'active'
                    LIMIT 1
                    """,
                    (row["capability_key"],),
                ).fetchone()

                inferred_dependencies = self._decode_json_list(row["inferred_dependencies"])
                unresolved_dependencies: list[str] = []

                if old is None:
                    new_id = self._insert_feature_with_score(
                        conn,
                        name=row["name"],
                        capability_key=row["capability_key"],
                        category=row["category"],
                        description=row["description"],
                        status="active",
                        version=1,
                        source_ref=row["source_ref"],
                        ingestion_record_id=row["ingestion_record_id"],
                        performance=row["performance"],
                        security=row["security"],
                        complexity=row["complexity"],
                    )
                    unresolved_dependencies = self._persist_dependency_edges(conn, new_id, inferred_dependencies)
                    conn.execute(
                        """
                        UPDATE feature_candidates
                        SET candidate_status='resolved', resolver_decision='replace', resolved_feature_id=?,
                            unresolved_dependencies=?
                        WHERE id=?
                        """,
                        (new_id, json.dumps(unresolved_dependencies, ensure_ascii=True), row["id"]),
                    )
                    decisions.append(
                        ResolverDecision(
                            candidate_id=row["id"],
                            capability_key=row["capability_key"],
                            decision="replace",
                            old_feature_id=None,
                            new_feature_id=new_id,
                            score_diff=None,
                        )
                    )
                    transitions.append(
                        LifecycleTransition(
                            action="activate_new",
                            old_status=None,
                            new_status="active",
                            old_version=None,
                            new_version=1,
                        )
                    )
                    accepted += 1
                    continue

                score_diff = row["score_total"] - old["score_total"]
                decision = self._resolve_decision(score_diff, thresholds)

                if decision == "replace":
                    old_version = int(old["version"])
                    new_version = old_version + 1
                    self._assert_next_version(conn, row["capability_key"], old_version, new_version)
                    self._snapshot_feature(conn, old_feature=old, reason=f"replaced_by_candidate:{row['id']}")

                    conn.execute("UPDATE features SET status='deprecated' WHERE id=?", (old["id"],))

                    new_id = self._insert_feature_with_score(
                        conn,
                        name=row["name"],
                        capability_key=row["capability_key"],
                        category=row["category"],
                        description=row["description"],
                        status="active",
                        version=new_version,
                        source_ref=row["source_ref"],
                        ingestion_record_id=row["ingestion_record_id"],
                        performance=row["performance"],
                        security=row["security"],
                        complexity=row["complexity"],
                    )
                    unresolved_dependencies = self._persist_dependency_edges(conn, new_id, inferred_dependencies)

                    conn.executemany(
                        """
                        INSERT INTO feature_relations (from_feature_id, to_feature_id, relation_type)
                        VALUES (?, ?, ?)
                        """,
                        [
                            (new_id, old["id"], "replaces"),
                            (old["id"], new_id, "replaced_by"),
                        ],
                    )

                    conn.execute(
                        """
                        UPDATE feature_candidates
                        SET candidate_status='resolved', resolver_decision='replace', resolved_feature_id=?,
                            unresolved_dependencies=?
                        WHERE id=?
                        """,
                        (new_id, json.dumps(unresolved_dependencies, ensure_ascii=True), row["id"]),
                    )
                    decisions.append(
                        ResolverDecision(
                            candidate_id=row["id"],
                            capability_key=row["capability_key"],
                            decision="replace",
                            old_feature_id=old["id"],
                            new_feature_id=new_id,
                            score_diff=score_diff,
                        )
                    )
                    transitions.append(
                        LifecycleTransition(
                            action="replace",
                            old_status="active",
                            new_status="active",
                            old_version=old_version,
                            new_version=new_version,
                        )
                    )
                    accepted += 1

                elif decision == "merge_variant":
                    variant_key = f"{old['capability_key']}.variant"
                    next_variant_version = self._next_version(conn, variant_key)
                    variant_name = self._ensure_unique_name(conn, f"{row['name']}.variant")
                    variant_id = self._insert_feature_with_score(
                        conn,
                        name=variant_name,
                        capability_key=variant_key,
                        category=row["category"],
                        description=f"Variant of {old['name']}: {row['description']}",
                        status="experimental",
                        version=next_variant_version,
                        source_ref=row["source_ref"],
                        ingestion_record_id=row["ingestion_record_id"],
                        performance=row["performance"],
                        security=row["security"],
                        complexity=row["complexity"],
                    )
                    unresolved_dependencies = self._persist_dependency_edges(conn, variant_id, inferred_dependencies)
                    conn.execute(
                        """
                        INSERT INTO feature_relations (from_feature_id, to_feature_id, relation_type)
                        VALUES (?, ?, 'variant')
                        """,
                        (old["id"], variant_id),
                    )
                    conn.execute(
                        """
                        UPDATE feature_candidates
                        SET candidate_status='merged_variant', resolver_decision='merge_variant', resolved_feature_id=?,
                            unresolved_dependencies=?
                        WHERE id=?
                        """,
                        (variant_id, json.dumps(unresolved_dependencies, ensure_ascii=True), row["id"]),
                    )
                    decisions.append(
                        ResolverDecision(
                            candidate_id=row["id"],
                            capability_key=row["capability_key"],
                            decision="merge_variant",
                            old_feature_id=old["id"],
                            new_feature_id=variant_id,
                            score_diff=score_diff,
                        )
                    )
                    transitions.append(
                        LifecycleTransition(
                            action="merge_variant",
                            old_status="active",
                            new_status="experimental",
                            old_version=int(old["version"]),
                            new_version=next_variant_version,
                        )
                    )
                    accepted += 1

                else:
                    conn.execute(
                        """
                        UPDATE feature_candidates
                        SET candidate_status='experimental', resolver_decision='keep_old', resolved_feature_id=NULL,
                            unresolved_dependencies=?
                        WHERE id=?
                        """,
                        (json.dumps(inferred_dependencies, ensure_ascii=True), row["id"]),
                    )
                    decisions.append(
                        ResolverDecision(
                            candidate_id=row["id"],
                            capability_key=row["capability_key"],
                            decision="keep_old",
                            old_feature_id=old["id"],
                            new_feature_id=None,
                            score_diff=score_diff,
                        )
                    )
                    transitions.append(
                        LifecycleTransition(
                            action="keep_old",
                            old_status="active",
                            new_status="experimental",
                            old_version=int(old["version"]),
                            new_version=None,
                        )
                    )
                    rejected += 1

            conn.commit()

        decision_counts: dict[str, int] = {}
        for item in decisions:
            decision_counts[item.decision] = decision_counts.get(item.decision, 0) + 1

        return {
            "status": "ok",
            "thresholds": asdict(thresholds),
            "ingestion_id": ingestion_id,
            "processed": len(decisions),
            "decision_counts": decision_counts,
            "reusability_gate": {
                "accepted": accepted,
                "rejected": rejected,
                "reasons": rejection_reasons,
            },
            "decisions": [asdict(d) for d in decisions],
            "transitions": [asdict(t) for t in transitions],
        }

    def improve(
        self,
        project_path: Path,
        category_filter: str | None = None,
        retrieval_mode: str = "hybrid",
        min_confidence: float = 0.6,
    ) -> dict[str, Any]:
        project_path = project_path.resolve()
        files = [p for p in project_path.rglob("*") if p.is_file()] if project_path.exists() else []
        observed_categories: set[str] = set()

        for path in files:
            if self._is_noise_file(path):
                continue
            tokens = self._tokenize_path(path.relative_to(project_path))
            if not tokens:
                continue
            observed_categories.add(self._classify_category(tokens))

        context_profile = self._build_context_profile(files, observed_categories)
        cache_key = self._build_decision_cache_key(
            project_path=project_path,
            files=files,
            observed_categories=observed_categories,
            category_filter=category_filter,
            context_profile=context_profile,
        )
        cache_key = hashlib.sha1(f"{cache_key}|{retrieval_mode}|{min_confidence:.2f}".encode("utf-8")).hexdigest()

        if category_filter:
            target_categories = [category_filter]
        else:
            target_categories = ["security", "network", "storage", "api", "design", "runtime", "tooling"]

        missing_categories = [c for c in target_categories if c not in observed_categories]
        recommendations: list[dict[str, Any]] = []

        with get_connection(self.db_path) as conn:
            cached = conn.execute(
                "SELECT id, result_payload FROM decision_cache WHERE cache_key = ?",
                (cache_key,),
            ).fetchone()
            if cached is not None:
                conn.execute(
                    "UPDATE decision_cache SET hit_count = hit_count + 1 WHERE id = ?",
                    (cached["id"],),
                )
                conn.commit()
                payload = json.loads(cached["result_payload"])
                payload["cache_hit"] = True
                return payload

            active_rows = conn.execute(
                """
                SELECT f.id, f.name, f.capability_key, f.category, f.description,
                       s.performance, s.security, s.complexity, s.score_total
                FROM features f
                JOIN feature_scores s ON s.feature_id = f.id
                WHERE f.status = 'active'
                ORDER BY s.score_total DESC
                """
            ).fetchall()

            by_category: dict[str, list[Any]] = {}
            for row in active_rows:
                by_category.setdefault(row["category"], []).append(row)
            for category, rows in list(by_category.items()):
                by_category[category] = self._rerank_features(rows, context_profile)

            for category in missing_categories:
                picks = by_category.get(category, [])
                if not picks:
                    continue
                best = picks[0]
                dep_categories = CATEGORY_DEPENDENCIES.get(category, [])
                missing_deps = [dc for dc in dep_categories if dc not in observed_categories]
                priority = "high" if category in {"security", "api", "storage"} else "medium"
                confidence = self._recommendation_confidence(
                    missing_deps_count=len(missing_deps),
                    context_profile=context_profile,
                    retrieval_mode=retrieval_mode,
                )
                use_retrieval = retrieval_mode == "retrieval" or (
                    retrieval_mode == "hybrid" and confidence < min_confidence
                )
                semantic_score = None
                if use_retrieval:
                    query_tokens = self._retrieval_query_tokens(category, context_profile, missing_deps)
                    best, semantic_score = self._semantic_best_feature(conn, picks, query_tokens)
                recommendations.append(
                    {
                        "feature": best["name"],
                        "category": category,
                        "reason": (
                            f"Category '{category}' is missing in project signals and reranked best feature was "
                            f"selected for context size='{context_profile['size']}' type='{context_profile['type']}'."
                        ),
                        "priority": priority,
                        "confidence": round(confidence, 3),
                        "selection_mode": "retrieval_rerank" if use_retrieval else "direct_search",
                        "semantic_score": round(semantic_score, 3) if semantic_score is not None else None,
                        "integration_points": CATEGORY_INTEGRATION_POINTS.get(category, CATEGORY_INTEGRATION_POINTS["general"]),
                        "missing_dependencies": missing_deps,
                    }
                )

            for category in target_categories:
                for row in by_category.get(category, [])[:1]:
                    dep_categories = CATEGORY_DEPENDENCIES.get(category, [])
                    unresolved = [dc for dc in dep_categories if dc not in observed_categories]
                    if not unresolved:
                        continue
                    already = any(r["feature"] == row["name"] for r in recommendations)
                    if already:
                        continue
                    confidence = self._recommendation_confidence(
                        missing_deps_count=len(unresolved),
                        context_profile=context_profile,
                        retrieval_mode=retrieval_mode,
                    )
                    use_retrieval = retrieval_mode == "retrieval" or (
                        retrieval_mode == "hybrid" and confidence < min_confidence
                    )
                    chosen = row
                    semantic_score = None
                    if use_retrieval:
                        query_tokens = self._retrieval_query_tokens(category, context_profile, unresolved)
                        chosen, semantic_score = self._semantic_best_feature(conn, by_category.get(category, []), query_tokens)
                    recommendations.append(
                        {
                            "feature": chosen["name"],
                            "category": category,
                            "reason": (
                                "Reranked feature remains strong in current context but project is missing "
                                "prerequisite capabilities."
                            ),
                            "priority": "medium",
                            "confidence": round(confidence, 3),
                            "selection_mode": "retrieval_rerank" if use_retrieval else "direct_search",
                            "semantic_score": round(semantic_score, 3) if semantic_score is not None else None,
                            "integration_points": CATEGORY_INTEGRATION_POINTS.get(category, CATEGORY_INTEGRATION_POINTS["general"]),
                            "missing_dependencies": unresolved,
                        }
                    )

        recommendations.sort(key=lambda x: (x["priority"] != "high", x["category"], x["feature"]))

        result = {
            "cache_hit": False,
            "summary": {
                "observed_categories": sorted(observed_categories),
                "missing_categories": missing_categories,
                "recommendation_count": len(recommendations),
            },
            "project_path": str(project_path),
            "context_profile": context_profile,
            "retrieval_mode": retrieval_mode,
            "min_confidence": min_confidence,
            "detected_gaps": {
                "category_gaps": missing_categories,
            },
            "recommendations": recommendations,
        }
        with get_connection(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO decision_cache (
                    cache_key, project_fingerprint, category_filter, context_profile, result_payload, hit_count
                ) VALUES (?, ?, ?, ?, ?, 0)
                ON CONFLICT (cache_key) DO UPDATE SET
                    result_payload=excluded.result_payload,
                    context_profile=excluded.context_profile,
                    category_filter=excluded.category_filter
                """,
                (
                    cache_key,
                    self._project_fingerprint(project_path, files),
                    category_filter,
                    json.dumps(context_profile, ensure_ascii=True),
                    json.dumps(result, ensure_ascii=True),
                ),
            )
            conn.commit()
        return result

    def query_best(self, category: str | None = None, include_deprecated: bool = False) -> list[dict[str, Any]]:
        if include_deprecated:
            sql = """
                SELECT f.id, f.name, f.capability_key, f.category, f.status, f.version,
                       s.performance, s.security, s.complexity, s.score_total
                FROM features f
                JOIN feature_scores s ON s.feature_id = f.id
            """
            params: tuple[Any, ...] = ()
            if category:
                sql += " WHERE f.category = ?"
                params = (category,)
            sql += " ORDER BY f.status='active' DESC, s.score_total DESC, f.name ASC"
        else:
            sql = """
                SELECT id, name, capability_key, category, status, version,
                       performance, security, complexity, score_total
                FROM active_feature_best_scores
            """
            params = ()
            if category:
                sql += " WHERE category = ?"
                params = (category,)
            sql += " ORDER BY score_total DESC, name ASC"

        with get_connection(self.db_path) as conn:
            rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

    def cleanup(self, ingestion_id: int, apply: bool = False, force: bool = False) -> dict[str, Any]:
        with get_connection(self.db_path) as conn:
            row = conn.execute("SELECT * FROM ingestion_records WHERE id = ?", (ingestion_id,)).fetchone()
            if row is None:
                raise ValueError(f"ingestion_id {ingestion_id} not found")

            source_path = Path(row["source_path"])
            source_type = row["source_type"]
            decision = row["cleanup_decision"]

            can_delete_default = source_type == "non-operational" and decision == "delete"
            can_delete = can_delete_default or (force and source_type != "runtime-linked")

            response: dict[str, Any] = {
                "ingestion_id": ingestion_id,
                "source_path": str(source_path),
                "source_type": source_type,
                "cleanup_decision": decision,
                "apply": apply,
                "force": force,
                "can_delete": can_delete,
                "exists": source_path.exists(),
            }

            if not apply:
                return response | {"status": "dry_run", "result": "pending"}

            cleanup_mode = "forced-delete" if force else "default"
            cleanup_requested = 1
            try:
                if can_delete and source_path.exists():
                    if source_path.is_dir():
                        shutil.rmtree(source_path)
                    else:
                        source_path.unlink()
                    result = "success"
                    error = None
                elif can_delete:
                    result = "success"
                    error = None
                else:
                    result = "skipped"
                    error = "default_policy_blocked_delete"

                conn.execute(
                    """
                    UPDATE ingestion_records
                    SET cleanup_mode=?, cleanup_requested=?, cleanup_result=?, cleanup_error=?,
                        cleanup_executed_at=strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
                    WHERE id=?
                    """,
                    (cleanup_mode, cleanup_requested, result, error, ingestion_id),
                )
                conn.commit()
                return response | {"status": "applied", "result": result, "error": error}
            except Exception as exc:
                conn.execute(
                    """
                    UPDATE ingestion_records
                    SET cleanup_mode=?, cleanup_requested=?, cleanup_result='failed', cleanup_error=?,
                        cleanup_executed_at=strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
                    WHERE id=?
                    """,
                    (cleanup_mode, cleanup_requested, str(exc), ingestion_id),
                )
                conn.commit()
                return response | {"status": "applied", "result": "failed", "error": str(exc)}

    def _extract_candidates(self, source_root: Path, files: list[Path]) -> list[CandidateFeature]:
        by_capability: dict[str, CandidateFeature] = {}
        synthetic_ingestion_id = -1

        for file_path in files:
            if self._is_noise_file(file_path):
                continue
            rel = file_path.relative_to(source_root)
            tokens = self._tokenize_path(rel) + self._reader_normalized_tokens(file_path)
            if not tokens:
                continue
            category = self._classify_category(tokens)
            capability_key = self._build_capability_key(category, tokens)
            name = self._build_name(capability_key, tokens)
            performance, security, complexity = self._score(category, tokens, file_path)
            reusable_score, reusable_pass, reusable_reason = self._reusability_score(tokens, rel)
            inferred_dependencies = CATEGORY_DEPENDENCIES.get(category, [])
            description = f"Extracted {category} capability from {rel.as_posix()}"
            fingerprint = hashlib.sha1(
                f"{capability_key}:{rel.as_posix()}:{performance}:{security}:{complexity}:{reusable_score}".encode("utf-8")
            ).hexdigest()

            candidate = CandidateFeature(
                ingestion_record_id=synthetic_ingestion_id,
                name=name,
                capability_key=capability_key,
                category=category,
                description=description,
                source_ref=rel.as_posix(),
                fingerprint=fingerprint,
                performance=performance,
                security=security,
                complexity=complexity,
                reusable_score=reusable_score,
                reusable_across_projects=reusable_pass,
                reusable_reason=reusable_reason,
                inferred_dependencies=inferred_dependencies,
            )
            existing = by_capability.get(capability_key)
            if existing is None or candidate.score_total > existing.score_total:
                by_capability[capability_key] = candidate

        return sorted(by_capability.values(), key=lambda c: (c.category, c.capability_key))

    def _upsert_candidates(self, conn: Any, ingestion_id: int, candidates: list[CandidateFeature]) -> None:
        for c in candidates:
            conn.execute(
                """
                INSERT INTO feature_candidates (
                    ingestion_record_id, name, capability_key, category, description,
                    source_ref, fingerprint, performance, security, complexity,
                    reusable_score, reusable_across_projects, reusable_reason, inferred_dependencies,
                    unresolved_dependencies
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, '[]')
                ON CONFLICT (ingestion_record_id, capability_key)
                DO UPDATE SET
                    name=excluded.name,
                    category=excluded.category,
                    description=excluded.description,
                    source_ref=excluded.source_ref,
                    fingerprint=excluded.fingerprint,
                    performance=excluded.performance,
                    security=excluded.security,
                    complexity=excluded.complexity,
                    reusable_score=excluded.reusable_score,
                    reusable_across_projects=excluded.reusable_across_projects,
                    reusable_reason=excluded.reusable_reason,
                    inferred_dependencies=excluded.inferred_dependencies,
                    unresolved_dependencies='[]',
                    candidate_status='candidate',
                    resolver_decision=NULL,
                    resolved_feature_id=NULL
                """,
                (
                    ingestion_id,
                    c.name,
                    c.capability_key,
                    c.category,
                    c.description,
                    c.source_ref,
                    c.fingerprint,
                    c.performance,
                    c.security,
                    c.complexity,
                    c.reusable_score,
                    1 if c.reusable_across_projects else 0,
                    c.reusable_reason,
                    json.dumps(c.inferred_dependencies, ensure_ascii=True),
                ),
            )

    def _resolve_decision(self, score_diff: int, thresholds: ResolverThresholds) -> str:
        if score_diff >= thresholds.threshold_replace:
            return "replace"
        if abs(score_diff) <= thresholds.threshold_merge:
            return "merge_variant"
        return "keep_old"

    def _insert_feature_with_score(
        self,
        conn: Any,
        *,
        name: str,
        capability_key: str,
        category: str,
        description: str,
        status: str,
        version: int,
        source_ref: str,
        ingestion_record_id: int,
        performance: int,
        security: int,
        complexity: int,
    ) -> int:
        unique_name = self._ensure_unique_name(conn, name)
        cur = conn.execute(
            """
            INSERT INTO features (
                name, capability_key, category, description, status,
                version, source_ref, ingestion_record_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                unique_name,
                capability_key,
                category,
                description,
                status,
                version,
                source_ref,
                ingestion_record_id,
            ),
        )
        feature_id = int(cur.lastrowid)
        conn.execute(
            """
            INSERT INTO feature_scores (feature_id, performance, security, complexity)
            VALUES (?, ?, ?, ?)
            """,
            (feature_id, performance, security, complexity),
        )
        self._upsert_feature_embedding(conn, feature_id, unique_name, category, description)
        return feature_id

    def _persist_dependency_edges(self, conn: Any, feature_id: int, dependency_categories: list[str]) -> list[str]:
        missing: list[str] = []
        for dep_category in dependency_categories:
            dep = conn.execute(
                """
                SELECT f.id
                FROM features f
                JOIN feature_scores s ON s.feature_id = f.id
                WHERE f.category = ? AND f.status = 'active'
                ORDER BY s.score_total DESC
                LIMIT 1
                """,
                (dep_category,),
            ).fetchone()
            if dep is None:
                missing.append(dep_category)
                continue
            if int(dep["id"]) == feature_id:
                continue
            conn.execute(
                """
                INSERT OR IGNORE INTO feature_relations (from_feature_id, to_feature_id, relation_type)
                VALUES (?, ?, 'depends_on')
                """,
                (feature_id, dep["id"]),
            )
        return missing

    def _snapshot_feature(self, conn: Any, old_feature: Any, reason: str) -> None:
        conn.execute(
            """
            INSERT INTO feature_history (
                feature_id, lineage_key, name, capability_key, category, status, version,
                description, score_performance, score_security, score_complexity, score_total,
                ingestion_record_id, reason
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                old_feature["id"],
                old_feature["capability_key"],
                old_feature["name"],
                old_feature["capability_key"],
                old_feature["category"],
                old_feature["status"],
                old_feature["version"],
                old_feature["description"],
                old_feature["performance"],
                old_feature["security"],
                old_feature["complexity"],
                old_feature["score_total"],
                old_feature["ingestion_record_id"],
                reason,
            ),
        )

    def _assert_next_version(self, conn: Any, capability_key: str, old_version: int, new_version: int) -> None:
        max_row = conn.execute(
            "SELECT MAX(version) AS max_version FROM features WHERE capability_key = ?",
            (capability_key,),
        ).fetchone()
        max_version = int(max_row["max_version"]) if max_row and max_row["max_version"] is not None else 0
        if new_version != old_version + 1:
            raise ValueError("invalid replacement version step")
        if max_version > old_version:
            raise ValueError("version monotonicity violated: existing version already ahead")

    def _next_version(self, conn: Any, capability_key: str) -> int:
        row = conn.execute(
            "SELECT COALESCE(MAX(version), 0) AS max_version FROM features WHERE capability_key = ?",
            (capability_key,),
        ).fetchone()
        return int(row["max_version"]) + 1

    def _ensure_unique_name(self, conn: Any, desired: str) -> str:
        base = desired
        candidate = base
        counter = 2
        while conn.execute("SELECT 1 FROM features WHERE name = ? LIMIT 1", (candidate,)).fetchone():
            candidate = f"{base}.v{counter}"
            counter += 1
        return candidate

    def _tokenize_path(self, rel_path: Path) -> list[str]:
        parts = [p.lower() for p in rel_path.parts]
        tokens: list[str] = []
        for part in parts:
            tokens.extend(WORD_RE.findall(part.replace("-", "_")))
        return [t for t in tokens if t]

    def _reader_normalized_tokens(self, file_path: Path) -> list[str]:
        ext = file_path.suffix.lower()
        if ext not in {".md", ".txt", ".html", ".htm", ".json", ".yaml", ".yml"}:
            return []
        try:
            raw = file_path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            return []
        cleaned = HTML_TAG_RE.sub(" ", raw.replace("\n", " ").replace("\r", " ")).lower()
        return WORD_RE.findall(cleaned)[:80]

    def _classify_category(self, tokens: list[str]) -> str:
        joined = " ".join(tokens)
        for category, keywords in CATEGORY_RULES:
            if any(k in joined for k in keywords):
                return category
        return "general"

    def _build_capability_key(self, category: str, tokens: list[str]) -> str:
        stop = {"py", "md", "json", "yaml", "yml", "js", "ts", "tsx", "jsx", "html", "css"}
        picked = [t for t in tokens if t not in stop and t != category]
        core = picked[0] if picked else "core"
        return f"{category}.{core}"

    def _build_name(self, capability_key: str, tokens: list[str]) -> str:
        stop = {"py", "md", "json", "yaml", "yml", "js", "ts", "tsx", "jsx", "html", "css"}
        picked = [t for t in tokens if t not in stop]
        suffix = picked[1] if len(picked) > 1 else "default"
        normalized = f"{capability_key}.{suffix}".lower()
        normalized = re.sub(r"[^a-z0-9.]+", ".", normalized)
        normalized = re.sub(r"\.{2,}", ".", normalized).strip(".")
        return normalized or "general.core.default"

    def _score(self, category: str, tokens: list[str], file_path: Path) -> tuple[int, int, int]:
        perf, sec, comp = BASE_SCORES.get(category, BASE_SCORES["general"])
        joined = " ".join(tokens)

        if any(k in joined for k in ("cache", "async", "batch", "opt", "fast")):
            perf += 2
        if any(k in joined for k in ("auth", "token", "encrypt", "secure", "acl")):
            sec += 2
        if any(k in joined for k in ("legacy", "compat", "migration", "complex")):
            comp += 2

        ext = file_path.suffix.lower()
        if ext in {".md", ".txt", ".rst", ".html"}:
            comp -= 1
        if ext in {".ts", ".tsx", ".rs", ".py"}:
            perf += 1

        perf = max(0, min(10, perf))
        sec = max(0, min(10, sec))
        comp = max(0, min(10, comp))
        return perf, sec, comp

    def _reusability_score(self, tokens: list[str], relative_path: Path) -> tuple[int, bool, str]:
        score = 10
        joined = " ".join(tokens)

        project_specific_markers = ("temp", "tmp", "prototype", "arsip", "backup", "draft", "akp2i")
        if any(marker in joined for marker in project_specific_markers):
            score -= 4

        if any(part.lower() in {"idea", "archive", "arsip_prototipe_dan_tools"} for part in relative_path.parts):
            score -= 2
        if any(part.lower() in {"tmp", "temp", "prototype", "draft"} for part in relative_path.parts):
            score -= 6

        if len(tokens) <= 2:
            score -= 1
        if any(token in {"tmp", "temp", "prototype", "draft"} for token in tokens):
            score -= 3

        if any(k in joined for k in ("auth", "api", "cache", "runtime", "security", "network", "design")):
            score += 1

        score = max(0, min(10, score))
        if score >= 6:
            return score, True, "reusable_pattern_detected"
        return score, False, "project_specific_or_low_generality"

    def _decode_json_list(self, payload: str | None) -> list[str]:
        if not payload:
            return []
        try:
            value = json.loads(payload)
            if isinstance(value, list):
                return [str(x) for x in value]
        except json.JSONDecodeError:
            return []
        return []

    def _build_context_profile(self, files: list[Path], observed_categories: set[str]) -> dict[str, Any]:
        count = len(files)
        if count <= 30:
            size = "small"
        elif count <= 200:
            size = "medium"
        else:
            size = "large"

        if "api" in observed_categories and "design" in observed_categories:
            project_type = "dashboard"
        elif "api" in observed_categories:
            project_type = "api"
        elif "design" in observed_categories:
            project_type = "landing"
        else:
            project_type = "general"

        if size == "small":
            priorities = ["speed_dev", "security", "maintainability"]
        elif size == "medium":
            priorities = ["security", "performance", "maintainability"]
        else:
            priorities = ["scalability", "security", "performance"]

        return {
            "size": size,
            "type": project_type,
            "priorities": priorities,
        }

    def _rerank_features(self, rows: list[Any], context_profile: dict[str, Any]) -> list[Any]:
        def score(row: Any) -> float:
            total = float(row["score_total"])
            size = context_profile["size"]
            ptype = context_profile["type"]

            if size == "small":
                total += max(0, 6 - int(row["complexity"]))
                if row["category"] == "api":
                    total += 1.5
            elif size == "large":
                total += int(row["security"]) * 0.6
                total += int(row["performance"]) * 0.5
            else:
                total += int(row["security"]) * 0.3

            if ptype == "api" and row["category"] in {"api", "security", "network"}:
                total += 1.0
            if ptype == "dashboard" and row["category"] in {"design", "api"}:
                total += 1.0
            if ptype == "landing" and row["category"] == "design":
                total += 1.0
            return total

        return sorted(rows, key=lambda r: (score(r), r["score_total"]), reverse=True)

    def _recommendation_confidence(
        self,
        *,
        missing_deps_count: int,
        context_profile: dict[str, Any],
        retrieval_mode: str,
    ) -> float:
        base = 0.85 if retrieval_mode == "retrieval" else 0.7
        if context_profile["size"] == "small":
            base += 0.05
        elif context_profile["size"] == "large":
            base -= 0.05
        base -= min(0.25, missing_deps_count * 0.08)
        return max(0.0, min(1.0, base))

    def _upsert_feature_embedding(
        self,
        conn: Any,
        feature_id: int,
        name: str,
        category: str,
        description: str,
    ) -> None:
        tokens = self._embedding_tokens_from_text(f"{name} {category} {description}")
        conn.execute(
            """
            INSERT INTO feature_embeddings (feature_id, embedding_tokens, model, updated_at)
            VALUES (?, ?, 'lite-token-v1', strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
            ON CONFLICT (feature_id) DO UPDATE SET
                embedding_tokens=excluded.embedding_tokens,
                model=excluded.model,
                updated_at=strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
            """,
            (feature_id, json.dumps(tokens, ensure_ascii=True)),
        )

    def _embedding_tokens_from_text(self, text: str) -> list[str]:
        stop = {
            "the", "and", "for", "with", "from", "into", "this", "that", "use", "using",
            "feature", "default", "core", "module", "layer",
        }
        tokens = [t for t in WORD_RE.findall(text.lower()) if len(t) > 2 and t not in stop]
        # deterministic top-k unique order
        uniq: list[str] = []
        seen: set[str] = set()
        for t in tokens:
            if t in seen:
                continue
            seen.add(t)
            uniq.append(t)
            if len(uniq) >= 32:
                break
        return uniq

    def _retrieval_query_tokens(
        self,
        category: str,
        context_profile: dict[str, Any],
        missing_deps: list[str],
    ) -> set[str]:
        raw = [category, context_profile["type"], context_profile["size"], *context_profile["priorities"], *missing_deps]
        return set(self._embedding_tokens_from_text(" ".join(raw)))

    def _semantic_best_feature(self, conn: Any, candidates: list[Any], query_tokens: set[str]) -> tuple[Any, float]:
        best = candidates[0]
        best_score = -1.0
        for row in candidates:
            emb = conn.execute(
                "SELECT embedding_tokens FROM feature_embeddings WHERE feature_id = ?",
                (row["id"],),
            ).fetchone()
            if emb is None:
                score = 0.0
            else:
                candidate_tokens = set(self._decode_json_list(emb["embedding_tokens"]))
                if not candidate_tokens:
                    score = 0.0
                else:
                    inter = len(candidate_tokens & query_tokens)
                    union = len(candidate_tokens | query_tokens)
                    score = (inter / union) if union else 0.0
            if score > best_score:
                best = row
                best_score = score
        return best, max(0.0, best_score)

    def _build_decision_cache_key(
        self,
        *,
        project_path: Path,
        files: list[Path],
        observed_categories: set[str],
        category_filter: str | None,
        context_profile: dict[str, Any],
    ) -> str:
        payload = {
            "project_fingerprint": self._project_fingerprint(project_path, files),
            "observed_categories": sorted(observed_categories),
            "category_filter": category_filter or "",
            "context_profile": context_profile,
        }
        return hashlib.sha1(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()

    def _project_fingerprint(self, project_path: Path, files: list[Path]) -> str:
        normalized = str(project_path.resolve())
        if not files:
            # Fast fallback for cache key build paths where file list is not reused.
            return hashlib.sha1(normalized.encode("utf-8")).hexdigest()
        rels = []
        for path in files:
            try:
                rels.append(path.relative_to(project_path).as_posix())
            except ValueError:
                rels.append(path.as_posix())
        rels.sort()
        return hashlib.sha1(f"{normalized}|{len(files)}|{'|'.join(rels[:200])}".encode("utf-8")).hexdigest()

    def _is_noise_file(self, file_path: Path) -> bool:
        if file_path.name in IGNORED_NAMES:
            return True
        if file_path.suffix.lower() in IGNORED_SUFFIXES:
            return True
        lowered_parts = {part.lower() for part in file_path.parts}
        return any(part in lowered_parts for part in IGNORED_PARTS)
