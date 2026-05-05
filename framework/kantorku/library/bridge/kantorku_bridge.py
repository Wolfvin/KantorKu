"""
KantorKuLibraryBridge — Bridge between KantorKu office workers and the Library.

The bridge enables KantorKu workers to interact with the Library system
through a simplified API designed for the office workflow:

- **find_solution**: Search the Library for solutions to a problem a worker
  is facing.
- **save_solution**: Save a worker's solution to a problem as a Library
  SOLUTION entry.
- **inject_context**: Find relevant Library entries for a worker about to
  execute a task, providing prior knowledge and solved problems.
- **auto_save_from_worker**: Automatically detect and save valuable worker
  output when quality is high enough.

The bridge integrates with the Archive (persistent storage), VectorStore
(semantic search), and Indexer (combined search with filters) to provide
a unified interface for worker-Library interactions.

Example::

    from kantorku.library.storage.archive import Archive
    from kantorku.library.storage.vectors import VectorStore
    from kantorku.library.storage.hot_index import HotIndex
    from kantorku.library.core.indexer import Indexer

    archive = Archive("data/library/archive.db")
    vector_store = VectorStore("data/library/vectors")
    hot_index = HotIndex("data/library/hot_index.duckdb")
    await archive.initialize()
    await vector_store.initialize()
    await hot_index.initialize()

    indexer = Indexer(archive=archive, vector_store=vector_store, hot_index=hot_index)

    bridge = KantorKuLibraryBridge(archive=archive, vector_store=vector_store, indexer=indexer)

    # Find a solution
    result = await bridge.find_solution("How to fix Python ImportError", worker_id="coder-01")
    if result:
        print(f"Found: {result['title']} (quality={result['quality_score']})")

    # Save a solution
    entry = await bridge.save_solution(
        problem="Module not found: requests",
        solution="Run pip install requests to install the missing package.",
        solution_code="pip install requests",
        worker_id="coder-01",
        session_id="sess-abc123",
    )
"""

from __future__ import annotations

import logging
from typing import Any

from kantorku.library.core.models import EntrySource, EntryType, LibraryEntry, VerificationResult
from kantorku.library.core.indexer import Indexer
from kantorku.library.storage.archive import Archive
from kantorku.library.storage.vectors import VectorStore

logger = logging.getLogger(__name__)

# Minimum quality threshold for auto-save decisions
_AUTO_SAVE_MIN_QUALITY = 0.7


class KantorKuLibraryBridge:
    """Bridge between KantorKu office workers and the Library.

    Provides a simplified API for workers to search the Library for
    solutions, save their own solutions, receive relevant context
    before task execution, and automatically persist valuable output.

    Args:
        archive: The Archive instance for persistent storage.
        vector_store: The VectorStore instance for semantic search.
        indexer: The Indexer instance for combined search with filters.
    """

    def __init__(
        self,
        archive: Archive,
        vector_store: VectorStore,
        indexer: Indexer,
    ) -> None:
        self._archive = archive
        self._vector_store = vector_store
        self._indexer = indexer

    # ── Find Solution ─────────────────────────────────────────────────────

    async def find_solution(
        self,
        problem: str,
        worker_id: str | None = None,
    ) -> dict | None:
        """Search the Library for solutions to a problem.

        Uses the Indexer's combined vector + archive search to find
        SOLUTION-type entries that match the problem description. Results
        are filtered to only include entries with a quality score >= 0.5
        and are ranked by a combination of semantic similarity and quality.

        Args:
            problem: A description of the problem to solve.
            worker_id: Optional worker ID for logging/tracking purposes.

        Returns:
            A dict with keys ``entry_id``, ``title``, ``content``,
            ``quality_score``, ``shelf_path`` if a solution is found,
            or ``None`` if no suitable solution exists in the Library.
        """
        logger.info(
            "Worker %s searching for solution: %s",
            worker_id or "(anonymous)",
            problem[:100],
        )

        try:
            results = await self._indexer.search(
                query=problem,
                top_k=5,
                entry_type="solution",
                min_quality=0.5,
            )
        except Exception as exc:
            logger.error(
                "Failed to search for solution (worker=%s): %s",
                worker_id,
                exc,
            )
            return None

        if not results:
            logger.info(
                "No solution found for problem (worker=%s): %s",
                worker_id or "(anonymous)",
                problem[:80],
            )
            return None

        # Take the top-ranked result
        best = results[0]

        # Retrieve the full entry for complete content
        entry = await self._archive.get(best["entry_id"])
        if entry is None:
            logger.warning(
                "Index returned entry %s but it was not found in archive",
                best["entry_id"],
            )
            return None

        # Record that this entry was used
        try:
            await self._archive.record_usage(entry.id)
        except Exception as exc:
            logger.debug("Failed to record usage for %s: %s", entry.id, exc)

        result = {
            "entry_id": entry.id,
            "title": entry.title or "(untitled)",
            "content": entry.content,
            "quality_score": entry.quality_score,
            "shelf_path": entry.shelf_path,
        }

        logger.info(
            "Found solution for worker %s: %s (quality=%.2f)",
            worker_id or "(anonymous)",
            result["title"],
            result["quality_score"],
        )
        return result

    # ── Save Solution ─────────────────────────────────────────────────────

    async def save_solution(
        self,
        problem: str,
        solution: str,
        solution_code: str | None = None,
        worker_id: str | None = None,
        session_id: str | None = None,
        task_id: str | None = None,
        failed_attempts: list[dict] | None = None,
        verification_result: str = "untested",
    ) -> LibraryEntry:
        """Save a worker's solution to the Library as a SOLUTION entry.

        Creates a new LibraryEntry with type SOLUTION, populating all
        relevant fields including the problem description, solution content,
        optional code, and origin tracking information. The entry is then
        stored in the Archive and indexed for future search.

        Args:
            problem: A description of the problem that was solved.
            solution: The solution content (markdown).
            solution_code: Optional code implementing the solution.
            worker_id: The ID of the worker who produced the solution.
            session_id: The KantorKu session ID for traceability.
            task_id: The task ID within the session.
            failed_attempts: Optional list of dicts describing approaches
                that were tried and failed before finding the solution.
                Each dict may contain keys like "description", "approach",
                "reason", "error".
            verification_result: Verification status of the solution.
                One of "pass", "fail", or "untested" (default).

        Returns:
            The created LibraryEntry, stored and indexed.
        """
        logger.info(
            "Saving solution from worker %s (session=%s, task=%s): %s",
            worker_id or "(anonymous)",
            session_id or "(none)",
            task_id or "(none)",
            problem[:80],
        )

        # Parse verification result
        try:
            verification = VerificationResult(verification_result)
        except ValueError:
            logger.warning(
                "Invalid verification_result %r — defaulting to 'untested'",
                verification_result,
            )
            verification = VerificationResult.UNTESTED

        # Build a descriptive title from the problem
        title = self._build_solution_title(problem)

        # Create the LibraryEntry
        entry = LibraryEntry(
            title=title,
            content=solution,
            entry_type=EntryType.SOLUTION,
            source=EntrySource.KANTORKU,
            problem_description=problem,
            solution_code=solution_code,
            failed_attempts=failed_attempts or [],
            verification_result=verification,
            origin_worker_id=worker_id,
            origin_session_id=session_id,
            origin_task_id=task_id,
            quality_score=0.6,  # Initial estimate; will be refined by feedback
            domain="code",  # Workers typically produce code-related solutions
        )

        # Determine shelf path from problem content
        entry.shelf_path = self._infer_shelf_from_problem(problem)

        # Store in archive
        try:
            await self._archive.store(entry)
            logger.info("Stored solution entry %s in archive", entry.id)
        except Exception as exc:
            logger.error("Failed to store solution entry: %s", exc)
            raise

        # Index for search
        try:
            await self._indexer.index_entry(entry)
            logger.debug("Indexed solution entry %s", entry.id)
        except Exception as exc:
            logger.warning(
                "Failed to index solution entry %s: %s", entry.id, exc
            )

        return entry

    # ── Inject Context ────────────────────────────────────────────────────

    async def inject_context(
        self,
        task_description: str,
        worker_id: str | None = None,
    ) -> list[dict]:
        """Find relevant Library entries for a worker about to execute a task.

        Searches the Library for entries that are semantically relevant to
        the task description. This provides workers with prior knowledge,
        solved problems, and established procedures before they begin work,
        enabling them to avoid repeating mistakes and leverage existing
        solutions.

        Returns up to 5 entries, each containing a summary and relevance
        score, without the full content (to keep the context concise).

        Args:
            task_description: A description of the task the worker is about
                to execute.
            worker_id: Optional worker ID for logging/tracking.

        Returns:
            A list of dicts with keys ``entry_id``, ``title``, ``summary``,
            ``relevance``. Sorted by relevance descending. May be empty
            if no relevant entries are found.
        """
        logger.info(
            "Injecting context for worker %s: %s",
            worker_id or "(anonymous)",
            task_description[:100],
        )

        try:
            results = await self._indexer.search(
                query=task_description,
                top_k=5,
                min_quality=0.3,
            )
        except Exception as exc:
            logger.error(
                "Failed to search for context (worker=%s): %s",
                worker_id,
                exc,
            )
            return []

        context_entries: list[dict] = []
        for result in results:
            # Retrieve full entry for the summary
            entry = await self._archive.get(result["entry_id"])
            if entry is None:
                continue

            # Compute a relevance score from similarity and quality
            similarity = result.get("similarity", 0.0)
            quality = result.get("quality_score", 0.0)
            relevance = round(0.6 * similarity + 0.4 * quality, 4)

            context_entries.append({
                "entry_id": entry.id,
                "title": entry.title or "(untitled)",
                "summary": entry.summary or (entry.content[:150] + "..." if entry.content else ""),
                "relevance": relevance,
            })

        # Sort by relevance descending
        context_entries.sort(key=lambda x: x["relevance"], reverse=True)

        logger.info(
            "Injected %d context entries for worker %s",
            len(context_entries),
            worker_id or "(anonymous)",
        )
        return context_entries

    # ── Auto-Save from Worker ─────────────────────────────────────────────

    async def auto_save_from_worker(
        self,
        worker_id: str,
        session_id: str,
        task_result: dict,
    ) -> LibraryEntry | None:
        """Automatically detect and save valuable worker output.

        Examines a task result from a worker and determines whether it
        contains a solution-worthy output. If the output quality is high
        enough (>= 0.7 by default), it is automatically saved to the
        Library as a SOLUTION entry.

        The task result dict is expected to contain some of the following
        keys (all optional, but at least ``solution`` or ``output`` is
        needed for anything to be saved):

        - ``problem`` or ``task``: Description of the problem solved.
        - ``solution`` or ``output``: The solution content.
        - ``code`` or ``solution_code``: Optional code implementing the
          solution.
        - ``quality`` or ``quality_score``: A quality score (0.0-1.0).
        - ``failed_attempts``: List of failed approaches.
        - ``verification_result``: "pass", "fail", or "untested".
        - ``task_id``: The task ID within the session.

        Args:
            worker_id: The ID of the worker that produced the output.
            session_id: The KantorKu session ID.
            task_result: A dict containing the task result data.

        Returns:
            The created LibraryEntry if the output was valuable enough
            to save, or ``None`` if the output did not meet the quality
            threshold.
        """
        logger.debug(
            "Auto-save check for worker %s (session=%s)",
            worker_id,
            session_id,
        )

        # Extract solution content
        solution = task_result.get("solution") or task_result.get("output")
        if not solution or not isinstance(solution, str) or not solution.strip():
            logger.debug("No solution content found in task result — skipping auto-save")
            return None

        # Extract problem description
        problem = (
            task_result.get("problem")
            or task_result.get("task")
            or "Auto-saved from worker output"
        )

        # Check quality threshold
        quality = task_result.get("quality") or task_result.get("quality_score")
        if quality is not None:
            try:
                quality = float(quality)
            except (TypeError, ValueError):
                quality = None

        # If no explicit quality, estimate from content
        if quality is None:
            quality = self._estimate_output_quality(solution, task_result)

        if quality < _AUTO_SAVE_MIN_QUALITY:
            logger.info(
                "Auto-save skipped: quality %.2f below threshold %.2f (worker=%s)",
                quality,
                _AUTO_SAVE_MIN_QUALITY,
                worker_id,
            )
            return None

        # Extract optional fields
        solution_code = task_result.get("code") or task_result.get("solution_code")
        failed_attempts = task_result.get("failed_attempts")
        task_id = task_result.get("task_id")
        verification_result = task_result.get("verification_result", "untested")

        logger.info(
            "Auto-saving valuable output from worker %s (quality=%.2f): %s",
            worker_id,
            quality,
            problem[:80],
        )

        entry = await self.save_solution(
            problem=problem,
            solution=solution,
            solution_code=solution_code,
            worker_id=worker_id,
            session_id=session_id,
            task_id=task_id,
            failed_attempts=failed_attempts,
            verification_result=verification_result,
        )

        # Override the initial quality with the estimated score
        entry.quality_score = quality
        entry._recalculate_quality()  # This preserves the quality floor for verified entries
        # Restore our quality estimate since _recalculate_quality uses Bayesian
        entry.quality_score = max(quality, entry.quality_score)
        try:
            await self._archive.store(entry)
        except Exception as exc:
            logger.warning("Failed to update quality for auto-saved entry %s: %s", entry.id, exc)

        return entry

    # ── Allowed Tools ─────────────────────────────────────────────────────

    def get_allowed_tools(self) -> list[str]:
        """Return the list of Library tools available to KantorKu workers.

        These tool names can be included in worker tool configurations
        to grant them access to Library functionality through the bridge.

        Returns:
            A list of tool name strings:
            ``["library.find_solution", "library.save_solution"]``.
        """
        return ["library.find_solution", "library.save_solution"]

    # ── Private helpers ───────────────────────────────────────────────────

    @staticmethod
    def _build_solution_title(problem: str) -> str:
        """Build a descriptive title from a problem description.

        Takes the first meaningful line or sentence of the problem and
        creates a concise title suitable for a Library entry.

        Args:
            problem: The problem description.

        Returns:
            A title string (max 100 characters).
        """
        # Take first non-empty line
        lines = problem.strip().splitlines()
        first_line = next((l.strip() for l in lines if l.strip()), problem[:80])

        # Truncate to reasonable title length
        if len(first_line) > 100:
            first_line = first_line[:97] + "..."

        return first_line

    @staticmethod
    def _infer_shelf_from_problem(problem: str) -> list[str]:
        """Infer a shelf path from the problem description.

        Uses simple keyword matching to assign the solution to an
        appropriate shelf in the Library hierarchy.

        Args:
            problem: The problem description text.

        Returns:
            A list of shelf path segments.
        """
        problem_lower = problem.lower()

        # Topic detection keywords → shelf mapping
        shelf_rules: list[tuple[list[str], list[str]]] = [
            (["python", "django", "flask", "fastapi"], ["Engineering", "Backend", "Python"]),
            (["javascript", "typescript", "node", "react", "vue"], ["Engineering", "Frontend"]),
            (["docker", "kubernetes", "k8s", "deploy", "ci/cd", "devops"], ["Engineering", "DevOps"]),
            (["database", "sql", "postgres", "mysql", "mongodb", "redis"], ["Engineering", "Backend", "Database"]),
            (["auth", "security", "jwt", "oauth", "encryption"], ["Engineering", "Security"]),
            (["api", "rest", "graphql", "endpoint"], ["Engineering", "Backend", "API"]),
            (["test", "testing", "pytest", "unittest", "jest"], ["Engineering", "Backend", "Testing"]),
            (["rust", "golang", "go ", "c++", "compiler"], ["Engineering", "Backend"]),
        ]

        for keywords, shelf in shelf_rules:
            if any(kw in problem_lower for kw in keywords):
                return shelf

        return ["Engineering"]

    @staticmethod
    def _estimate_output_quality(solution: str, task_result: dict) -> float:
        """Estimate the quality of a worker's output for auto-save decisions.

        Uses heuristic signals from the solution content and task result
        to produce a quality estimate in the range [0.0, 1.0].

        Factors considered:
        - Solution length (longer is generally better, up to a point)
        - Presence of code blocks
        - Verification result
        - Whether failed attempts were recorded (shows iteration)

        Args:
            solution: The solution text content.
            task_result: The full task result dict.

        Returns:
            An estimated quality score between 0.0 and 1.0.
        """
        quality = 0.4  # Base quality

        # Content length
        length = len(solution)
        if length > 100:
            quality += 0.1
        if length > 500:
            quality += 0.1
        if length > 1500:
            quality += 0.05
        if length < 50:
            quality -= 0.2

        # Code presence
        if "```" in solution:
            quality += 0.1

        # Verification bonus
        verification = task_result.get("verification_result", "untested")
        if verification == "pass":
            quality += 0.15
        elif verification == "fail":
            quality -= 0.2

        # Failed attempts recorded (shows iteration and thoroughness)
        failed_attempts = task_result.get("failed_attempts")
        if failed_attempts and len(failed_attempts) > 0:
            quality += 0.05

        return max(0.0, min(quality, 1.0))
