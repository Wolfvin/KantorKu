from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from arch_engine.db import get_connection, init_db
from arch_engine.repository import ArchEngineRepository


class ArchEngineTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp_dir.name)
        self.db_path = self.root / "arch_engine_test.db"
        init_db(self.db_path)
        self.repo = ArchEngineRepository(self.db_path)

    def tearDown(self) -> None:
        self.tmp_dir.cleanup()

    def _write(self, rel: str, content: str = "x") -> Path:
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def test_reusability_gate_rejects_project_specific_candidate(self) -> None:
        src = self.root / "input"
        self._write("input/security/auth.py")
        self._write("input/tmp/prototype_akp2i_draft.md")

        self.repo.ingest_source(src, dry_run=True, apply_candidates=True)
        result = self.repo.resolve()

        self.assertGreaterEqual(result["reusability_gate"]["rejected"], 1)
        reasons = result["reusability_gate"]["reasons"]
        self.assertIn("project_specific_or_low_generality", reasons)

        with get_connection(self.db_path) as conn:
            discarded = conn.execute(
                "SELECT COUNT(*) AS n FROM feature_candidates WHERE candidate_status='discarded'"
            ).fetchone()["n"]
        self.assertGreaterEqual(discarded, 1)

    def test_dependency_relation_persisted_when_prerequisite_exists(self) -> None:
        self._write("first/security/auth.py")
        self.repo.ingest_source(self.root / "first", dry_run=True, apply_candidates=True)
        self.repo.resolve()

        self._write("second/api/router.py")
        self.repo.ingest_source(self.root / "second", dry_run=True, apply_candidates=True)
        self.repo.resolve()

        with get_connection(self.db_path) as conn:
            dep_count = conn.execute(
                "SELECT COUNT(*) AS n FROM feature_relations WHERE relation_type='depends_on'"
            ).fetchone()["n"]
        self.assertGreaterEqual(dep_count, 1)

    def test_resolve_replace_transition_and_history_snapshot(self) -> None:
        first = self.root / "first"
        first.mkdir(parents=True, exist_ok=True)
        (first / "security" / "auth.py").parent.mkdir(parents=True, exist_ok=True)
        (first / "security" / "auth.py").write_text("auth", encoding="utf-8")

        self.repo.ingest_source(first, dry_run=True, apply_candidates=True)
        self.repo.resolve()

        second = self.root / "second"
        second.mkdir(parents=True, exist_ok=True)
        (second / "security" / "auth_cache_encrypt.py").parent.mkdir(parents=True, exist_ok=True)
        (second / "security" / "auth_cache_encrypt.py").write_text("better", encoding="utf-8")

        self.repo.ingest_source(second, dry_run=True, apply_candidates=True)
        result = self.repo.resolve(threshold_replace=1, threshold_merge=0)

        self.assertGreaterEqual(result["decision_counts"].get("replace", 0), 1)

        with get_connection(self.db_path) as conn:
            deprecated = conn.execute(
                "SELECT COUNT(*) AS n FROM features WHERE status='deprecated'"
            ).fetchone()["n"]
            history = conn.execute("SELECT COUNT(*) AS n FROM feature_history").fetchone()["n"]
        self.assertGreaterEqual(deprecated, 1)
        self.assertGreaterEqual(history, 1)

    def test_improve_output_contract_fields(self) -> None:
        self._write("seed/security/auth.py")
        self._write("seed/api/router.py")
        self.repo.ingest_source(self.root / "seed", dry_run=True, apply_candidates=True)
        self.repo.resolve()

        project = self.root / "project"
        self._write("project/design/layout.css")

        result = self.repo.improve(project)

        self.assertIn("summary", result)
        self.assertIn("project_path", result)
        self.assertIn("detected_gaps", result)
        self.assertIn("recommendations", result)

        if result["recommendations"]:
            item = result["recommendations"][0]
            for key in (
                "feature",
                "category",
                "reason",
                "priority",
                "integration_points",
                "missing_dependencies",
            ):
                self.assertIn(key, item)
        self.assertIn("cache_hit", result)
        self.assertIn("context_profile", result)

    def test_improve_uses_decision_cache(self) -> None:
        self._write("seed/security/auth.py")
        self.repo.ingest_source(self.root / "seed", dry_run=True, apply_candidates=True)
        self.repo.resolve()
        self._write("project/api/router.py")

        first = self.repo.improve(self.root / "project")
        second = self.repo.improve(self.root / "project")

        self.assertFalse(first["cache_hit"])
        self.assertTrue(second["cache_hit"])
        self.assertEqual(first["retrieval_mode"], "hybrid")


    def test_reader_normalization_enriches_extraction_tokens(self) -> None:
        self._write("input/spec.md", "Use JWT token auth and access policy for secure login")
        result = self.repo.ingest_source(self.root / "input", dry_run=True, apply_candidates=False)
        categories = {item["category"] for item in result.candidates}
        self.assertIn("security", categories)

    def test_hybrid_mode_marks_selection_mode_and_confidence(self) -> None:
        self._write("seed/security/auth.py")
        self.repo.ingest_source(self.root / "seed", dry_run=True, apply_candidates=True)
        self.repo.resolve()
        self._write("project/api/router.py")

        result = self.repo.improve(self.root / "project", retrieval_mode="hybrid", min_confidence=0.95)
        if result["recommendations"]:
            item = result["recommendations"][0]
            self.assertIn("selection_mode", item)
            self.assertIn("confidence", item)
            self.assertEqual(item["selection_mode"], "retrieval_rerank")
            self.assertIn("semantic_score", item)

    def test_retrieval_mode_uses_embedding_table(self) -> None:
        self._write("seed/security/auth_token_policy.py")
        self._write("seed/api/router.py")
        self.repo.ingest_source(self.root / "seed", dry_run=True, apply_candidates=True)
        self.repo.resolve()
        self._write("project/ui/page.html", "<div>dashboard</div>")

        result = self.repo.improve(self.root / "project", retrieval_mode="retrieval", min_confidence=0.9)
        self.assertEqual(result["retrieval_mode"], "retrieval")
        if result["recommendations"]:
            self.assertIsNotNone(result["recommendations"][0]["semantic_score"])

        with get_connection(self.db_path) as conn:
            n = conn.execute("SELECT COUNT(*) AS n FROM feature_embeddings").fetchone()["n"]
        self.assertGreaterEqual(n, 1)

    def test_schema_migrations_recorded(self) -> None:
        with get_connection(self.db_path) as conn:
            rows = conn.execute("SELECT name FROM schema_migrations ORDER BY name").fetchall()
        names = [r["name"] for r in rows]
        self.assertIn("0001_init.sql", names)
        self.assertIn("0002_decision_cache.sql", names)
        self.assertIn("0003_feature_embeddings.sql", names)


if __name__ == "__main__":
    unittest.main()
