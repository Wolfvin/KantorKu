"""
EventEmitter — Convenience wrapper for emitting typed events.

Provides methods for each event type in the kantorku protocol,
ensuring consistent event structure across the framework.
"""

from __future__ import annotations

from typing import Any

from kantorku.events.bus import EventBus


class EventEmitter:
    """
    Typed event emitter — wraps EventBus with convenience methods.

    Usage:
        emitter = EventEmitter(bus, "session-123")
        await emitter.briefing_opened(from_id="conductor", content="Todo 1")
        await emitter.task_assigned(to_id="coder_backend", content="Implement X")
    """

    def __init__(self, bus: EventBus, session_id: str) -> None:
        self.bus = bus
        self.session_id = session_id

    async def _emit(self, **kwargs: Any) -> None:
        await self.bus.emit(self.session_id, kwargs)

    # ── Lifecycle events ──────────────────────────────────────────

    async def briefing_opened(self, from_id: str = "conductor", content: str = "") -> None:
        await self._emit(type="briefing_opened", **{"from": from_id}, content=content)

    async def plan_drafted(self, from_id: str = "conductor", content: str = "") -> None:
        await self._emit(type="plan_drafted", **{"from": from_id}, content=content)

    async def plan_revised(
        self, from_id: str = "conductor", content: str = "", reason: str = ""
    ) -> None:
        await self._emit(type="plan_revised", **{"from": from_id}, content=content, reason=reason)

    async def contract_ready(
        self, from_id: str = "conductor", todos: list[dict[str, Any]] | None = None
    ) -> None:
        await self._emit(type="contract_ready", **{"from": from_id}, todos=todos or [])

    async def contract_accepted(self) -> None:
        await self._emit(type="contract_accepted", **{"from": "user"})

    # ── Worker activity ───────────────────────────────────────────

    async def worker_speak_up(self, from_id: str, content: str) -> None:
        await self._emit(type="worker_speak_up", **{"from": from_id}, content=content)

    async def task_assigned(
        self, from_id: str = "conductor", to_id: str = "", content: str = ""
    ) -> None:
        await self._emit(type="task_assigned", **{"from": from_id, "to": to_id}, content=content)

    async def task_started(self, from_id: str) -> None:
        await self._emit(type="task_started", **{"from": from_id})

    async def task_done(self, from_id: str, files: list[str] | None = None) -> None:
        await self._emit(type="task_done", **{"from": from_id}, files=files or [])

    async def task_failed(self, from_id: str, error: str) -> None:
        await self._emit(type="task_failed", **{"from": from_id}, error=error)

    # ── Peer communication ────────────────────────────────────────

    async def worker_dm(
        self, from_id: str, to_id: str, content: str
    ) -> None:
        await self._emit(type="worker_dm", **{"from": from_id, "to": to_id}, content=content)

    async def worker_broadcast(self, from_id: str, content: str) -> None:
        await self._emit(type="worker_broadcast", **{"from": from_id}, content=content)

    # ── Context pool ──────────────────────────────────────────────

    async def context_fetch_start(
        self, instance: int, query: str, for_task: str
    ) -> None:
        await self._emit(
            type="context_fetch_start", instance=instance, query=query, for_task=for_task
        )

    async def context_fetch_done(
        self, instance: int, for_task: str, results: list[dict[str, Any]] | None = None
    ) -> None:
        await self._emit(
            type="context_fetch_done", instance=instance, for_task=for_task, results=results or []
        )

    async def context_requested(self, from_id: str, query: str) -> None:
        await self._emit(type="context_requested", **{"from": from_id}, query=query)

    async def context_delivered(self, to_id: str, summary: str) -> None:
        await self._emit(type="context_delivered", **{"to": to_id}, summary=summary)

    # ── Verification ──────────────────────────────────────────────

    async def verify_design_start(self) -> None:
        await self._emit(type="verify_design_start", **{"from": "verifier_designer"})

    async def verify_design_done(
        self, issues: list[str] | None = None, approved: bool = True
    ) -> None:
        await self._emit(
            type="verify_design_done",
            **{"from": "verifier_designer"},
            issues=issues or [],
            approved=approved,
        )

    async def verify_engineer_start(self) -> None:
        await self._emit(type="verify_engineer_start", **{"from": "verifier_engineer"})

    async def verify_engineer_done(
        self, issues: list[str] | None = None, approved: bool = True
    ) -> None:
        await self._emit(
            type="verify_engineer_done",
            **{"from": "verifier_engineer"},
            issues=issues or [],
            approved=approved,
        )

    # ── Learning ──────────────────────────────────────────────────

    async def error_logged(self, lesson: str) -> None:
        await self._emit(type="error_logged", **{"from": "sentinel"}, lesson=lesson)

    async def skill_updated(self, worker_id: str, lesson: str) -> None:
        await self._emit(type="skill_updated", **{"from": "curator"}, worker=worker_id, lesson=lesson)

    # ── Conductor ↔ Client ────────────────────────────────────────

    async def manager_message(self, content: str) -> None:
        await self._emit(type="manager_message", **{"from": "conductor"}, content=content)

    async def manager_question(self, content: str) -> None:
        await self._emit(type="manager_question", **{"from": "conductor"}, content=content)

    # ── Streaming events ───────────────────────────────────────────

    async def llm_stream_start(
        self, from_id: str, model: str = ""
    ) -> None:
        """Emit when an LLM streaming call begins."""
        await self._emit(
            type="llm_stream_start",
            **{"from": from_id},
            model=model,
        )

    async def llm_stream_chunk(
        self, from_id: str, chunk: str, model: str = ""
    ) -> None:
        """Emit a single token chunk from an LLM streaming call."""
        await self._emit(
            type="llm_stream_chunk",
            **{"from": from_id},
            chunk=chunk,
            model=model,
        )

    async def llm_stream_done(
        self, from_id: str, model: str = "", full_text: str = ""
    ) -> None:
        """Emit when an LLM streaming call completes."""
        await self._emit(
            type="llm_stream_done",
            **{"from": from_id},
            model=model,
            full_text=full_text,
        )
