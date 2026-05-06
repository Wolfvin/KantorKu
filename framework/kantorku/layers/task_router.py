"""
Task Skill Router — O22: Route tasks to the best-fit worker.

Uses keyword-based scoring to match tasks to workers based on
their capabilities. Includes a comprehensive route map and
supports multiple assignment strategies.

Like a project manager who knows exactly who to assign to each task
based on their skills.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class RoutingResult:
    """Result of a task routing decision."""
    worker_id: str = ""
    category: str = ""
    score: float = 0.0
    reason: str = ""


# Route map: keyword patterns → default worker IDs
ROUTE_MAP: dict[str, str] = {
    "code/frontend": "coder_frontend",
    "code/backend": "coder_backend",
    "api": "coder_wiring",
    "ws": "coder_wiring",
    "mcp": "coder_wiring",
    "verify/ux": "verifier_designer",
    "verify/logic": "verifier_engineer",
    "debug/fix": "debugger",
    "research/search": "scout",
    "review/audit": "auditor",
    "document": "scribe",
    "summarize": "summarizer",
}

# Expanded keyword → worker mapping for scoring
_KEYWORD_WORKER_MAP: dict[str, str] = {
    # Frontend keywords
    "frontend": "coder_frontend",
    "react": "coder_frontend",
    "vue": "coder_frontend",
    "svelte": "coder_frontend",
    "css": "coder_frontend",
    "html": "coder_frontend",
    "ui": "coder_frontend",
    "component": "coder_frontend",
    "page": "coder_frontend",
    "layout": "coder_frontend",
    # Backend keywords
    "backend": "coder_backend",
    "api": "coder_backend",
    "server": "coder_backend",
    "database": "coder_backend",
    "model": "coder_backend",
    "schema": "coder_backend",
    "endpoint": "coder_backend",
    "service": "coder_backend",
    "logic": "coder_backend",
    # Wiring keywords
    "websocket": "coder_wiring",
    "ws": "coder_wiring",
    "mcp": "coder_wiring",
    "integration": "coder_wiring",
    "middleware": "coder_wiring",
    "wiring": "coder_wiring",
    "adapter": "coder_wiring",
    "connector": "coder_wiring",
    # Verification keywords
    "verify": "verifier_engineer",
    "test": "verifier_engineer",
    "check": "verifier_engineer",
    "validate": "verifier_engineer",
    "assert": "verifier_engineer",
    "design": "verifier_designer",
    "ux": "verifier_designer",
    "accessibility": "verifier_designer",
    "responsive": "verifier_designer",
    "visual": "verifier_designer",
    # Debug keywords
    "debug": "debugger",
    "fix": "debugger",
    "error": "debugger",
    "bug": "debugger",
    "traceback": "debugger",
    "troubleshoot": "debugger",
    # Research keywords
    "research": "scout",
    "search": "scout",
    "explore": "scout",
    "investigate": "scout",
    "find": "scout",
    "analyze": "scout",
    # Review keywords
    "review": "auditor",
    "audit": "auditor",
    "inspect": "auditor",
    "security": "auditor",
    "compliance": "auditor",
    # Documentation keywords
    "document": "scribe",
    "docs": "scribe",
    "readme": "scribe",
    "comment": "scribe",
    "explain": "scribe",
    # Summary keywords
    "summarize": "summarizer",
    "summary": "summarizer",
    "brief": "summarizer",
    "overview": "summarizer",
    "condense": "summarizer",
}


class TaskSkillRouter:
    """
    Task Skill Router — route tasks to the best-fit worker.

    Uses keyword extraction and scoring to match task descriptions
    to workers based on their capabilities. Supports multiple
    assignment strategies (best_fit, round_robin, least_loaded).

    Usage:
        router = TaskSkillRouter()
        result = router.route("Build a REST API endpoint", ["coder_backend", "coder_frontend"])
        score = router.score_worker(["api", "backend"], "coder_backend", {"skills": ["python", "api"]})
        worker_id = router.assign(task, workers, strategy="best_fit")
    """

    def __init__(self) -> None:
        self._round_robin_idx: dict[str, int] = {}
        self._worker_loads: dict[str, int] = {}

    def _extract_task_keywords(self, task_description: str) -> list[str]:
        """
        Extract meaningful keywords from a task description.

        Args:
            task_description: The task description

        Returns:
            List of keywords (lowercase)
        """
        if not task_description:
            return []

        text_lower = task_description.lower()
        # Extract alphanumeric tokens
        tokens = re.findall(r"[a-z][a-z0-9_]*", text_lower)

        # Remove common stopwords
        stopwords = {
            "the", "a", "an", "is", "are", "was", "were", "be", "been",
            "have", "has", "had", "do", "does", "did", "will", "would",
            "could", "should", "may", "might", "to", "of", "in", "for",
            "on", "with", "at", "by", "from", "and", "or", "but", "not",
            "this", "that", "it", "its", "me", "my", "we", "our",
        }

        return [t for t in tokens if t not in stopwords and len(t) > 2]

    def route(
        self,
        task_description: str,
        available_workers: list[str] | None = None,
    ) -> RoutingResult:
        """
        Route a task to the best-fit worker.

        Args:
            task_description: Description of the task
            available_workers: List of available worker IDs (restricts routing)

        Returns:
            RoutingResult with worker_id, category, score, and reason
        """
        keywords = self._extract_task_keywords(task_description)

        if not keywords:
            # No keywords — default to backend worker
            default_worker = "coder_backend"
            if available_workers and default_worker not in available_workers:
                default_worker = available_workers[0] if available_workers else ""
            return RoutingResult(
                worker_id=default_worker,
                category="general",
                score=0.3,
                reason="No specific keywords found — defaulting to general worker",
            )

        # Score each keyword against the keyword-worker map
        worker_scores: dict[str, float] = {}
        category = "general"

        for keyword in keywords:
            mapped_worker = _KEYWORD_WORKER_MAP.get(keyword)
            if mapped_worker:
                worker_scores[mapped_worker] = worker_scores.get(mapped_worker, 0.0) + 1.0
                # Track the category from route map
                for route_key, route_worker in ROUTE_MAP.items():
                    if route_worker == mapped_worker:
                        category = route_key
                        break

        # Filter by available workers if specified
        if available_workers:
            available_set = set(available_workers)
            worker_scores = {
                w: s for w, s in worker_scores.items()
                if w in available_set
            }

            # If no scored workers match available, pick first available
            if not worker_scores and available_workers:
                return RoutingResult(
                    worker_id=available_workers[0],
                    category=category,
                    score=0.2,
                    reason="No keyword match — assigned first available worker",
                )

        if not worker_scores:
            return RoutingResult(
                worker_id="",
                category=category,
                score=0.0,
                reason="No matching worker found for task keywords",
            )

        # Normalize scores
        max_score = max(worker_scores.values())
        for w in worker_scores:
            worker_scores[w] = worker_scores[w] / max_score if max_score > 0 else 0.0

        # Select best worker
        best_worker = max(worker_scores, key=lambda w: worker_scores[w])
        best_score = worker_scores[best_worker]

        return RoutingResult(
            worker_id=best_worker,
            category=category,
            score=best_score,
            reason=f"Best match: {best_score:.2f} score based on keyword analysis",
        )

    def score_worker(
        self,
        task_keywords: list[str],
        worker_id: str,
        worker_capabilities: dict[str, Any] | None = None,
    ) -> float:
        """
        Score a worker's fit for a task based on keywords and capabilities.

        Args:
            task_keywords: Keywords extracted from the task
            worker_id: The worker to score
            worker_capabilities: Optional worker capability dict

        Returns:
            Score (0.0 - 1.0)
        """
        if not task_keywords:
            return 0.5  # Neutral score

        score = 0.0
        max_possible = len(task_keywords)

        # Score based on keyword-worker map
        for keyword in task_keywords:
            mapped_worker = _KEYWORD_WORKER_MAP.get(keyword)
            if mapped_worker == worker_id:
                score += 1.0

        # Score based on worker capabilities
        if worker_capabilities:
            skills = worker_capabilities.get("skills", [])
            if isinstance(skills, list):
                for keyword in task_keywords:
                    if keyword in " ".join(str(s) for s in skills).lower():
                        score += 0.5

            # Check worker role/specialization
            role = str(worker_capabilities.get("role", "")).lower()
            for keyword in task_keywords:
                if keyword in role:
                    score += 0.3

        # Normalize
        if max_possible > 0:
            score = min(1.0, score / max_possible)

        return score

    def assign(
        self,
        task: str | dict[str, Any],
        workers: list[str],
        strategy: str = "best_fit",
    ) -> str:
        """
        Assign a task to a worker using the specified strategy.

        Strategies:
        - best_fit: Route to highest-scoring worker
        - round_robin: Cycle through workers evenly
        - least_loaded: Assign to worker with fewest current tasks

        Args:
            task: Task description (string or dict with 'description' key)
            workers: List of available worker IDs
            strategy: Assignment strategy

        Returns:
            Selected worker_id
        """
        if not workers:
            return ""

        # Extract task description
        if isinstance(task, dict):
            description = task.get("description", task.get("instruction", ""))
        else:
            description = str(task)

        if strategy == "best_fit":
            result = self.route(description, workers)
            return result.worker_id or workers[0]

        elif strategy == "round_robin":
            task_key = description[:20] if description else "default"
            idx = self._round_robin_idx.get(task_key, 0)
            worker_id = workers[idx % len(workers)]
            self._round_robin_idx[task_key] = idx + 1
            return worker_id

        elif strategy == "least_loaded":
            # Find worker with minimum load
            min_load = float("inf")
            selected = workers[0]
            for wid in workers:
                load = self._worker_loads.get(wid, 0)
                if load < min_load:
                    min_load = load
                    selected = wid
            self._worker_loads[selected] = self._worker_loads.get(selected, 0) + 1
            return selected

        else:
            # Default to best_fit
            result = self.route(description, workers)
            return result.worker_id or workers[0]

    def validate_assignment(
        self,
        task: str,
        worker_id: str,
        worker_capabilities: dict[str, Any] | None = None,
    ) -> bool:
        """
        Validate that a task assignment is appropriate.

        Args:
            task: Task description
            worker_id: Assigned worker ID
            worker_capabilities: Worker capability dict

        Returns:
            True if the assignment appears valid
        """
        keywords = self._extract_task_keywords(task)
        if not keywords:
            return True  # Can't validate without keywords

        score = self.score_worker(keywords, worker_id, worker_capabilities)
        return score >= 0.2  # Minimum threshold for valid assignment
