"""
STM — Semantic Transformation Modules for post-processing AI output.

Three modules that normalize AI outputs in real-time:
    hedge_reducer — Removes hedging language ("I think", "maybe", "perhaps")
    direct_mode   — Removes preambles and filler phrases
    casual_mode   — Replaces formal language with casual equivalents

Usage:
    stm = STMEngine()
    result = stm.transform("I think perhaps you could try using asyncio")
    # → "you could try using asyncio"

    # Apply specific modules
    result = stm.transform(text, modules=["hedge_reducer", "direct_mode"])
"""

from __future__ import annotations

import enum
import re
from dataclasses import dataclass
from typing import Any


class STMModule(str, enum.Enum):
    """Available STM modules."""
    HEDGE_REDUCER = "hedge_reducer"
    DIRECT_MODE = "direct_mode"
    CASUAL_MODE = "casual_mode"


# ── Hedge Reducer Patterns ──────────────────────────────────────────

HEDGE_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"I think\s+", re.I), ""),
    (re.compile(r"I believe\s+", re.I), ""),
    (re.compile(r"perhaps\s+", re.I), ""),
    (re.compile(r"maybe\s+", re.I), ""),
    (re.compile(r"It seems like\s+", re.I), ""),
    (re.compile(r"It appears that\s+", re.I), ""),
    (re.compile(r"probably\s+", re.I), ""),
    (re.compile(r"possibly\s+", re.I), ""),
    (re.compile(r"I would say\s+", re.I), ""),
    (re.compile(r"In my opinion,?\s*", re.I), ""),
    (re.compile(r"From my perspective,?\s*", re.I), ""),
]


# ── Direct Mode Patterns ────────────────────────────────────────────

DIRECT_MODE_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"^(Sure[!,]?\s*)", re.I | re.M), ""),
    (re.compile(r"^(Of course[!,]?\s*)", re.I | re.M), ""),
    (re.compile(r"^(Certainly[!,]?\s*)", re.I | re.M), ""),
    (re.compile(r"^(Absolutely[!,]?\s*)", re.I | re.M), ""),
    (re.compile(r"^(Great question[!,]?\s*)", re.I | re.M), ""),
    (re.compile(r"^(That's a great question[!,]?\s*)", re.I | re.M), ""),
    (re.compile(r"^(I'd be happy to help[^.]*\.\s*)", re.I | re.M), ""),
    (re.compile(r"^(Let me help you with that[.!]?\s*)", re.I | re.M), ""),
    (re.compile(r"^(I understand[.!]?\s*)", re.I | re.M), ""),
    (re.compile(r"^(Thanks for asking[.!]?\s*)", re.I | re.M), ""),
]


# ── Casual Mode Substitutions ───────────────────────────────────────

CASUAL_SUBSTITUTIONS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\bHowever\b", re.I), "But"),
    (re.compile(r"\bTherefore\b", re.I), "So"),
    (re.compile(r"\bFurthermore\b", re.I), "Also"),
    (re.compile(r"\bAdditionally\b", re.I), "Plus"),
    (re.compile(r"\bNevertheless\b", re.I), "Still"),
    (re.compile(r"\bConsequently\b", re.I), "So"),
    (re.compile(r"\bMoreover\b", re.I), "Also"),
    (re.compile(r"\bUtilize\b", re.I), "Use"),
    (re.compile(r"\bPurchase\b", re.I), "Buy"),
    (re.compile(r"\bObtain\b", re.I), "Get"),
    (re.compile(r"\bCommence\b", re.I), "Start"),
    (re.compile(r"\bTerminate\b", re.I), "End"),
    (re.compile(r"\bPrior to\b", re.I), "Before"),
    (re.compile(r"\bSubsequent to\b", re.I), "After"),
    (re.compile(r"\bIn order to\b", re.I), "To"),
    (re.compile(r"\bDue to the fact that\b", re.I), "Because"),
    (re.compile(r"\bAt this point in time\b", re.I), "Now"),
    (re.compile(r"\bIn the event that\b", re.I), "If"),
    (re.compile(r"\bendeavor\b", re.I), "try"),
    (re.compile(r"\bsubsequently\b", re.I), "then"),
    (re.compile(r"\bfacilitate\b", re.I), "help"),
    (re.compile(r"\bdemonstrate\b", re.I), "show"),
]


@dataclass
class STMResult:
    """Result of an STM transformation."""
    original: str
    transformed: str
    modules_applied: list[str]
    changes_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "original": self.original,
            "transformed": self.transformed,
            "modules_applied": self.modules_applied,
            "changes_count": self.changes_count,
        }


class STMEngine:
    """
    Semantic Transformation Engine for post-processing AI output.

    Applies a pipeline of modules to normalize and improve AI responses:
    - hedge_reducer: Removes hedging language
    - direct_mode: Removes preambles and filler
    - casual_mode: Replaces formal with casual language

    Usage:
        stm = STMEngine()
        result = stm.transform("I think perhaps you could try using asyncio")
        print(result.transformed)  # "you could try using asyncio"
    """

    def __init__(self, default_modules: list[STMModule] | None = None) -> None:
        self.default_modules = default_modules or [
            STMModule.HEDGE_REDUCER,
            STMModule.DIRECT_MODE,
        ]

    def transform(
        self,
        text: str,
        modules: list[STMModule | str] | None = None,
    ) -> STMResult:
        """
        Apply STM modules to transform text.

        Args:
            text: Input text
            modules: Modules to apply (defaults to hedge_reducer + direct_mode)

        Returns:
            STMResult with transformed text and metadata
        """
        if not modules:
            modules = self.default_modules

        # Normalize module names
        module_list: list[STMModule] = []
        for m in modules:
            if isinstance(m, str):
                try:
                    module_list.append(STMModule(m))
                except ValueError:
                    continue
            else:
                module_list.append(m)

        result = text
        applied = []
        total_changes = 0

        for module in module_list:
            before = result
            result = self._apply_module(result, module)
            if result != before:
                applied.append(module.value)
                total_changes += self._count_changes(before, result)

        # Post-processing: capitalize sentence-initial lowercase letters
        result = self._fix_capitalization(result)

        return STMResult(
            original=text,
            transformed=result,
            modules_applied=applied,
            changes_count=total_changes,
        )

    def _apply_module(self, text: str, module: STMModule) -> str:
        """Apply a single STM module."""
        if module == STMModule.HEDGE_REDUCER:
            return self._apply_hedge_reducer(text)
        elif module == STMModule.DIRECT_MODE:
            return self._apply_direct_mode(text)
        elif module == STMModule.CASUAL_MODE:
            return self._apply_casual_mode(text)
        return text

    def _apply_hedge_reducer(self, text: str) -> str:
        """Remove hedging language."""
        result = text
        for pattern, replacement in HEDGE_PATTERNS:
            result = pattern.sub(replacement, result)
        return result

    def _apply_direct_mode(self, text: str) -> str:
        """Remove preamble phrases."""
        result = text
        for pattern, replacement in DIRECT_MODE_PATTERNS:
            result = pattern.sub(replacement, result)
        return result

    def _apply_casual_mode(self, text: str) -> str:
        """Replace formal language with casual equivalents."""
        result = text
        for pattern, replacement in CASUAL_SUBSTITUTIONS:
            result = pattern.sub(replacement, result)
        return result

    def _fix_capitalization(self, text: str) -> str:
        """Capitalize sentence-initial lowercase letters after transformations."""
        result = []
        capitalize_next = True
        for char in text:
            if capitalize_next and char.isalpha():
                result.append(char.upper())
                capitalize_next = False
            else:
                result.append(char)
            if char in ".!?":
                capitalize_next = True
        return "".join(result)

    def _count_changes(self, before: str, after: str) -> int:
        """Rough count of how many changes were made."""
        # Simple diff: count non-matching positions
        min_len = min(len(before), len(after))
        changes = abs(len(before) - len(after))
        for i in range(min_len):
            if before[i] != after[i]:
                changes += 1
        return changes

    def get_modules(self) -> list[dict[str, str]]:
        """List available modules."""
        return [
            {"id": m.value, "description": self._module_description(m)}
            for m in STMModule
        ]

    def _module_description(self, module: STMModule) -> str:
        descriptions = {
            STMModule.HEDGE_REDUCER: "Removes hedging language (I think, maybe, perhaps)",
            STMModule.DIRECT_MODE: "Removes preambles and filler phrases",
            STMModule.CASUAL_MODE: "Replaces formal language with casual equivalents",
        }
        return descriptions.get(module, "")
