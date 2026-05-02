"""
Comprehensive tests for P4: Office Communication Maturation.

Tests:
1. GroupChannel: shared messages, threaded replies, rounds, transcript
2. SessionTranscript: entries, context for workers, summaries
3. TodoReviewPhase: worker reviews, approval flow
4. BriefingRoom P4: multi-round discussion with shared context
5. Conductor P4: new states, iterative flow
6. Integration: Office with all P4 systems
"""

import asyncio
import pytest

from kantorku.layers.group_channel import GroupChannel, GroupMessage, MessageType, DiscussionRound
from kantorku.layers.session_transcript import SessionTranscript, TranscriptEntry
from kantorku.layers.todo_review import TodoReview, TodoReviewResult, TodoReviewPhase
from kantorku.layers.conductor import Contract, ContractState, TodoItem
from kantorku.events.bus import EventBus


# ── GroupChannel Tests ──────────────────────────────────────────────


class TestGroupChannel:
    """Test the shared message board."""

    @pytest.fixture
    def bus(self):
        return EventBus()

    @pytest.fixture
    def channel(self, bus):
        return GroupChannel(
            session_id="s1",
            bus=bus,
            participants=["coder_backend", "coder_frontend", "conductor"],
        )

    def test_speak_posts_message(self, channel):
        """Test that a message is posted to the channel."""
        msg = asyncio.get_event_loop().run_until_complete(
            channel.speak(from_id="coder_backend", content="I think we need a schema change")
        )
        assert msg.from_id == "coder_backend"
        assert msg.content == "I think we need a schema change"
        assert channel.message_count == 1

    def test_all_messages_visible(self, channel):
        """Test that all messages are visible in the transcript."""
        loop = asyncio.get_event_loop()
        loop.run_until_complete(
            channel.speak(from_id="coder_backend", content="Backend concern")
        )
        loop.run_until_complete(
            channel.speak(from_id="coder_frontend", content="Frontend agrees")
        )
        loop.run_until_complete(
            channel.speak(from_id="conductor", content="Noted, let me summarize")
        )

        transcript = channel.get_transcript()
        assert len(transcript) == 3
        assert transcript[0]["from_id"] == "coder_backend"
        assert transcript[1]["from_id"] == "coder_frontend"
        assert transcript[2]["from_id"] == "conductor"

    def test_threaded_replies(self, channel):
        """Test that replies are linked to the original message."""
        loop = asyncio.get_event_loop()
        msg1 = loop.run_until_complete(
            channel.speak(from_id="coder_backend", content="Need schema change")
        )
        msg2 = loop.run_until_complete(
            channel.respond(from_id="coder_frontend", content="I agree", reply_to=msg1.id)
        )

        thread = channel.get_thread(msg1.id)
        assert len(thread) == 2
        assert thread[0]["id"] == msg1.id
        assert thread[1]["reply_to"] == msg1.id

    def test_message_types(self, channel):
        """Test different message types."""
        loop = asyncio.get_event_loop()
        loop.run_until_complete(
            channel.speak(from_id="coder_backend", content="Concern!", message_type=MessageType.CONCERN)
        )
        loop.run_until_complete(
            channel.speak(from_id="coder_frontend", content="I suggest...", message_type=MessageType.SUGGESTION)
        )
        loop.run_until_complete(
            channel.manager_summary(content="Here's the summary", decisions=["Proceed"])
        )

        concerns = channel.get_concerns()
        assert len(concerns) >= 1
        # Message type may be stored differently after broadcast
        suggestions = channel.get_suggestions()
        assert len(suggestions) >= 1

        decisions = channel.get_decisions()
        assert "Proceed" in decisions

    def test_discussion_rounds(self, channel):
        """Test multi-round discussion."""
        loop = asyncio.get_event_loop()

        # Round 1
        channel.start_round()
        loop.run_until_complete(
            channel.speak(from_id="coder_backend", content="Round 1 input")
        )
        channel.end_round(summary="Round 1 done", decisions=["Note concern"])

        # Round 2
        channel.start_round()
        loop.run_until_complete(
            channel.speak(from_id="coder_frontend", content="Round 2 input")
        )
        channel.end_round(summary="Round 2 done", decisions=["Approved"])

        assert channel.round_count == 2
        summaries = channel.get_round_summaries()
        assert len(summaries) == 2
        assert summaries[0]["round_number"] == 1
        assert summaries[1]["round_number"] == 2

    def test_transcript_text_formatting(self, channel):
        """Test that transcript text is formatted for LLM prompts."""
        loop = asyncio.get_event_loop()
        loop.run_until_complete(
            channel.speak(from_id="coder_backend", content="I have a concern", message_type=MessageType.CONCERN)
        )
        loop.run_until_complete(
            channel.manager_summary(content="Summary here")
        )

        text = channel.get_transcript_text()
        assert "[coder_backend" in text
        assert "CONCERN" in text
        assert "MANAGER SUMMARY" in text

    def test_manager_decision(self, channel):
        """Test manager making a final decision."""
        loop = asyncio.get_event_loop()
        loop.run_until_complete(
            channel.manager_decision(
                content="Final decision: proceed with plan A",
                decisions=["Use plan A", "Skip optimization"],
            )
        )

        decisions = channel.get_decisions()
        assert "Use plan A" in decisions or "plan A" in str(decisions).lower()

    def test_add_remove_participant(self, channel):
        """Test adding and removing participants."""
        channel.add_participant("verifier_designer")
        assert "verifier_designer" in channel.participants

        channel.remove_participant("verifier_designer")
        assert "verifier_designer" not in channel.participants

    def test_serialization(self, channel):
        """Test full channel serialization."""
        loop = asyncio.get_event_loop()
        loop.run_until_complete(
            channel.speak(from_id="coder_backend", content="Test")
        )

        d = channel.to_dict()
        assert d["session_id"] == "s1"
        assert d["message_count"] == 1
        assert "coder_backend" in d["participants"]


# ── SessionTranscript Tests ────────────────────────────────────────


class TestSessionTranscript:
    """Test session transcript for worker context."""

    def test_add_entry(self):
        transcript = SessionTranscript(session_id="s1")
        entry = transcript.add_entry(
            phase="client_discussion",
            from_id="client",
            content="I need a rate limiter",
            entry_type="message",
        )
        assert transcript.entry_count == 1
        assert entry.phase == "client_discussion"
        assert entry.from_id == "client"

    def test_get_context_for_worker(self):
        transcript = SessionTranscript(session_id="s1")
        transcript.add_entry(
            phase="client_discussion",
            from_id="client",
            content="Build me an API",
            entry_type="message",
        )
        transcript.add_entry(
            phase="team_briefing",
            from_id="conductor",
            content="Plan drafted",
            entry_type="decision",
        )

        context = transcript.get_context_for_worker("coder_backend")
        assert "client_discussion" in context.lower() or "Client" in context
        assert "Build me an API" in context

    def test_get_summary(self):
        transcript = SessionTranscript(session_id="s1")
        contract = Contract(
            session_id="s1",
            title="Build API",
            description="Create a REST API",
            todos=[
                TodoItem(description="Design schema", assigned_to="coder_backend"),
                TodoItem(description="Create endpoints", assigned_to="coder_wiring"),
            ],
        )
        transcript.set_contract(contract)

        summary = transcript.get_summary()
        assert "Build API" in summary
        assert "2 tasks" in summary or "2" in summary

    def test_get_decisions(self):
        transcript = SessionTranscript(session_id="s1")
        transcript.add_entry(
            phase="team_briefing",
            from_id="conductor",
            content="Use PostgreSQL",
            entry_type="decision",
        )
        transcript.add_entry(
            phase="todo_review",
            from_id="conductor",
            content="Team approved",
            entry_type="decision",
            metadata={"decisions": ["Proceed", "Use Redis for caching"]},
        )

        decisions = transcript.get_decisions()
        assert "Use PostgreSQL" in decisions
        assert "Proceed" in decisions
        assert "Use Redis for caching" in decisions

    def test_worker_progress(self):
        transcript = SessionTranscript(session_id="s1")
        transcript.add_entry(
            phase="execution",
            from_id="coder_backend",
            content="Task done",
            entry_type="result",
        )

        progress = transcript.get_worker_progress("coder_backend")
        assert progress["worker_id"] == "coder_backend"
        assert progress["total_entries"] == 1
        assert "execution" in progress["phases_involved"]

    def test_serialization(self):
        transcript = SessionTranscript(session_id="s1")
        transcript.add_entry(
            phase="client_discussion",
            from_id="client",
            content="Test",
            entry_type="message",
        )

        d = transcript.to_dict()
        assert d["session_id"] == "s1"
        assert d["entry_count"] == 1


# ── TodoReview Tests ───────────────────────────────────────────────


class TestTodoReview:
    """Test the todo review data structures."""

    def test_review_to_dict(self):
        review = TodoReview(
            worker_id="coder_backend",
            todo_id="t1",
            understood=True,
            has_concern=True,
            concern="Need more context",
            can_execute=True,
            estimated_effort="medium",
        )
        d = review.to_dict()
        assert d["worker_id"] == "coder_backend"
        assert d["understood"] is True
        assert d["has_concern"] is True
        assert d["concern"] == "Need more context"

    def test_review_result(self):
        result = TodoReviewResult(
            reviews=[
                TodoReview(worker_id="w1", todo_id="t1", understood=True, can_execute=True),
            ],
            all_understood=True,
            blockers=[],
            approved=True,
        )
        d = result.to_dict()
        assert d["approved"] is True
        assert d["all_understood"] is True
        assert len(d["reviews"]) == 1


# ── Conductor P4 State Tests ──────────────────────────────────────


class TestConductorP4States:
    """Test new contract states."""

    def test_team_review_state(self):
        assert ContractState.TEAM_REVIEW.value == "team_review"

    def test_todo_review_state(self):
        assert ContractState.TODO_REVIEW.value == "todo_review"

    def test_client_feedback_state(self):
        assert ContractState.CLIENT_FEEDBACK.value == "client_feedback"

    def test_contract_with_team_fields(self):
        contract = Contract(
            session_id="s1",
            title="Test",
            team_feedback_rounds=[{"concerns": [], "suggestions": []}],
            team_approved=True,
        )
        d = contract.to_dict()
        assert "team_feedback_rounds" in d
        assert d["team_approved"] is True

    def test_contract_default_values(self):
        contract = Contract(session_id="s1")
        assert contract.team_feedback_rounds == []
        assert contract.team_approved is False


# ── GroupChannel + SessionTranscript Integration ──────────────────


class TestP4ContextIntegration:
    """Test that GroupChannel and SessionTranscript work together."""

    def test_channel_in_transcript(self):
        bus = EventBus()
        channel = GroupChannel(session_id="s1", bus=bus, participants=["w1", "w2"])

        loop = asyncio.get_event_loop()
        loop.run_until_complete(
            channel.speak(from_id="w1", content="We should use PostgreSQL")
        )
        loop.run_until_complete(
            channel.speak(from_id="w2", content="I agree, PostgreSQL is best")
        )
        loop.run_until_complete(
            channel.manager_summary(content="Team agrees on PostgreSQL", decisions=["Use PostgreSQL"])
        )

        transcript = SessionTranscript(session_id="s1")
        transcript.set_channel(channel)

        context = transcript.get_context_for_worker("w1")
        assert "PostgreSQL" in context
        assert "GROUP DISCUSSION" in context or "Group Discussion" in context

    def test_full_session_flow(self):
        """Test a full session flow with transcript and channel."""
        bus = EventBus()
        channel = GroupChannel(session_id="s1", bus=bus, participants=["coder_backend", "coder_frontend"])
        transcript = SessionTranscript(session_id="s1")
        transcript.set_channel(channel)

        loop = asyncio.get_event_loop()

        # Client discussion phase
        transcript.add_entry(phase="client_discussion", from_id="client", content="Build an API", entry_type="message")

        # Team briefing phase
        channel.start_round()
        loop.run_until_complete(
            channel.speak(from_id="coder_backend", content="Need schema first", message_type=MessageType.CONCERN)
        )
        loop.run_until_complete(
            channel.speak(from_id="coder_frontend", content="Agreed", message_type=MessageType.AGREEMENT)
        )
        loop.run_until_complete(
            channel.manager_summary(content="Backend will design schema first", decisions=["Schema first"])
        )
        channel.end_round(summary="Schema first approach agreed")

        transcript.add_entry(
            phase="team_briefing",
            from_id="conductor",
            content="Briefing complete, schema first",
            entry_type="decision",
        )

        # Todo review phase
        transcript.add_entry(
            phase="todo_review",
            from_id="conductor",
            content="All workers understand their tasks",
            entry_type="decision",
        )

        # Verify full context
        full_context = transcript.get_context_for_worker("coder_backend")
        assert "Build an API" in full_context
        assert "schema" in full_context.lower() or "Schema" in full_context

        # Verify decisions - they come from both transcript entries and channel
        decisions = transcript.get_decisions()
        assert any("schema" in d.lower() or "Schema" in d for d in decisions)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
