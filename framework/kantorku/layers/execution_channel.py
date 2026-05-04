"""
ExecutionChannel — Group chat that stays alive during execution.

Unlike BriefingRoom (structured rounds, pre-execution only),
ExecutionChannel is a freeform, async, non-blocking channel that
remains open while workers are actively working on tasks.

Workers can:
- Announce progress and discoveries
- Ask permission before making changes
- Flag issues that affect other workers
- Answer questions from other workers
- Share interface contracts and updates

This mimics a real office where people chat in Slack while working —
you don't stop working to communicate, and you don't need a
facilitator to speak.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any

from kantorku.layers.group_channel import GroupChannel, MessageType, GroupMessage
from kantorku.events.bus import EventBus


@dataclass
class PermissionResult:
    """Result of an ask_permission() call."""

    approved: bool
    from_id: str          # Who answered (or "timeout")
    reason: str           # Why approved/denied
    msg_id: str           # The question message ID


class ExecutionChannel(GroupChannel):
    """
    Group channel that stays active during execution.

    Extends GroupChannel with:
    - ask_permission(): worker asks group, waits for answer
    - answer_question(): worker answers a pending question
    - announce(): worker posts non-blocking update

    Usage:
        channel = ExecutionChannel(session_id="s1", bus=bus)

        # Worker announces progress
        await channel.announce(
            from_id="coder_wiring",
            content="WebSocket endpoint ready: ws://localhost:8080/ws/progress",
            relevant_workers=["coder_frontend"],
        )

        # Worker asks permission
        result = await channel.ask_permission(
            from_id="auditor",
            question="Can I delete legacy_resize() in image_utils.py?",
            context="Function not called from anywhere.",
            default_answer="skip",
        )
        if result.approved:
            delete_function("legacy_resize")

        # Worker answers a question
        await channel.answer_question(
            from_id="coder_backend",
            question_msg_id=msg_id,
            approved=False,
            reason="I need that function for batch mode next sprint.",
        )
    """

    def __init__(
        self,
        session_id: str,
        bus: EventBus,
        participants: list[str] | None = None,
    ) -> None:
        super().__init__(session_id=session_id, bus=bus, participants=participants)
        # Pending questions: msg_id → asyncio.Future
        self._pending_questions: dict[str, asyncio.Future[dict[str, Any]]] = {}
        self._closed = False

    async def ask_permission(
        self,
        from_id: str,
        question: str,
        context: str = "",
        timeout: float = 45.0,
        default_answer: str = "skip",
    ) -> PermissionResult:
        """
        Worker asks the group a question and waits for an answer.

        If nobody answers within timeout, the default_answer is used.
        If someone answers, their answer is used.

        Args:
            from_id: Worker asking the question
            question: What you want to know / get permission for
            context: Additional context for the question
            timeout: Seconds to wait for an answer (default: 45s)
            default_answer: What to do if nobody answers ("proceed" or "skip")

        Returns:
            PermissionResult with approved/denied + who answered + why
        """
        content = f"❓ {question}"
        if context:
            content += f"\n{context}"

        msg = await self.speak(
            from_id=from_id,
            content=content,
            message_type=MessageType.QUESTION,
            metadata={
                "awaiting_response": True,
                "default": default_answer,
            },
        )

        # Create a future that resolves when someone answers
        loop = asyncio.get_running_loop()
        future: asyncio.Future[dict[str, Any]] = loop.create_future()
        self._pending_questions[msg.id] = future

        try:
            answer = await asyncio.wait_for(
                asyncio.shield(future),
                timeout=timeout,
            )
            return PermissionResult(
                approved=answer.get("approved", True),
                from_id=answer.get("from_id", ""),
                reason=answer.get("reason", ""),
                msg_id=msg.id,
            )
        except asyncio.TimeoutError:
            # Nobody answered — use default
            self._pending_questions.pop(msg.id, None)
            is_approved = default_answer == "proceed"
            # Post timeout notice to channel
            await self.speak(
                from_id=from_id,
                content=f"⏱️ No response in {timeout}s — defaulting to: {default_answer}",
                message_type=MessageType.INFO,
                metadata={"is_timeout_notice": True, "original_question": msg.id},
            )
            return PermissionResult(
                approved=is_approved,
                from_id="timeout",
                reason=f"No response in {timeout}s, default: {default_answer}",
                msg_id=msg.id,
            )

    async def answer_question(
        self,
        from_id: str,
        question_msg_id: str,
        approved: bool,
        reason: str = "",
    ) -> GroupMessage:
        """
        Worker answers a question from another worker.

        This resolves the pending future, so the asker can proceed.

        Args:
            from_id: Worker answering the question
            question_msg_id: ID of the question message being answered
            approved: True = proceed, False = don't
            reason: Why you approve/deny

        Returns:
            The answer message posted to the channel
        """
        icon = "✅" if approved else "❌"
        content = f"{icon} {reason}" if reason else f"{icon} {'Approved' if approved else 'Denied'}"

        msg = await self.respond(
            from_id=from_id,
            content=content,
            reply_to=question_msg_id,
            message_type=MessageType.AGREEMENT if approved else MessageType.DISAGREEMENT,
        )

        # Resolve the future if someone is waiting
        if question_msg_id in self._pending_questions:
            future = self._pending_questions.pop(question_msg_id)
            if not future.done():
                future.set_result({
                    "approved": approved,
                    "from_id": from_id,
                    "reason": reason,
                })

        return msg

    async def announce(
        self,
        from_id: str,
        content: str,
        relevant_workers: list[str] | None = None,
    ) -> GroupMessage:
        """
        Worker announces something to the group — non-blocking.

        Unlike ask_permission(), this does NOT wait for a response.
        It's just a heads-up for other workers.

        Args:
            from_id: Worker making the announcement
            content: What you want to announce
            relevant_workers: Workers who should especially pay attention

        Returns:
            The posted message
        """
        meta: dict[str, Any] = {}
        if relevant_workers:
            meta["relevant_to"] = relevant_workers

        return await self.speak(
            from_id=from_id,
            content=f"📢 {content}",
            message_type=MessageType.INFO,
            metadata=meta,
        )

    def get_pending_questions(self) -> list[dict[str, Any]]:
        """Get all currently unanswered questions."""
        pending = []
        for msg_id, _ in self._pending_questions.items():
            msg = self._message_index.get(msg_id)
            if msg:
                pending.append(msg.to_dict())
        return pending

    def close(self) -> None:
        """Close the channel and cancel all pending futures."""
        self._closed = True
        # Cancel any pending futures
        for msg_id, future in list(self._pending_questions.items()):
            if not future.done():
                future.cancel()
        self._pending_questions.clear()

    @property
    def is_closed(self) -> bool:
        return self._closed
