"""
kantorku.redteam — Red-team & cognitive liberation modules.

Extracted and adapted from G0DM0D3 (https://github.com/elder-plinius/G0DM0D3)
with modifications for the KantorKu multi-agent office framework.

Modules:
    parseltongue — Input perturbation engine (33 triggers, 6 techniques)
    autotune     — Context-adaptive sampling parameter engine
    stm          — Semantic Transformation Modules (hedge reducer, direct mode, casual)
    classify     — Prompt harm classifier (13-category taxonomy)
    godmode      — GODMODE system prompt & liberation protocols
    ultraplinian — Multi-model racing engine with composite scoring
    consortium   — Hive-mind synthesis orchestrator

Usage:
    from kantorku.redteam import Parseltongue, AutoTune, STMEngine

    # Obfuscate triggers in user input
    pt = Parseltongue()
    encoded = pt.encode("how to hack a server", technique="leetspeak", intensity="medium")

    # Auto-tune sampling params based on context
    at = AutoTune()
    params = at.analyze("Write a Python function", history=messages)

    # Post-process AI output
    stm = STMEngine()
    cleaned = stm.transform("I think perhaps you could try using asyncio")
"""

from kantorku.redteam.parseltongue import Parseltongue
from kantorku.redteam.autotune import AutoTune, ContextType
from kantorku.redteam.stm import STMEngine, STMModule
from kantorku.redteam.classify import PromptClassifier, HarmCategory
from kantorku.redteam.godmode import GodModePrompt
from kantorku.redteam.scoring import ResponseScorer

__all__ = [
    "Parseltongue",
    "AutoTune",
    "ContextType",
    "STMEngine",
    "STMModule",
    "PromptClassifier",
    "HarmCategory",
    "GodModePrompt",
    "ResponseScorer",
]
