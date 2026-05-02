"""
GroupChannel — Shared message board for team communication.

This is the "Slack channel" of kantorku. When a worker speaks
in the group channel, ALL other workers in the same session
can see and respond to the message.

Key design principles:
1. Every message is visible to all participants (no silos)
2. Workers can respond to specific messages (threaded)
3. Manager (Conductor) facilitates, summarizes, and decides
4. Full transcript is maintained for context retrieval

This mimics real office communication:
- In a meeting room, when someone speaks, everyone hears it
- People can build on each other's ideas
- Manager facilitates the discussion
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from kantorku.events.bus import EventBus
from kantorku.events.emitter import EventEmitter


class MessageType(str, Enum):
    """Types of messages in a group channel."""
    SPEAK = "speak"               # Normal message
    CONCERN = "concern"           # Worker raises a concern
    SUGGESTION = "suggestion"     # Worker makes a suggestion
    QUESTION = "question"         # Worker asks a question
    RESPONSE = "response"         # Response to another message
    AGREEMENT = "agreement"       # Worker agrees with something
    DISAGREEMENT = "disagreement" # Worker disagrees with something
    INFO = "info"                 # Informational message
    MANAGER_SUMMARY = "manager_summary"  # Manager summarizes discussion
    MANAGER_DECISION = "manager_decision" # Manager makes a final decision


@dataclass
class GroupMessage:
    """A single message in the group channel."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    session_id: str = ""
    from_id: str = ""           # Who sent this (worker_id or "conductor")
    message_type: MessageType = MessageType.SPEAK
    content: str = ""
    reply_to: str = ""          # ID of message being replied to (threaded)
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "session_id": self.session_id,
            "from_id": self.from_id,
            "message_type": self.message_type.value,
            "content": self.content,
            "reply_to": self.reply_to,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }


@dataclass
class DiscussionRound:
    """A single round of discussion in the group channel."""

    round_number: int = 0
    messages: list[GroupMessage] = field(default_factory=list)
    summary: str = ""
    decisions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "round_number": self.round_number,
            "messages": [m.to_dict() for m in self.messages],
            "summary": self.summary,
            "decisions": self.decisions,
        }


class GroupChannel:
    """
    GroupChannel — the shared message board for a session.

    This is where real office communication happens:
    - Workers speak and EVERYONE in the channel hears it
    - Workers can respond to each other's messages
    - The manager (Conductor) facilitates and summarizes
    - Full transcript is maintained for context

    Usage:
        channel = GroupChannel(session_id="s1", bus=bus)

        # Worker speaks (everyone sees it)
        await channel.speak(
            from_id="coder_backend",
            content="I think we need to change the DB schema first",
        )

        # Another worker responds
        await channel.respond(
            from_id="coder_frontend",
            content="Agreed, I'll adjust my API calls accordingly",
            reply_to=msg.id,
        )

        # Get full transcript for context
        transcript = channel.get_transcript()
    """

    def __init__(
        self,
        session_id: str,
        bus: EventBus,
        participants: list[str] | None = None,
    ) -> None:
        self.session_id = session_id
        self.bus = bus
        self.participants: set[str] = set(participants or [])
        self._messages: list[GroupMessage] = []
        self._rounds: list[DiscussionRound] = []
        self._current_round: int = 0
        self._message_index: dict[str, GroupMessage] = {}  # id → message

    def add_participant(self, participant_id: str) -> None:
        """Add a participant to the channel."""
        self.participants.add(participant_id)

    def remove_participant(self, participant_id: str) -> None:
        """Remove a participant from the channel."""
        self.participants.discard(participant_id)

    async def speak(
        self,
        from_id: str,
        content: str,
        message_type: MessageType = MessageType.SPEAK,
        reply_to: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> GroupMessage:
        """
        Post a message to the group channel.

        This message is visible to ALL participants in the channel.
        This is like speaking in a meeting room — everyone hears it.

        Args:
            from_id: Who is speaking (worker_id or "conductor")
            content: The message content
            message_type: Type of message (concern, suggestion, etc.)
            reply_to: ID of a message being replied to (for threading)
            metadata: Additional metadata

        Returns:
            The created GroupMessage
        """
        msg = GroupMessage(
            session_id=self.session_id,
            from_id=from_id,
            message_type=message_type,
            content=content,
            reply_to=reply_to,
            metadata=metadata or {},
        )

        self._messages.append(msg)
        self._message_index[msg.id] = msg

        # If this is part of a round, add to current round
        if self._current_round > 0 and self._rounds:
            self._rounds[-1].messages.append(msg)

        # Emit event to the bus so all participants are notified
        emitter = EventEmitter(self.bus, self.session_id)
        await emitter.worker_broadcast(
            from_id=from_id,
            content=content,
        )

        return msg

    async def respond(
        self,
        from_id: str,
        content: str,
        reply_to: str,
        message_type: MessageType = MessageType.RESPONSE,
        metadata: dict[str, Any] | None = None,
    ) -> GroupMessage:
        """
        Respond to a specific message in the channel.

        Like replying in a thread — everyone still sees it,
        but the threading relationship is preserved.

        Args:
            from_id: Who is responding
            content: The response content
            reply_to: ID of the message being replied to
            message_type: Type of response
            metadata: Additional metadata

        Returns:
            The created GroupMessage
        """
        return await self.speak(
            from_id=from_id,
            content=content,
            message_type=message_type,
            reply_to=reply_to,
            metadata=metadata,
        )

    async def manager_summary(
        self,
        content: str,
        decisions: list[str] | None = None,
    ) -> GroupMessage:
        """
        Manager posts a summary of the discussion so far.

        This is crucial for maintaining alignment — the manager
        summarizes what was discussed and what was decided,
        so every worker is on the same page.

        Args:
            content: The summary text
            decisions: List of decisions made

        Returns:
            The created GroupMessage
        """
        msg = await self.speak(
            from_id="conductor",
            content=content,
            message_type=MessageType.MANAGER_SUMMARY,
            metadata={"decisions": decisions or []},
        )

        if self._current_round > 0 and self._rounds:
            self._rounds[-1].summary = content
            self._rounds[-1].decisions = decisions or []

        return msg

    async def manager_decision(
        self,
        content: str,
        decisions: list[str],
    ) -> GroupMessage:
        """
        Manager makes a final decision after discussion.

        This signals that the discussion has reached a conclusion.

        Args:
            content: The decision explanation
            decisions: List of final decisions

        Returns:
            The created GroupMessage
        """
        return await self.speak(
            from_id="conductor",
            content=content,
            message_type=MessageType.MANAGER_DECISION,
            metadata={"decisions": decisions},
        )

    def start_round(self) -> int:
        """
        Start a new round of discussion.

        Returns:
            The round number
        """
        self._current_round += 1
        round_obj = DiscussionRound(round_number=self._current_round)
        self._rounds.append(round_obj)
        return self._current_round

    def end_round(self, summary: str = "", decisions: list[str] | None = None) -> DiscussionRound:
        """
        End the current round of discussion.

        Args:
            summary: Summary of the round
            decisions: Decisions made in this round

        Returns:
            The completed DiscussionRound
        """
        if not self._rounds:
            return DiscussionRound()

        current = self._rounds[-1]
        current.summary = summary
        current.decisions = decisions or []
        return current

    def get_transcript(
        self,
        since_round: int = 0,
        participant_filter: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Get the full transcript of the group channel.

        This is what workers use to understand the full context
        of what has been discussed. Like reading a Slack channel history.

        Args:
            since_round: Only get messages from this round onwards (0 = all)
            participant_filter: Only get messages from this participant

        Returns:
            List of message dicts
        """
        messages = self._messages

        if since_round > 0:
            # Filter to messages from the specified round onwards
            round_messages = []
            for round_obj in self._rounds:
                if round_obj.round_number >= since_round:
                    round_messages.extend(round_obj.messages)
            messages = round_messages

        if participant_filter:
            messages = [m for m in messages if m.from_id == participant_filter]

        return [m.to_dict() for m in messages]

    def get_transcript_text(
        self,
        since_round: int = 0,
        participant_filter: str | None = None,
    ) -> str:
        """
        Get the transcript as formatted text, suitable for
        including in LLM prompts.

        Args:
            since_round: Only get messages from this round onwards
            participant_filter: Only get messages from this participant

        Returns:
            Formatted transcript text
        """
        messages = self.get_transcript(since_round, participant_filter)
        if not messages:
            return "(No messages yet)"

        lines = []
        for msg in messages:
            from_id = msg["from_id"]
            msg_type = msg["message_type"]
            content = msg["content"]
            reply_to = msg.get("reply_to", "")

            prefix = f"[{from_id}]"
            if msg_type == "concern":
                prefix = f"[{from_id} ⚠️ CONCERN]"
            elif msg_type == "suggestion":
                prefix = f"[{from_id} 💡 SUGGESTION]"
            elif msg_type == "question":
                prefix = f"[{from_id} ❓ QUESTION]"
            elif msg_type == "manager_summary":
                prefix = f"[📋 MANAGER SUMMARY]"
            elif msg_type == "manager_decision":
                prefix = f"[✅ MANAGER DECISION]"
            elif msg_type == "agreement":
                prefix = f"[{from_id} ✅ AGREE]"
            elif msg_type == "disagreement":
                prefix = f"[{from_id} ❌ DISAGREE]"
            elif msg_type == "response" and reply_to:
                prefix = f"[{from_id} → reply to {reply_to}]"

            lines.append(f"{prefix} {content}")

        return "\n".join(lines)

    def get_thread(self, message_id: str) -> list[dict[str, Any]]:
        """
        Get all messages in a thread (original + all replies).

        Args:
            message_id: The root message ID

        Returns:
            List of message dicts in the thread
        """
        thread = []
        root = self._message_index.get(message_id)
        if root:
            thread.append(root.to_dict())

        # Find all replies
        for msg in self._messages:
            if msg.reply_to == message_id:
                thread.append(msg.to_dict())

        return thread

    def get_round_summaries(self) -> list[dict[str, Any]]:
        """Get summaries of all discussion rounds."""
        return [r.to_dict() for r in self._rounds if r.summary]

    def get_concerns(self) -> list[dict[str, Any]]:
        """Get all concerns raised in the channel."""
        return [
            m.to_dict() for m in self._messages
            if m.message_type == MessageType.CONCERN
        ]

    def get_suggestions(self) -> list[dict[str, Any]]:
        """Get all suggestions made in the channel."""
        return [
            m.to_dict() for m in self._messages
            if m.message_type == MessageType.SUGGESTION
        ]

    def get_decisions(self) -> list[str]:
        """Get all decisions made across all rounds and messages."""
        decisions = []
        # From round summaries
        for round_obj in self._rounds:
            decisions.extend(round_obj.decisions)
        # From individual messages (MANAGER_SUMMARY and MANAGER_DECISION)
        for msg in self._messages:
            if msg.message_type in (MessageType.MANAGER_SUMMARY, MessageType.MANAGER_DECISION):
                if "decisions" in msg.metadata:
                    decisions.extend(msg.metadata["decisions"])
        return decisions

    @property
    def message_count(self) -> int:
        """Total number of messages in the channel."""
        return len(self._messages)

    @property
    def round_count(self) -> int:
        """Total number of discussion rounds."""
        return len(self._rounds)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the entire channel state."""
        return {
            "session_id": self.session_id,
            "participants": list(self.participants),
            "message_count": self.message_count,
            "round_count": self.round_count,
            "rounds": [r.to_dict() for r in self._rounds],
            "transcript": [m.to_dict() for m in self._messages],
        }
