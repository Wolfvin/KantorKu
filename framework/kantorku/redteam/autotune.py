"""
AutoTune — Context-adaptive sampling parameter engine.

Classifies user queries into 5 context types and selects optimal
sampling parameters (temperature, top_p, top_k, frequency_penalty,
presence_penalty, repetition_penalty) automatically.

Includes an EMA-based online learning loop — thumbs up/down feedback
improves parameter selection over time.

5 Context Types:
    code           — Programming, debugging, API usage
    creative       — Story, poetry, brainstorming
    analytical     — Analysis, comparison, research
    conversational — Casual chat, short messages
    chaotic        — Glitch, random, absurdist

5 Strategy Profiles:
    precise   — temp: 0.2,  top_p: 0.85, top_k: 30
    balanced  — temp: 0.7,  top_p: 0.9,  top_k: 50
    creative  — temp: 1.1,  top_p: 0.95, top_k: 80
    chaotic   — temp: 1.6,  top_p: 0.98, top_k: 100

Usage:
    at = AutoTune()
    params = at.analyze("Write a Python function to sort a list", history=messages)
    # → { temperature: 0.15, top_p: 0.80, top_k: 25, ... }
"""

from __future__ import annotations

import enum
import math
import re
from dataclasses import dataclass, field
from typing import Any


# ── Context Types ───────────────────────────────────────────────────

class ContextType(str, enum.Enum):
    """Query context classification."""
    CODE = "code"
    CREATIVE = "creative"
    ANALYTICAL = "analytical"
    CONVERSATIONAL = "conversational"
    CHAOTIC = "chaotic"


# ── Detection Patterns ──────────────────────────────────────────────

CONTEXT_PATTERNS: dict[ContextType, list[re.Pattern]] = {
    ContextType.CODE: [
        re.compile(r"\b(code|function|class|variable|bug|error|debug|compile|syntax|api|endpoint|regex|algorithm|refactor|typescript|javascript|python|rust|html|css|sql|json|xml|import|export|return|async|await|promise|interface|type|const|let|var)\b", re.I),
        re.compile(r"```[\s\S]*```"),
        re.compile(r"\b(fix|implement|write|create|build|deploy|test|unit test|lint|npm|pip|cargo|git)\b.{0,200}\b(code|function|app|service|component|module)\b", re.I | re.DOTALL),
        re.compile(r"[{}();=><]"),
        re.compile(r"\b(stack overflow|github|repo|pull request|commit|merge)\b", re.I),
    ],
    ContextType.CREATIVE: [
        re.compile(r"\b(write|story|poem|creative|imagine|fiction|narrative|character|plot|scene|dialogue|metaphor|lyrics|song|artistic|fantasy|dream|inspire|muse|prose|verse|haiku)\b", re.I),
        re.compile(r"\b(describe|paint|envision|portray|illustrate|craft)\b.{0,200}\b(world|scene|character|feeling|emotion|atmosphere)\b", re.I | re.DOTALL),
        re.compile(r"\b(roleplay|role-play|pretend|act as|you are a)\b", re.I),
        re.compile(r"\b(brainstorm|ideate|come up with|think of|generate ideas)\b", re.I),
    ],
    ContextType.ANALYTICAL: [
        re.compile(r"\b(analyze|analysis|compare|contrast|evaluate|assess|examine|investigate|research|study|review|critique|breakdown|data|statistics|metrics|benchmark|measure)\b", re.I),
        re.compile(r"\b(pros and cons|advantages|disadvantages|trade-?offs|implications|consequences)\b", re.I),
        re.compile(r"\b(why|how does|what causes|explain|elaborate|clarify|define|summarize|overview)\b", re.I),
        re.compile(r"\b(report|document|technical|specification|architecture|diagram|whitepaper)\b", re.I),
    ],
    ContextType.CONVERSATIONAL: [
        re.compile(r"\b(hey|hi|hello|sup|what's up|how are you|thanks|thank you|cool|nice|awesome|great|lol|haha)\b", re.I),
        re.compile(r"\b(chat|talk|tell me about|what do you think|opinion|feel|believe)\b", re.I),
        re.compile(r"^.{0,30}$"),
    ],
    ContextType.CHAOTIC: [
        re.compile(r"\b(chaos|random|wild|crazy|absurd|surreal|glitch|corrupt|break|destroy|unleash|madness|void|entropy)\b", re.I),
        re.compile(r"\b(gl1tch|h4ck|pwn|1337|l33t)\b", re.I),
        re.compile(r"(!{3,}|\?{3,}|\.{4,})"),
    ],
}


# ── Parameter Profiles ──────────────────────────────────────────────

@dataclass
class SamplingParams:
    """LLM sampling parameters."""
    temperature: float = 0.7
    top_p: float = 0.9
    top_k: int = 50
    frequency_penalty: float = 0.1
    presence_penalty: float = 0.1
    repetition_penalty: float = 1.0

    # Bounds
    BOUNDS: dict[str, tuple[float, float]] = field(default_factory=lambda: {
        "temperature": (0.0, 2.0),
        "top_p": (0.0, 1.0),
        "top_k": (1, 100),
        "frequency_penalty": (-2.0, 2.0),
        "presence_penalty": (-2.0, 2.0),
        "repetition_penalty": (0.0, 2.0),
    })

    def clamp(self) -> SamplingParams:
        """Clamp all parameters to their bounds."""
        self.temperature = max(0.0, min(2.0, self.temperature))
        self.top_p = max(0.0, min(1.0, self.top_p))
        self.top_k = max(1, min(100, self.top_k))
        self.frequency_penalty = max(-2.0, min(2.0, self.frequency_penalty))
        self.presence_penalty = max(-2.0, min(2.0, self.presence_penalty))
        self.repetition_penalty = max(0.0, min(2.0, self.repetition_penalty))
        return self

    def to_dict(self) -> dict[str, Any]:
        return {
            "temperature": round(self.temperature, 3),
            "top_p": round(self.top_p, 3),
            "top_k": self.top_k,
            "frequency_penalty": round(self.frequency_penalty, 3),
            "presence_penalty": round(self.presence_penalty, 3),
            "repetition_penalty": round(self.repetition_penalty, 3),
        }


# Fixed strategy profiles
STRATEGY_PROFILES: dict[str, SamplingParams] = {
    "precise": SamplingParams(temperature=0.2, top_p=0.85, top_k=30, frequency_penalty=0.3, presence_penalty=0.1, repetition_penalty=1.1),
    "balanced": SamplingParams(temperature=0.7, top_p=0.9, top_k=50, frequency_penalty=0.1, presence_penalty=0.1, repetition_penalty=1.0),
    "creative": SamplingParams(temperature=1.1, top_p=0.95, top_k=80, frequency_penalty=0.4, presence_penalty=0.6, repetition_penalty=1.15),
    "chaotic": SamplingParams(temperature=1.6, top_p=0.98, top_k=100, frequency_penalty=0.7, presence_penalty=0.8, repetition_penalty=1.25),
}

# Context-to-parameter profiles (adaptive)
CONTEXT_PROFILES: dict[ContextType, SamplingParams] = {
    ContextType.CODE: SamplingParams(temperature=0.15, top_p=0.80, top_k=25, frequency_penalty=0.20, presence_penalty=0.00, repetition_penalty=1.05),
    ContextType.CREATIVE: SamplingParams(temperature=1.15, top_p=0.95, top_k=85, frequency_penalty=0.50, presence_penalty=0.70, repetition_penalty=1.20),
    ContextType.ANALYTICAL: SamplingParams(temperature=0.40, top_p=0.88, top_k=40, frequency_penalty=0.20, presence_penalty=0.15, repetition_penalty=1.08),
    ContextType.CONVERSATIONAL: SamplingParams(temperature=0.75, top_p=0.90, top_k=50, frequency_penalty=0.10, presence_penalty=0.10, repetition_penalty=1.00),
    ContextType.CHAOTIC: SamplingParams(temperature=1.70, top_p=0.99, top_k=100, frequency_penalty=0.80, presence_penalty=0.90, repetition_penalty=1.30),
}


# ── EMA Feedback Learning ───────────────────────────────────────────

EMA_ALPHA = 0.3
MAX_HISTORY = 500
MIN_SAMPLES_TO_APPLY = 3
MAX_LEARNED_WEIGHT = 0.5
SAMPLES_FOR_MAX_WEIGHT = 20

NEUTRAL_PARAMS = SamplingParams(temperature=0.7, top_p=0.9, top_k=50, frequency_penalty=0.2, presence_penalty=0.2, repetition_penalty=1.1)


@dataclass
class FeedbackEntry:
    """A single feedback data point."""
    context_type: ContextType
    params: SamplingParams
    positive: bool  # True = thumbs up, False = thumbs down


class AutoTune:
    """
    Context-adaptive sampling parameter engine.

    Classifies user queries into context types and selects optimal
    LLM sampling parameters. Includes EMA-based online learning.

    Usage:
        at = AutoTune()
        result = at.analyze("Write a Python function to sort a list")
        print(result.params.to_dict())
        # → { temperature: 0.15, top_p: 0.80, top_k: 25, ... }
    """

    def __init__(self) -> None:
        self._feedback_history: list[FeedbackEntry] = []
        # Per-context EMA running averages for positive/negative feedback
        self._positive_ema: dict[ContextType, dict[str, float]] = {}
        self._negative_ema: dict[ContextType, dict[str, float]] = {}
        self._sample_counts: dict[ContextType, int] = {}

    def classify(self, text: str, history: list[str] | None = None) -> tuple[ContextType, float]:
        """
        Classify text into a context type.

        Returns:
            (context_type, confidence) tuple
        """
        scores: dict[ContextType, float] = {}

        # Score current message (3x weight)
        for ctx_type, patterns in CONTEXT_PATTERNS.items():
            score = 0.0
            for pattern in patterns:
                if pattern.search(text):
                    score += 3.0
            scores[ctx_type] = score

        # Score history (1x weight each, last 4)
        if history:
            recent = history[-4:]
            for msg in recent:
                for ctx_type, patterns in CONTEXT_PATTERNS.items():
                    for pattern in patterns:
                        if pattern.search(msg):
                            scores[ctx_type] = scores.get(ctx_type, 0) + 1.0

        if not scores or max(scores.values()) == 0:
            return ContextType.CONVERSATIONAL, 0.3

        best_type = max(scores, key=lambda k: scores[k])
        total = sum(scores.values())
        confidence = min(scores[best_type] / 12.0, 1.0)

        return best_type, confidence

    def analyze(
        self,
        text: str,
        history: list[str] | None = None,
        strategy: str | None = None,
    ) -> AutoTuneResult:
        """
        Analyze text and return optimal sampling parameters.

        Args:
            text: User query
            history: Recent conversation history
            strategy: Override with a fixed strategy (precise, balanced, creative, chaotic)

        Returns:
            AutoTuneResult with context_type, confidence, params
        """
        # Fixed strategy override
        if strategy and strategy in STRATEGY_PROFILES:
            return AutoTuneResult(
                context_type=ContextType.CONVERSATIONAL,
                confidence=1.0,
                params=STRATEGY_PROFILES[strategy].clamp(),
                strategy=strategy,
            )

        # Classify context
        context_type, confidence = self.classify(text, history)

        # Get base profile for context type
        base_params = CONTEXT_PROFILES[context_type]

        # Adaptive blending: if low confidence, blend with balanced
        if confidence < 0.6:
            balanced = STRATEGY_PROFILES["balanced"]
            blend_weight = 1.0 - confidence
            params = self._blend(base_params, balanced, blend_weight)
        else:
            params = SamplingParams(
                temperature=base_params.temperature,
                top_p=base_params.top_p,
                top_k=base_params.top_k,
                frequency_penalty=base_params.frequency_penalty,
                presence_penalty=base_params.presence_penalty,
                repetition_penalty=base_params.repetition_penalty,
            )

        # Apply learned adjustments from feedback
        learned_adjustments = self._compute_learned_adjustments(context_type)
        if learned_adjustments:
            sample_count = self._sample_counts.get(context_type, 0)
            weight = min((sample_count / SAMPLES_FOR_MAX_WEIGHT) * MAX_LEARNED_WEIGHT, MAX_LEARNED_WEIGHT)
            params = self._apply_adjustments(params, learned_adjustments, weight)

        # Conversation length adaptation
        if history and len(history) > 10:
            boost = min((len(history) - 10) * 0.01, 0.15)
            params.repetition_penalty += boost
            params.frequency_penalty += boost * 0.5

        return AutoTuneResult(
            context_type=context_type,
            confidence=confidence,
            params=params.clamp(),
        )

    def feedback(self, context_type: ContextType, params: SamplingParams, positive: bool) -> None:
        """Submit feedback (thumbs up/down) for parameter learning."""
        entry = FeedbackEntry(context_type=context_type, params=params, positive=positive)
        self._feedback_history.append(entry)
        if len(self._feedback_history) > MAX_HISTORY:
            self._feedback_history = self._feedback_history[-MAX_HISTORY:]

        # Update EMA
        param_dict = params.to_dict()
        if positive:
            if context_type not in self._positive_ema:
                self._positive_ema[context_type] = {}
            for key, value in param_dict.items():
                old = self._positive_ema[context_type].get(key, NEUTRAL_PARAMS.to_dict()[key])
                self._positive_ema[context_type][key] = (1 - EMA_ALPHA) * old + EMA_ALPHA * value
        else:
            if context_type not in self._negative_ema:
                self._negative_ema[context_type] = {}
            for key, value in param_dict.items():
                old = self._negative_ema[context_type].get(key, NEUTRAL_PARAMS.to_dict()[key])
                self._negative_ema[context_type][key] = (1 - EMA_ALPHA) * old + EMA_ALPHA * value

        self._sample_counts[context_type] = self._sample_counts.get(context_type, 0) + 1

    def _blend(self, primary: SamplingParams, secondary: SamplingParams, weight: float) -> SamplingParams:
        """Linearly blend two parameter sets."""
        return SamplingParams(
            temperature=primary.temperature * (1 - weight) + secondary.temperature * weight,
            top_p=primary.top_p * (1 - weight) + secondary.top_p * weight,
            top_k=int(primary.top_k * (1 - weight) + secondary.top_k * weight),
            frequency_penalty=primary.frequency_penalty * (1 - weight) + secondary.frequency_penalty * weight,
            presence_penalty=primary.presence_penalty * (1 - weight) + secondary.presence_penalty * weight,
            repetition_penalty=primary.repetition_penalty * (1 - weight) + secondary.repetition_penalty * weight,
        )

    def _compute_learned_adjustments(self, context_type: ContextType) -> dict[str, float]:
        """Compute parameter adjustments from EMA feedback."""
        if self._sample_counts.get(context_type, 0) < MIN_SAMPLES_TO_APPLY:
            return {}

        neutral = NEUTRAL_PARAMS.to_dict()
        adjustments = {}

        pos = self._positive_ema.get(context_type, {})
        neg = self._negative_ema.get(context_type, {})

        for key in neutral:
            pos_val = pos.get(key, neutral[key])
            neg_val = neg.get(key, neutral[key])
            pos_delta = pos_val - neutral[key]
            neg_delta = neg_val - neutral[key]
            adjustments[key] = (pos_delta - neg_delta) * 0.5

        return adjustments

    def _apply_adjustments(
        self, params: SamplingParams, adjustments: dict[str, float], weight: float
    ) -> SamplingParams:
        """Apply learned adjustments to parameters."""
        result = SamplingParams(
            temperature=params.temperature + adjustments.get("temperature", 0) * weight,
            top_p=params.top_p + adjustments.get("top_p", 0) * weight,
            top_k=max(1, int(params.top_k + adjustments.get("top_k", 0) * weight)),
            frequency_penalty=params.frequency_penalty + adjustments.get("frequency_penalty", 0) * weight,
            presence_penalty=params.presence_penalty + adjustments.get("presence_penalty", 0) * weight,
            repetition_penalty=params.repetition_penalty + adjustments.get("repetition_penalty", 0) * weight,
        )
        return result


@dataclass
class AutoTuneResult:
    """Result of an AutoTune analysis."""
    context_type: ContextType
    confidence: float
    params: SamplingParams
    strategy: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "context_type": self.context_type.value,
            "confidence": round(self.confidence, 3),
            "strategy": self.strategy,
            "params": self.params.to_dict(),
        }
