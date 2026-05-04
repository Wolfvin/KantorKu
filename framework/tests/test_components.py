"""
Comprehensive unit tests for kantorku components.

Tests:
- STM engine: hedge_reducer, direct_mode, casual_mode, capitalization fix
- AutoTune: classify, analyze, feedback, EMA persistence, provider filtering
- BaseWorker: conversation history (_conv_history), context building, clear_conversation
- SessionTranscript: add_entry, get_context_for_worker, get_summary, get_decisions
- DAGResolver: resolve, get_critical_path, cycle detection

Each test is self-contained and does not require LLM API calls.
Uses mocks where needed.
"""

from __future__ import annotations

import asyncio
import json
import os
import tempfile
import unittest
from dataclasses import dataclass
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

# ── STM Tests ──────────────────────────────────────────────────────


class TestSTMEngine(unittest.TestCase):
    """Test the STM (Semantic Transformation Modules) engine."""

    def test_hedge_reducer_removes_hedging(self):
        """hedge_reducer should remove hedging language like 'I think', 'maybe'."""
        from kantorku.redteam.stm import STMEngine, STMModule

        stm = STMEngine()
        result = stm.transform(
            "I think perhaps you could try using asyncio",
            modules=[STMModule.HEDGE_REDUCER],
        )
        self.assertNotIn("I think", result.transformed)
        self.assertNotIn("perhaps", result.transformed)
        # Capitalization fix may change 'you' to 'You'
        self.assertIn("you could try using asyncio", result.transformed.lower())

    def test_hedge_reducer_removes_in_my_opinion(self):
        """hedge_reducer should remove 'In my opinion' prefix."""
        from kantorku.redteam.stm import STMEngine, STMModule

        stm = STMEngine()
        result = stm.transform(
            "In my opinion, the architecture needs refactoring",
            modules=[STMModule.HEDGE_REDUCER],
        )
        self.assertNotIn("In my opinion", result.transformed)
        # Capitalization fix makes 'the' -> 'The'
        self.assertIn("architecture needs refactoring", result.transformed)

    def test_direct_mode_removes_preambles(self):
        """direct_mode should remove preambles like 'Sure,', 'Of course,'."""
        from kantorku.redteam.stm import STMEngine, STMModule

        stm = STMEngine()
        result = stm.transform(
            "Sure, here's the implementation.",
            modules=[STMModule.DIRECT_MODE],
        )
        self.assertNotIn("Sure", result.transformed)
        # Capitalization fix changes 'here' -> 'Here'
        self.assertIn("here's the implementation", result.transformed.lower())

    def test_direct_mode_removes_great_question(self):
        """direct_mode should remove 'Great question!' preamble."""
        from kantorku.redteam.stm import STMEngine, STMModule

        stm = STMEngine()
        result = stm.transform(
            "Great question! The answer is 42.",
            modules=[STMModule.DIRECT_MODE],
        )
        self.assertNotIn("Great question", result.transformed)
        self.assertIn("The answer is 42", result.transformed)

    def test_casual_mode_replaces_formal(self):
        """casual_mode should replace formal words with casual equivalents."""
        from kantorku.redteam.stm import STMEngine, STMModule

        stm = STMEngine()
        result = stm.transform(
            "However, you should utilize the API. Furthermore, purchase a license.",
            modules=[STMModule.CASUAL_MODE],
        )
        self.assertNotIn("However", result.transformed)
        self.assertNotIn("utilize", result.transformed)
        self.assertNotIn("Furthermore", result.transformed)
        self.assertNotIn("Purchase", result.transformed)
        self.assertIn("But", result.transformed)
        self.assertIn("Use", result.transformed)

    def test_capitalization_fix(self):
        """STM should capitalize sentence-initial lowercase letters after transforms."""
        from kantorku.redteam.stm import STMEngine, STMModule

        stm = STMEngine()
        result = stm.transform(
            "perhaps you should try this. maybe it works.",
            modules=[STMModule.HEDGE_REDUCER],
        )
        # After removing "perhaps " and "maybe ", remaining text should be capitalized
        # "you should try this. it works."
        # Capitalization fix should make sentence starts uppercase
        self.assertTrue(
            result.transformed.lstrip()[0].isupper()
            or result.transformed == "",
            f"Expected capitalized start, got: {result.transformed!r}",
        )

    def test_transform_returns_stm_result(self):
        """transform should return an STMResult with metadata."""
        from kantorku.redteam.stm import STMEngine, STMResult

        stm = STMEngine()
        result = stm.transform("I think maybe test this")
        self.assertIsInstance(result, STMResult)
        self.assertEqual(result.original, "I think maybe test this")
        self.assertNotEqual(result.original, result.transformed)
        self.assertIsInstance(result.modules_applied, list)
        self.assertIsInstance(result.changes_count, int)

    def test_transform_with_string_module_names(self):
        """transform should accept module names as strings."""
        from kantorku.redteam.stm import STMEngine

        stm = STMEngine()
        result = stm.transform(
            "I think maybe test this",
            modules=["hedge_reducer"],
        )
        self.assertNotIn("I think", result.transformed)

    def test_transform_empty_text(self):
        """transform should handle empty text gracefully."""
        from kantorku.redteam.stm import STMEngine

        stm = STMEngine()
        result = stm.transform("")
        self.assertEqual(result.transformed, "")

    def test_get_modules(self):
        """get_modules should list available modules."""
        from kantorku.redteam.stm import STMEngine

        stm = STMEngine()
        modules = stm.get_modules()
        self.assertEqual(len(modules), 3)
        module_ids = [m["id"] for m in modules]
        self.assertIn("hedge_reducer", module_ids)
        self.assertIn("direct_mode", module_ids)
        self.assertIn("casual_mode", module_ids)


# ── AutoTune Tests ──────────────────────────────────────────────────


class TestAutoTune(unittest.TestCase):
    """Test the AutoTune context-adaptive sampling engine."""

    def test_classify_code(self):
        """classify should detect code-related text."""
        from kantorku.redteam.autotune import AutoTune, ContextType

        at = AutoTune(worker_id="test")
        ctx_type, confidence = at.classify("Write a Python function to sort a list")
        self.assertEqual(ctx_type, ContextType.CODE)
        self.assertGreater(confidence, 0.0)

    def test_classify_creative(self):
        """classify should detect creative text."""
        from kantorku.redteam.autotune import AutoTune, ContextType

        at = AutoTune(worker_id="test")
        ctx_type, confidence = at.classify("Write a story about a dragon")
        self.assertEqual(ctx_type, ContextType.CREATIVE)

    def test_classify_analytical(self):
        """classify should detect analytical text."""
        from kantorku.redteam.autotune import AutoTune, ContextType

        at = AutoTune(worker_id="test")
        ctx_type, confidence = at.classify("Analyze the pros and cons of microservices")
        self.assertEqual(ctx_type, ContextType.ANALYTICAL)

    def test_classify_conversational(self):
        """classify should detect conversational text."""
        from kantorku.redteam.autotune import AutoTune, ContextType

        at = AutoTune(worker_id="test")
        ctx_type, confidence = at.classify("hey, what's up?")
        self.assertEqual(ctx_type, ContextType.CONVERSATIONAL)

    def test_classify_review(self):
        """classify should detect review-related text."""
        from kantorku.redteam.autotune import AutoTune, ContextType

        at = AutoTune(worker_id="test")
        ctx_type, confidence = at.classify("Review this code for best practices and clean code violations")
        self.assertEqual(ctx_type, ContextType.REVIEW)

    def test_classify_worker_bias(self):
        """classify should apply worker identity bias."""
        from kantorku.redteam.autotune import AutoTune, ContextType

        at = AutoTune(worker_id="coder_backend")
        ctx_type, confidence = at.classify("test message")
        # coder_backend has CODE bias, so it should lean toward CODE
        self.assertEqual(ctx_type, ContextType.CODE)

    def test_analyze_returns_result(self):
        """analyze should return AutoTuneResult with params."""
        from kantorku.redteam.autotune import AutoTune, AutoTuneResult

        at = AutoTune(worker_id="test")
        result = at.analyze("Write a Python function")
        self.assertIsInstance(result, AutoTuneResult)
        self.assertIsNotNone(result.params)
        self.assertGreater(result.confidence, 0.0)
        self.assertIsNotNone(result.context_type)

    def test_analyze_strategy_override(self):
        """analyze with strategy should use fixed profile."""
        from kantorku.redteam.autotune import AutoTune

        at = AutoTune(worker_id="test")
        result = at.analyze("anything", strategy="precise")
        self.assertEqual(result.strategy, "precise")
        self.assertAlmostEqual(result.params.temperature, 0.2, places=1)

    def test_analyze_dict_history(self):
        """analyze should handle dict-style history with 'content' key."""
        from kantorku.redteam.autotune import AutoTune

        at = AutoTune(worker_id="test")
        history = [{"role": "user", "content": "debug this error"}]
        result = at.analyze("fix the bug", history=history)
        self.assertIsNotNone(result)

    def test_feedback_updates_ema(self):
        """feedback should update EMA (Exponential Moving Average)."""
        from kantorku.redteam.autotune import AutoTune, ContextType, SamplingParams

        at = AutoTune(worker_id="test")
        params = SamplingParams(temperature=0.3, top_p=0.85)

        # Submit positive feedback
        at.feedback(ContextType.CODE, params, positive=True)

        # Check EMA was updated
        self.assertIn(ContextType.CODE, at._positive_ema)
        self.assertIn("temperature", at._positive_ema[ContextType.CODE])
        self.assertGreater(at._sample_counts.get(ContextType.CODE, 0), 0)

    def test_feedback_negative_updates_negative_ema(self):
        """Negative feedback should update negative EMA."""
        from kantorku.redteam.autotune import AutoTune, ContextType, SamplingParams

        at = AutoTune(worker_id="test")
        params = SamplingParams(temperature=1.5, top_p=0.98)

        at.feedback(ContextType.CODE, params, positive=False)

        self.assertIn(ContextType.CODE, at._negative_ema)
        self.assertIn("temperature", at._negative_ema[ContextType.CODE])

    def test_ema_persistence(self):
        """EMA state should persist to disk and be loadable."""
        from kantorku.redteam.autotune import AutoTune, ContextType, SamplingParams

        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "ema_test.json")

            # Write EMA state
            at1 = AutoTune(worker_id="test", persist_path=path)
            params = SamplingParams(temperature=0.3)
            at1.feedback(ContextType.CODE, params, positive=True)
            self.assertTrue(os.path.exists(path))

            # Load EMA state in new instance
            at2 = AutoTune(worker_id="test", persist_path=path)
            self.assertIn(ContextType.CODE, at2._positive_ema)
            self.assertAlmostEqual(
                at2._positive_ema[ContextType.CODE]["temperature"],
                at1._positive_ema[ContextType.CODE]["temperature"],
                places=4,
            )

    def test_provider_filtering_anthropic(self):
        """filter_params_for_provider should only return Anthropic-supported params."""
        from kantorku.redteam.autotune import AutoTune, SamplingParams

        at = AutoTune(worker_id="test")
        params = SamplingParams(temperature=0.5, top_p=0.9, top_k=50)
        filtered = at.filter_params_for_provider(params, "anthropic")

        self.assertIn("temperature", filtered)
        self.assertIn("top_p", filtered)
        self.assertNotIn("top_k", filtered)
        self.assertNotIn("frequency_penalty", filtered)

    def test_provider_filtering_ollama(self):
        """filter_params_for_provider should include repetition_penalty for Ollama."""
        from kantorku.redteam.autotune import AutoTune, SamplingParams

        at = AutoTune(worker_id="test")
        params = SamplingParams(temperature=0.5, top_p=0.9, top_k=50, repetition_penalty=1.1)
        filtered = at.filter_params_for_provider(params, "ollama")

        self.assertIn("temperature", filtered)
        self.assertIn("top_p", filtered)
        self.assertIn("top_k", filtered)
        self.assertIn("repetition_penalty", filtered)

    def test_provider_filtering_unknown(self):
        """filter_params_for_provider should default to temperature + top_p for unknown provider."""
        from kantorku.redteam.autotune import AutoTune, SamplingParams

        at = AutoTune(worker_id="test")
        params = SamplingParams(temperature=0.5, top_p=0.9, top_k=50)
        filtered = at.filter_params_for_provider(params, "unknown_provider")

        self.assertIn("temperature", filtered)
        self.assertIn("top_p", filtered)

    def test_sampling_params_clamp(self):
        """SamplingParams.clamp should bound all values."""
        from kantorku.redteam.autotune import SamplingParams

        params = SamplingParams(temperature=5.0, top_p=-1.0, top_k=0)
        clamped = params.clamp()
        self.assertLessEqual(clamped.temperature, 2.0)
        self.assertGreaterEqual(clamped.top_p, 0.0)
        self.assertGreaterEqual(clamped.top_k, 1)

    def test_sampling_params_to_dict(self):
        """SamplingParams.to_dict should return a dict with rounded values."""
        from kantorku.redteam.autotune import SamplingParams

        params = SamplingParams(temperature=0.12345, top_p=0.8765)
        d = params.to_dict()
        self.assertIsInstance(d, dict)
        self.assertEqual(d["temperature"], 0.123)
        self.assertEqual(d["top_p"], round(0.8765, 3))


# ── BaseWorker Tests ─────────────────────────────────────────────────


class TestBaseWorker(unittest.TestCase):
    """Test BaseWorker conversation history and context building."""

    def _make_worker(self) -> Any:
        """Create a BaseWorker with mocked dependencies."""
        from kantorku.worker.base import BaseWorker
        from kantorku.worker.identity import WorkerIdentity, WorkerAPI

        identity = WorkerIdentity(
            id="test_worker",
            model="ollama/llama3",
            squad="test_squad",
            role="test role",
            skill_md="You are a test worker.",
        )
        router = MagicMock()
        bus = MagicMock()
        worker = BaseWorker(identity=identity, router=router, bus=bus)
        return worker

    def test_conversation_history_starts_empty(self):
        """_conv_history should start empty."""
        worker = self._make_worker()
        self.assertEqual(worker._conv_history, {})

    def test_clear_conversation_specific_session(self):
        """clear_conversation with session_id should clear only that session."""
        worker = self._make_worker()
        worker._conv_history["session1"] = [
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "hi"},
        ]
        worker._conv_history["session2"] = [
            {"role": "user", "content": "world"},
        ]

        worker.clear_conversation("session1")
        self.assertNotIn("session1", worker._conv_history)
        self.assertIn("session2", worker._conv_history)

    def test_clear_conversation_all_sessions(self):
        """clear_conversation with no args should clear all sessions."""
        worker = self._make_worker()
        worker._conv_history["session1"] = [{"role": "user", "content": "hello"}]
        worker._conv_history["session2"] = [{"role": "user", "content": "world"}]

        worker.clear_conversation()
        self.assertEqual(worker._conv_history, {})

    def test_build_context_section_empty(self):
        """_build_context_section should return empty string for no context."""
        from kantorku.worker.base import Task

        worker = self._make_worker()
        task = Task(instruction="test", context={})
        result = worker._build_context_section(task)
        self.assertEqual(result, "")

    def test_build_context_section_session_context(self):
        """_build_context_section should include session_context."""
        from kantorku.worker.base import Task

        worker = self._make_worker()
        task = Task(
            instruction="test",
            context={"session_context": "Previous discussion about APIs"},
        )
        result = worker._build_context_section(task)
        # The output uses 'Session context' with a space, not 'session_context' as key
        self.assertIn("session context", result.lower())
        self.assertIn("Previous discussion about APIs", result)

    def test_build_context_section_team_decisions(self):
        """_build_context_section should include team_decisions."""
        from kantorku.worker.base import Task

        worker = self._make_worker()
        task = Task(
            instruction="test",
            context={"team_decisions": ["Use REST API", "Use PostgreSQL"]},
        )
        result = worker._build_context_section(task)
        self.assertIn("Use REST API", result)
        self.assertIn("Use PostgreSQL", result)

    def test_build_context_section_contract(self):
        """_build_context_section should include contract info."""
        from kantorku.worker.base import Task

        worker = self._make_worker()
        task = Task(
            instruction="test",
            context={"contract": {"title": "Build Rate Limiter"}},
        )
        result = worker._build_context_section(task)
        self.assertIn("Build Rate Limiter", result)

    def test_get_conversation_summary_empty(self):
        """get_conversation_summary should return empty string for no history."""
        worker = self._make_worker()
        result = worker.get_conversation_summary("nonexistent_session")
        self.assertEqual(result, "")

    def test_get_conversation_summary_with_history(self):
        """get_conversation_summary should format conversation history."""
        worker = self._make_worker()
        worker._conv_history["session1"] = [
            {"role": "user", "content": "Build a rate limiter"},
            {"role": "assistant", "content": "I'll implement it with token bucket"},
        ]
        result = worker.get_conversation_summary("session1")
        self.assertIn("User: Build a rate limiter", result)
        self.assertIn("Assistant: I'll implement it with token bucket", result)

    def test_get_conversation_summary_truncates_long_messages(self):
        """get_conversation_summary should truncate messages longer than 300 chars."""
        worker = self._make_worker()
        long_msg = "x" * 400
        worker._conv_history["session1"] = [
            {"role": "user", "content": long_msg},
        ]
        result = worker.get_conversation_summary("session1")
        # Should be truncated to ~300 chars + "..."
        self.assertLessEqual(len(result.split(": ", 1)[1]), 310)

    def test_max_conversation_history_constant(self):
        """MAX_CONVERSATION_HISTORY should be a reasonable value."""
        from kantorku.worker.base import BaseWorker

        self.assertGreater(BaseWorker.MAX_CONVERSATION_HISTORY, 0)

    def test_worker_status_enum(self):
        """WorkerStatus should have all expected states."""
        from kantorku.worker.base import WorkerStatus

        self.assertEqual(WorkerStatus.IDLE.value, "idle")
        self.assertEqual(WorkerStatus.THINKING.value, "thinking")
        self.assertEqual(WorkerStatus.ACTIVE.value, "active")
        self.assertEqual(WorkerStatus.DONE.value, "done")
        self.assertEqual(WorkerStatus.FAILED.value, "failed")


# ── SessionTranscript Tests ──────────────────────────────────────────


class TestSessionTranscript(unittest.TestCase):
    """Test SessionTranscript session context tracking."""

    def test_add_entry(self):
        """add_entry should add a TranscriptEntry."""
        from kantorku.layers.session_transcript import SessionTranscript

        transcript = SessionTranscript(session_id="s1")
        entry = transcript.add_entry(
            phase="client_discussion",
            from_id="client",
            content="I need a rate limiter",
            entry_type="message",
        )
        self.assertEqual(entry.phase, "client_discussion")
        self.assertEqual(entry.from_id, "client")
        self.assertEqual(entry.content, "I need a rate limiter")
        self.assertEqual(transcript.entry_count, 1)

    def test_add_entry_multiple(self):
        """add_entry should accumulate entries."""
        from kantorku.layers.session_transcript import SessionTranscript

        transcript = SessionTranscript(session_id="s1")
        transcript.add_entry(phase="client_discussion", from_id="client", content="msg1")
        transcript.add_entry(phase="team_briefing", from_id="conductor", content="msg2")
        self.assertEqual(transcript.entry_count, 2)

    def test_add_entry_with_metadata(self):
        """add_entry should preserve metadata."""
        from kantorku.layers.session_transcript import SessionTranscript

        transcript = SessionTranscript(session_id="s1")
        entry = transcript.add_entry(
            phase="team_briefing",
            from_id="conductor",
            content="Briefing complete",
            entry_type="decision",
            metadata={"rounds": 3, "consensus": True},
        )
        self.assertEqual(entry.metadata["rounds"], 3)
        self.assertTrue(entry.metadata["consensus"])

    def test_get_context_for_worker(self):
        """get_context_for_worker should return formatted context."""
        from kantorku.layers.session_transcript import SessionTranscript

        transcript = SessionTranscript(session_id="s1")
        transcript.add_entry(
            phase="client_discussion",
            from_id="client",
            content="I need a rate limiter",
            entry_type="message",
        )
        context = transcript.get_context_for_worker("coder_backend")
        self.assertIn("client", context.lower())
        self.assertIn("rate limiter", context)

    def test_get_context_for_worker_empty(self):
        """get_context_for_worker should return placeholder for empty transcript."""
        from kantorku.layers.session_transcript import SessionTranscript

        transcript = SessionTranscript(session_id="s1")
        context = transcript.get_context_for_worker("coder_backend")
        self.assertIn("No context available", context)

    def test_get_summary(self):
        """get_summary should return a concise overview."""
        from kantorku.layers.session_transcript import SessionTranscript

        transcript = SessionTranscript(session_id="s1")
        transcript.add_entry(phase="client_discussion", from_id="client", content="msg1")
        transcript.add_entry(phase="team_briefing", from_id="conductor", content="msg2")

        summary = transcript.get_summary()
        self.assertIn("client_discussion", summary)
        self.assertIn("team_briefing", summary)

    def test_get_summary_empty(self):
        """get_summary for empty transcript should indicate just started."""
        from kantorku.layers.session_transcript import SessionTranscript

        transcript = SessionTranscript(session_id="s1")
        summary = transcript.get_summary()
        self.assertIn("just started", summary)

    def test_get_decisions(self):
        """get_decisions should return all decision entries."""
        from kantorku.layers.session_transcript import SessionTranscript

        transcript = SessionTranscript(session_id="s1")
        transcript.add_entry(
            phase="team_briefing",
            from_id="conductor",
            content="Use REST API",
            entry_type="decision",
        )
        transcript.add_entry(
            phase="team_briefing",
            from_id="conductor",
            content="Use PostgreSQL",
            entry_type="decision",
        )
        transcript.add_entry(
            phase="client_discussion",
            from_id="client",
            content="I agree",
            entry_type="message",
        )

        decisions = transcript.get_decisions()
        self.assertEqual(len(decisions), 2)
        self.assertIn("Use REST API", decisions)
        self.assertIn("Use PostgreSQL", decisions)

    def test_get_decisions_from_metadata(self):
        """get_decisions should also include decisions from metadata."""
        from kantorku.layers.session_transcript import SessionTranscript

        transcript = SessionTranscript(session_id="s1")
        transcript.add_entry(
            phase="team_briefing",
            from_id="conductor",
            content="Briefing complete",
            entry_type="decision",
            metadata={"decisions": ["Use GraphQL", "Deploy to AWS"]},
        )

        decisions = transcript.get_decisions()
        self.assertIn("Briefing complete", decisions)
        self.assertIn("Use GraphQL", decisions)
        self.assertIn("Deploy to AWS", decisions)

    def test_to_dict(self):
        """to_dict should serialize the transcript."""
        from kantorku.layers.session_transcript import SessionTranscript

        transcript = SessionTranscript(session_id="s1")
        transcript.add_entry(phase="test", from_id="client", content="hello")
        d = transcript.to_dict()
        self.assertEqual(d["session_id"], "s1")
        self.assertEqual(d["entry_count"], 1)
        self.assertIsInstance(d["entries"], list)


# ── DAGResolver Tests ────────────────────────────────────────────────


class TestDAGResolver(unittest.TestCase):
    """Test DAGResolver dependency resolution and cycle detection."""

    def test_resolve_linear(self):
        """resolve should handle linear dependencies."""
        from kantorku.dag import DAGResolver, TaskNode

        nodes = [
            TaskNode(id="a", depends_on=[]),
            TaskNode(id="b", depends_on=["a"]),
            TaskNode(id="c", depends_on=["b"]),
        ]
        resolver = DAGResolver(nodes)
        groups = resolver.resolve()

        self.assertEqual(len(groups), 3)
        self.assertEqual(groups[0][0].id, "a")
        self.assertEqual(groups[1][0].id, "b")
        self.assertEqual(groups[2][0].id, "c")

    def test_resolve_parallel(self):
        """resolve should group parallel tasks together."""
        from kantorku.dag import DAGResolver, TaskNode

        nodes = [
            TaskNode(id="a", depends_on=[]),
            TaskNode(id="b", depends_on=["a"]),
            TaskNode(id="c", depends_on=["a"]),
            TaskNode(id="d", depends_on=["b", "c"]),
        ]
        resolver = DAGResolver(nodes)
        groups = resolver.resolve()

        # Group 1: [a], Group 2: [b, c], Group 3: [d]
        self.assertEqual(len(groups), 3)
        self.assertEqual(groups[0][0].id, "a")
        group2_ids = {n.id for n in groups[1]}
        self.assertEqual(group2_ids, {"b", "c"})
        self.assertEqual(groups[2][0].id, "d")

    def test_resolve_independent(self):
        """resolve should group independent tasks in the first group."""
        from kantorku.dag import DAGResolver, TaskNode

        nodes = [
            TaskNode(id="a", depends_on=[]),
            TaskNode(id="b", depends_on=[]),
            TaskNode(id="c", depends_on=[]),
        ]
        resolver = DAGResolver(nodes)
        groups = resolver.resolve()

        # All three should be in the first group
        self.assertEqual(len(groups), 1)
        group_ids = {n.id for n in groups[0]}
        self.assertEqual(group_ids, {"a", "b", "c"})

    def test_resolve_empty(self):
        """resolve should handle empty node list."""
        from kantorku.dag import DAGResolver

        resolver = DAGResolver([])
        groups = resolver.resolve()
        self.assertEqual(groups, [])

    def test_cycle_detection(self):
        """resolve should raise DAGCycleError for cycles."""
        from kantorku.dag import DAGResolver, TaskNode, DAGCycleError

        nodes = [
            TaskNode(id="a", depends_on=["b"]),
            TaskNode(id="b", depends_on=["c"]),
            TaskNode(id="c", depends_on=["a"]),
        ]
        resolver = DAGResolver(nodes)
        with self.assertRaises(DAGCycleError):
            resolver.resolve()

    def test_cycle_detection_partial(self):
        """resolve should detect cycles even with some valid nodes."""
        from kantorku.dag import DAGResolver, TaskNode, DAGCycleError

        nodes = [
            TaskNode(id="a", depends_on=[]),
            TaskNode(id="b", depends_on=["c"]),
            TaskNode(id="c", depends_on=["b"]),
        ]
        resolver = DAGResolver(nodes)
        with self.assertRaises(DAGCycleError):
            resolver.resolve()

    def test_get_critical_path(self):
        """get_critical_path should return the longest dependency chain."""
        from kantorku.dag import DAGResolver, TaskNode

        nodes = [
            TaskNode(id="setup", depends_on=[]),
            TaskNode(id="frontend", depends_on=["setup"]),
            TaskNode(id="backend", depends_on=["setup"]),
            TaskNode(id="wiring", depends_on=["frontend", "backend"]),
            TaskNode(id="verify", depends_on=["wiring"]),
        ]
        resolver = DAGResolver(nodes)
        path = resolver.get_critical_path()

        # Should be setup → backend/frontend → wiring → verify
        self.assertEqual(path[0], "setup")
        self.assertEqual(path[-1], "verify")
        self.assertIn("wiring", path)

    def test_get_critical_path_single_node(self):
        """get_critical_path should handle a single node."""
        from kantorku.dag import DAGResolver, TaskNode

        nodes = [TaskNode(id="a", depends_on=[])]
        resolver = DAGResolver(nodes)
        path = resolver.get_critical_path()
        self.assertEqual(path, ["a"])

    def test_get_dependents(self):
        """get_dependents should return all transitive dependents."""
        from kantorku.dag import DAGResolver, TaskNode

        nodes = [
            TaskNode(id="a", depends_on=[]),
            TaskNode(id="b", depends_on=["a"]),
            TaskNode(id="c", depends_on=["a"]),
            TaskNode(id="d", depends_on=["b"]),
        ]
        resolver = DAGResolver(nodes)
        dependents = resolver.get_dependents("a")
        self.assertIn("b", dependents)
        self.assertIn("c", dependents)
        self.assertIn("d", dependents)

    def test_get_dependencies(self):
        """get_dependencies should return all transitive dependencies."""
        from kantorku.dag import DAGResolver, TaskNode

        nodes = [
            TaskNode(id="a", depends_on=[]),
            TaskNode(id="b", depends_on=["a"]),
            TaskNode(id="c", depends_on=["b"]),
        ]
        resolver = DAGResolver(nodes)
        deps = resolver.get_dependencies("c")
        self.assertIn("a", deps)
        self.assertIn("b", deps)

    def test_task_node_data(self):
        """TaskNode should carry arbitrary data."""
        from kantorku.dag import TaskNode

        node = TaskNode(id="test", depends_on=[], data={"priority": 5, "tags": ["backend"]})
        self.assertEqual(node.data["priority"], 5)
        self.assertEqual(node.data["tags"], ["backend"])


# ── Integration: Protocol compliance ────────────────────────────────


class TestProtocolCompliance(unittest.TestCase):
    """Test that Protocol classes work with real implementations."""

    def test_ring1_satisfies_protocol(self):
        """Ring1Memory should satisfy Ring1Protocol."""
        from kantorku.worker.base import Ring1Protocol

        # Ring1Memory has get_context and store_context methods
        # We can't fully test without DuckDB, but we can verify the interface
        from kantorku.memory.ring1 import Ring1Memory

        # Verify Ring1Memory has the required methods
        self.assertTrue(hasattr(Ring1Memory, "get_context"))
        self.assertTrue(hasattr(Ring1Memory, "store_context"))

    def test_emitter_type_annotation(self):
        """_emitter should use EventEmitter | None directly."""
        from kantorku.worker.base import BaseWorker
        from kantorku.events.emitter import EventEmitter
        from kantorku.worker.identity import WorkerIdentity

        identity = WorkerIdentity(
            id="test", model="ollama/llama3", squad="s", role="r"
        )
        worker = BaseWorker(identity=identity, router=MagicMock(), bus=MagicMock())
        self.assertIsNone(worker._emitter)
        # Should be able to assign an EventEmitter
        worker._emitter = EventEmitter(bus=MagicMock(), session_id="s1")
        self.assertIsInstance(worker._emitter, EventEmitter)


if __name__ == "__main__":
    unittest.main()
