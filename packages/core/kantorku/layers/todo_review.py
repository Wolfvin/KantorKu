"""
TodoReviewPhase — Workers review and validate TODOs before execution.

This is the phase that happens AFTER the contract is created but
BEFORE execution starts. The manager presents the TODO list to
the team, and every worker MUST:

1. Read the TODO list
2. Give their feedback (concerns, suggestions, capacity check)
3. Confirm they understand their assigned tasks
4. Flag any blockers or dependencies they see

This mimics real office behavior: when a project manager creates
a task list, they don't just assign it silently. They call a
meeting, present the tasks, and everyone discusses until they're
aligned.

Key principle: "Manager buat TODO → wajib bahas bareng tim biar
semua LLM tau tugasnya. Setiap worker baca itu lalu beri saran."

Without this phase, workers might:
- Not understand their tasks fully
- Miss dependencies between tasks
- Start working with wrong assumptions
- Duplicate effort because they didn't know what others are doing
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any

from kantorku.events.bus import EventBus
from kantorku.events.emitter import EventEmitter
from kantorku.layers.conductor import Conductor, Contract, TodoItem
from kantorku.layers.group_channel import GroupChannel, MessageType
from kantorku.worker.registry import WorkerRegistry


@dataclass
class TodoReview:
    """A single worker's review of a TODO item."""

    worker_id: str = ""
    todo_id: str = ""
    understood: bool = False
    has_concern: bool = False
    concern: str = ""
    suggestion: str = ""
    can_execute: bool = True
    dependencies_needed: list[str] = field(default_factory=list)
    estimated_effort: str = ""
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "worker_id": self.worker_id,
            "todo_id": self.todo_id,
            "understood": self.understood,
            "has_concern": self.has_concern,
            "concern": self.concern,
            "suggestion": self.suggestion,
            "can_execute": self.can_execute,
            "dependencies_needed": self.dependencies_needed,
            "estimated_effort": self.estimated_effort,
            "notes": self.notes,
        }


@dataclass
class TodoReviewResult:
    """Result of the TODO review phase."""

    reviews: list[TodoReview] = field(default_factory=list)
    all_understood: bool = False
    blockers: list[str] = field(default_factory=list)
    refined_todos: list[dict[str, Any]] = field(default_factory=list)
    channel: GroupChannel | None = None
    approved: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "reviews": [r.to_dict() for r in self.reviews],
            "all_understood": self.all_understood,
            "blockers": self.blockers,
            "refined_todos": self.refined_todos,
            "approved": self.approved,
        }


class TodoReviewPhase:
    """
    TodoReviewPhase — where the team reviews the TODO list together.

    This is the critical "meeting before the sprint" phase.
    The manager presents the TODO list, and every worker reviews it.

    Flow:
    1. Manager presents the TODO list in the GroupChannel
    2. Each worker reviews their assigned tasks
    3. Workers also review OTHER workers' tasks (shared context!)
    4. Workers give feedback, flag concerns, suggest improvements
    5. Manager addresses concerns and refines the TODO list
    6. Only when all workers understand → execution starts

    This ensures:
    - Every worker knows EXACTLY what they need to do
    - Every worker knows what OTHERS are doing
    - Dependencies are identified upfront
    - Concerns are addressed before execution, not during
    - The team is aligned before work begins

    Like a real sprint planning meeting: the team reviews the backlog,
    asks questions, and only commits when everyone is confident.
    """

    def __init__(
        self,
        conductor: Conductor,
        registry: WorkerRegistry,
        bus: EventBus,
        review_timeout: float = 120.0,
    ) -> None:
        self.conductor = conductor
        self.registry = registry
        self.bus = bus
        self.review_timeout = review_timeout

    async def review(
        self,
        contract: Contract,
        channel: GroupChannel,
        session_id: str,
    ) -> TodoReviewResult:
        """
        Run the TODO review phase.

        Args:
            contract: The contract with TODOs to review
            channel: The GroupChannel (shared from BriefingRoom)
            session_id: Session ID

        Returns:
            TodoReviewResult with reviews, blockers, and approval status
        """
        emitter = EventEmitter(self.bus, session_id)

        # 1. Manager presents the TODO list
        todo_list_text = self._format_todo_list(contract)
        await channel.speak(
            from_id="conductor",
            content=f"📋 TODO List Review — Please review your assigned tasks:\n\n{todo_list_text}",
            message_type=MessageType.INFO,
        )

        await emitter.custom_event(
            event_type="todo_review_started",
            data={"todos": [t.to_dict() for t in contract.todos]},
        )

        # 2. Each worker reviews the TODO list
        reviews: list[TodoReview] = []
        blockers: list[str] = []

        # Get all assigned workers
        assigned_workers: set[str] = set()
        for todo in contract.todos:
            if todo.assigned_to:
                assigned_workers.add(todo.assigned_to)

        review_tasks = []
        for worker_id in assigned_workers:
            try:
                worker = self.registry.hire(worker_id)
                review_tasks.append(
                    self._worker_review_todos(
                        worker=worker,
                        worker_id=worker_id,
                        contract=contract,
                        channel=channel,
                        session_id=session_id,
                    )
                )
            except Exception:
                continue

        # Wait for all reviews (with timeout)
        try:
            review_results = await asyncio.wait_for(
                asyncio.gather(*review_tasks, return_exceptions=True),
                timeout=self.review_timeout,
            )

            for result in review_results:
                if isinstance(result, Exception):
                    continue
                for review in result:
                    reviews.append(review)

                    # Post the worker's review to the group channel
                    # so ALL other workers can see it
                    content = self._format_review_for_channel(review)
                    msg_type = MessageType.SPEAK
                    if review.has_concern:
                        msg_type = MessageType.CONCERN
                        blockers.append(f"[{review.worker_id}] {review.concern}")
                    elif review.suggestion:
                        msg_type = MessageType.SUGGESTION

                    await channel.speak(
                        from_id=review.worker_id,
                        content=content,
                        message_type=msg_type,
                    )

        except asyncio.TimeoutError:
            await channel.speak(
                from_id="conductor",
                content="TODO review timed out. Proceeding with the reviews we have.",
                message_type=MessageType.INFO,
            )

        # 3. Check if all workers understood their tasks
        all_understood = all(r.understood for r in reviews)
        has_blockers = any(not r.can_execute for r in reviews)

        # 4. Manager addresses concerns
        if blockers or not all_understood:
            await self._address_concerns(
                contract=contract,
                reviews=reviews,
                blockers=blockers,
                channel=channel,
                session_id=session_id,
            )

        # 5. Refine TODOs based on feedback
        refined_todos = await self._refine_todos(contract, reviews, channel, session_id)

        # 6. Final approval
        approved = all_understood and not has_blockers

        if approved:
            await channel.manager_decision(
                content="All workers understand their tasks and have no blockers. TODO list is approved. Let's begin execution.",
                decisions=["TODO list approved — execution can begin"],
            )
        else:
            await channel.manager_decision(
                content="There are some concerns that need attention, but we'll proceed with the current plan while monitoring these areas closely.",
                decisions=["Proceeding with noted concerns", "Monitor flagged areas during execution"],
            )

        await emitter.custom_event(
            event_type="todo_review_completed",
            data={
                "approved": approved,
                "all_understood": all_understood,
                "blockers": blockers,
            },
        )

        return TodoReviewResult(
            reviews=reviews,
            all_understood=all_understood,
            blockers=blockers,
            refined_todos=refined_todos,
            channel=channel,
            approved=approved,
        )

    async def _worker_review_todos(
        self,
        worker: Any,
        worker_id: str,
        contract: Contract,
        channel: GroupChannel,
        session_id: str,
    ) -> list[TodoReview]:
        """
        Have a worker review their assigned TODOs.

        The worker sees:
        - The full TODO list (not just their own tasks)
        - The channel transcript (what others have said)
        - Their specific assignments

        This gives them FULL CONTEXT before they give feedback.
        """
        transcript = channel.get_transcript_text()

        # Find this worker's assigned TODOs
        my_todos = [t for t in contract.todos if t.assigned_to == worker_id]
        all_todos = contract.todos

        prompt = f"""
You are {worker_id} ({worker.role}).
The manager has presented the TODO list for the project: {contract.title}

===== TEAM DISCUSSION SO FAR =====
{transcript}
===================================

===== ALL TASKS IN THE PROJECT =====
{self._format_todo_list(contract)}
=====================================

===== YOUR ASSIGNED TASKS =====
{chr(10).join(f"- [{t.id}] {t.description}" for t in my_todos)}
================================

Please review the entire TODO list and your assignments:

1. Do you UNDERSTAND each of your assigned tasks? (be honest)
2. Do you have any CONCERNS about your tasks or the overall plan?
3. Do you have any SUGGESTIONS for improvement?
4. Can you EXECUTE your assigned tasks? (any blockers?)
5. Are there any DEPENDENCIES you need from other workers?
6. What's your estimated EFFORT for each task?

For EACH of your assigned tasks, respond with JSON:
[
    {{
        "todo_id": "the todo id",
        "understood": true/false,
        "has_concern": true/false,
        "concern": "your concern (if any)",
        "suggestion": "your suggestion (if any)",
        "can_execute": true/false,
        "dependencies_needed": ["other_todo_id", ...],
        "estimated_effort": "low/medium/high",
        "notes": "any additional notes"
    }}
]

IMPORTANT: You can see what other workers have said in the discussion.
Consider their feedback when reviewing your own tasks. If someone raised
a concern that affects your work, address it.
"""
        result = await worker.llm_call_structured(prompt)

        # Parse the result
        reviews = []
        review_list = result if isinstance(result, list) else [result]

        # If result is a dict with a key containing list, extract it
        if isinstance(result, dict) and not any(k in result for k in ["todo_id", "understood"]):
            # Try to find the list
            for v in result.values():
                if isinstance(v, list):
                    review_list = v
                    break

        for item in review_list:
            if isinstance(item, dict):
                reviews.append(TodoReview(
                    worker_id=worker_id,
                    todo_id=item.get("todo_id", ""),
                    understood=item.get("understood", True),
                    has_concern=item.get("has_concern", False),
                    concern=item.get("concern", ""),
                    suggestion=item.get("suggestion", ""),
                    can_execute=item.get("can_execute", True),
                    dependencies_needed=item.get("dependencies_needed", []),
                    estimated_effort=item.get("estimated_effort", ""),
                    notes=item.get("notes", ""),
                ))

        # If no reviews were parsed, create default ones
        if not reviews:
            for todo in my_todos:
                reviews.append(TodoReview(
                    worker_id=worker_id,
                    todo_id=todo.id,
                    understood=True,
                    can_execute=True,
                    notes="Auto-reviewed (LLM parsing fallback)",
                ))

        return reviews

    async def _address_concerns(
        self,
        contract: Contract,
        reviews: list[TodoReview],
        blockers: list[str],
        channel: GroupChannel,
        session_id: str,
    ) -> None:
        """Manager addresses concerns raised during TODO review."""
        if not blockers:
            return

        concerns_text = "\n".join(f"- {b}" for b in blockers)
        summary = f"I've noted the following concerns from the team:\n{concerns_text}\n\nI'll address these before and during execution. If you have dependencies on others, please coordinate through this channel."

        await channel.manager_summary(
            content=summary,
            decisions=[f"Address: {b}" for b in blockers],
        )

    async def _refine_todos(
        self,
        contract: Contract,
        reviews: list[TodoReview],
        channel: GroupChannel,
        session_id: str,
    ) -> list[dict[str, Any]]:
        """Refine TODOs based on worker reviews."""
        import json

        refined = []
        for todo in contract.todos:
            todo_dict = todo.to_dict()

            # Apply worker suggestions
            for review in reviews:
                if review.todo_id == todo.id and review.suggestion:
                    todo_dict["notes"] = review.suggestion

                # Add dependencies
                if review.todo_id == todo.id and review.dependencies_needed:
                    todo_dict["identified_dependencies"] = review.dependencies_needed

            refined.append(todo_dict)

        return refined

    def _format_todo_list(self, contract: Contract) -> str:
        """Format the TODO list for display."""
        lines = [f"Project: {contract.title}", ""]
        for i, todo in enumerate(contract.todos, 1):
            status_emoji = "⬜" if todo.status == "pending" else "🔵" if todo.status == "in_progress" else "✅"
            assignee = f" → @{todo.assigned_to}" if todo.assigned_to else " → (unassigned)"
            deps = f" [depends on: {', '.join(todo.depends_on)}]" if todo.depends_on else ""
            lines.append(f"{i}. {status_emoji} {todo.description}{assignee}{deps}")
        return "\n".join(lines)

    def _format_review_for_channel(self, review: TodoReview) -> str:
        """Format a worker's review for posting in the channel."""
        parts = [f"Reviewing TODO [{review.todo_id}]:"]
        if review.understood:
            parts.append("✅ I understand this task")
        else:
            parts.append("❓ I need clarification on this task")

        if review.concern:
            parts.append(f"⚠️ Concern: {review.concern}")

        if review.suggestion:
            parts.append(f"💡 Suggestion: {review.suggestion}")

        if not review.can_execute:
            parts.append(f"🚫 Blocker: Cannot execute - {review.notes}")

        if review.dependencies_needed:
            parts.append(f"🔗 Needs from: {', '.join(review.dependencies_needed)}")

        if review.estimated_effort:
            parts.append(f"📊 Effort: {review.estimated_effort}")

        return "\n".join(parts)
