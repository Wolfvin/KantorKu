"""
SessionTranscript — Full session context for workers.

This provides a way for any worker to query the complete context
of what has happened in a session. It's like reading the meeting
minutes — you can catch up on everything that was discussed.

Key use cases:
1. A worker joining mid-session needs to catch up
2. A worker needs to understand what happened before their task
3. Workers need to understand the full client↔manager conversation
4. Workers need to see what other workers have already done

This ensures that during a session, workers have ENOUGH CONTEXT
and know the progress ("bagaimana perkembangannya").

Like in a real office: if you miss a meeting, you read the minutes.
If you're joining a project midway, you read the project history.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from kantorku.layers.group_channel import GroupChannel
from kantorku.layers.conductor import Contract


@dataclass
class TranscriptEntry:
    """A single entry in the session transcript."""

    phase: str = ""          # "client_discussion", "team_briefing", "todo_review", "execution"
    timestamp: str = ""
    from_id: str = ""
    content: str = ""
    entry_type: str = ""     # "message", "decision", "concern", "result"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "phase": self.phase,
            "timestamp": self.timestamp,
            "from_id": self.from_id,
            "content": self.content,
            "entry_type": self.entry_type,
            "metadata": self.metadata,
        }


class SessionTranscript:
    """
    SessionTranscript — the complete record of a session.

    This is the "project file" that every worker can access.
    It contains the full history of:
    - Client ↔ Manager conversations
    - Team briefing discussions
    - TODO reviews
    - Execution progress
    - Results and decisions

    Workers use this to:
    - Get up to speed on the project context
    - Understand what decisions were made and why
    - See what other workers have produced
    - Know the current state of the project

    Usage:
        transcript = SessionTranscript(session_id="s1")

        # Add entries as the session progresses
        transcript.add_entry(
            phase="client_discussion",
            from_id="client",
            content="I need a rate limiter",
            entry_type="message",
        )

        # Workers query for context
        context = transcript.get_context_for_worker("coder_backend")
        summary = transcript.get_summary()
    """

    def __init__(self, session_id: str) -> None:
        self.session_id = session_id
        self._entries: list[TranscriptEntry] = []
        self._channel: GroupChannel | None = None
        self._contract: Contract | None = None

    def set_channel(self, channel: GroupChannel) -> None:
        """Set the GroupChannel for this session."""
        self._channel = channel

    def set_contract(self, contract: Contract) -> None:
        """Set the Contract for this session."""
        self._contract = contract

    def add_entry(
        self,
        phase: str,
        from_id: str,
        content: str,
        entry_type: str = "message",
        metadata: dict[str, Any] | None = None,
        timestamp: str = "",
    ) -> TranscriptEntry:
        """
        Add an entry to the session transcript.

        Args:
            phase: Which phase this entry belongs to
            from_id: Who generated this entry
            content: The content of the entry
            entry_type: Type of entry (message, decision, concern, result)
            metadata: Additional metadata
            timestamp: Timestamp (auto-generated if empty)

        Returns:
            The created TranscriptEntry
        """
        from datetime import datetime, timezone

        entry = TranscriptEntry(
            phase=phase,
            timestamp=timestamp or datetime.now(timezone.utc).isoformat(),
            from_id=from_id,
            content=content,
            entry_type=entry_type,
            metadata=metadata or {},
        )
        self._entries.append(entry)
        return entry

    def get_context_for_worker(
        self,
        worker_id: str,
        include_client_chat: bool = True,
        include_team_discussion: bool = True,
        include_execution: bool = True,
        max_entries: int = 50,
    ) -> str:
        """
        Get formatted context for a specific worker.

        This is what a worker sees when they need to understand
        the full context of the session. It's like getting
        "caught up" on a project.

        Args:
            worker_id: The worker who needs context
            include_client_chat: Include client↔manager conversation
            include_team_discussion: Include team discussion
            include_execution: Include execution results
            max_entries: Maximum number of entries to include

        Returns:
            Formatted context text suitable for LLM prompts
        """
        sections = []
        entries = self._entries[-max_entries:] if len(self._entries) > max_entries else self._entries

        # Group entries by phase
        phases: dict[str, list[TranscriptEntry]] = {}
        for entry in entries:
            if entry.phase not in phases:
                phases[entry.phase] = []
            phases[entry.phase].append(entry)

        # Build context sections
        if include_client_chat and "client_discussion" in phases:
            sections.append(self._format_phase(
                "Client ↔ Manager Discussion",
                phases["client_discussion"],
            ))

        if include_team_discussion:
            # Include both briefing and todo review
            for phase_name in ["team_briefing", "todo_review"]:
                if phase_name in phases:
                    label = "Team Briefing" if phase_name == "team_briefing" else "TODO Review"
                    sections.append(self._format_phase(label, phases[phase_name]))

        if include_execution and "execution" in phases:
            sections.append(self._format_phase(
                "Execution Progress",
                phases["execution"],
            ))

        # Also include GroupChannel transcript if available
        if self._channel:
            channel_text = self._channel.get_transcript_text()
            if channel_text and channel_text != "(No messages yet)":
                sections.append(f"===== Group Discussion =====\n{channel_text}")

        # Include contract info if available
        if self._contract:
            sections.append(self._format_contract())

        if not sections:
            return "(No context available yet)"

        return "\n\n".join(sections)

    def get_summary(self) -> str:
        """
        Get a concise summary of the session.

        Useful for workers who need a quick overview
        rather than the full context.
        """
        parts = []

        if self._contract:
            parts.append(f"Project: {self._contract.title}")
            parts.append(f"Description: {self._contract.description}")
            todo_count = len(self._contract.todos)
            done_count = sum(1 for t in self._contract.todos if t.status == "done")
            parts.append(f"Progress: {done_count}/{todo_count} tasks completed")

        if self._channel:
            parts.append(f"Discussion rounds: {self._channel.round_count}")
            parts.append(f"Messages: {self._channel.message_count}")

            concerns = self._channel.get_concerns()
            if concerns:
                parts.append(f"Open concerns: {len(concerns)}")

            decisions = self._channel.get_decisions()
            if decisions:
                parts.append(f"Decisions made: {len(decisions)}")

        # Count entries by phase
        phases: dict[str, int] = {}
        for entry in self._entries:
            phases[entry.phase] = phases.get(entry.phase, 0) + 1

        if phases:
            parts.append("Phases: " + ", ".join(f"{k} ({v})" for k, v in phases.items()))

        return "\n".join(parts) if parts else "(Session just started)"

    def get_decisions(self) -> list[str]:
        """Get all decisions made in this session."""
        decisions = []

        # From transcript entries
        for entry in self._entries:
            if entry.entry_type == "decision":
                decisions.append(entry.content)
            if "decisions" in entry.metadata:
                decisions.extend(entry.metadata["decisions"])

        # From channel
        if self._channel:
            decisions.extend(self._channel.get_decisions())

        return decisions

    def get_concerns(self) -> list[dict[str, Any]]:
        """Get all concerns raised in this session."""
        concerns = []

        for entry in self._entries:
            if entry.entry_type == "concern":
                concerns.append(entry.to_dict())

        if self._channel:
            concerns.extend(self._channel.get_concerns())

        return concerns

    def get_worker_progress(self, worker_id: str) -> dict[str, Any]:
        """
        Get the progress of a specific worker in this session.

        Useful for workers to understand what their teammates
        have been working on.
        """
        worker_entries = [
            e for e in self._entries
            if e.from_id == worker_id
        ]

        return {
            "worker_id": worker_id,
            "total_entries": len(worker_entries),
            "phases_involved": list(set(e.phase for e in worker_entries)),
            "recent_activity": [e.to_dict() for e in worker_entries[-5:]],
        }

    def _format_phase(self, label: str, entries: list[TranscriptEntry]) -> str:
        """Format a phase's entries for display."""
        lines = [f"===== {label} ====="]
        for entry in entries:
            prefix = f"[{entry.from_id}]"
            if entry.entry_type == "decision":
                prefix = f"[✅ DECISION by {entry.from_id}]"
            elif entry.entry_type == "concern":
                prefix = f"[⚠️ CONCERN from {entry.from_id}]"
            elif entry.entry_type == "result":
                prefix = f"[📊 RESULT from {entry.from_id}]"
            lines.append(f"{prefix} {entry.content}")
        return "\n".join(lines)

    def _format_contract(self) -> str:
        """Format the contract info for display."""
        if not self._contract:
            return ""

        lines = [f"===== Contract: {self._contract.title} ====="]
        lines.append(f"Description: {self._contract.description}")
        lines.append(f"Status: {self._contract.state.value}")
        lines.append("")
        lines.append("Tasks:")
        for todo in self._contract.todos:
            status = "✅" if todo.status == "done" else "🔵" if todo.status == "in_progress" else "⬜"
            assignee = f" → {todo.assigned_to}" if todo.assigned_to else ""
            lines.append(f"  {status} {todo.description}{assignee}")
        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the full transcript."""
        return {
            "session_id": self.session_id,
            "entries": [e.to_dict() for e in self._entries],
            "entry_count": len(self._entries),
            "contract": self._contract.to_dict() if self._contract else None,
        }

    @property
    def entry_count(self) -> int:
        """Total number of transcript entries."""
        return len(self._entries)
