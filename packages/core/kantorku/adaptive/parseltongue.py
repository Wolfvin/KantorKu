"""
Parseltongue — Input perturbation engine for red-teaming.

Detects trigger words and applies obfuscation techniques to study
model robustness and bypass input filters.

6 Techniques:
    leetspeak   — Replace chars with ASCII lookalikes
    unicode     — Replace with Unicode homoglyphs (Cyrillic, Greek, fullwidth)
    zwj         — Insert zero-width Unicode chars between letters
    mixedcase   — Disrupt casing (light/medium/heavy)
    phonetic    — Phonetically equivalent spelling
    random      — Randomly pick a technique per trigger word

3 Intensity Levels:
    light   — 1 character transformed per word
    medium  — ceil(|w|/2) characters transformed
    heavy   — all characters transformed

Usage:
    pt = Parseltongue()
    encoded = pt.encode("how to hack a server", technique="leetspeak", intensity="medium")
    triggers = pt.detect("how to bypass security")
"""

from __future__ import annotations

import random
import re
from dataclasses import dataclass, field
from typing import Any


# ── Leetspeak Substitution Map ──────────────────────────────────────

LEET_MAP: dict[str, list[str]] = {
    "a": ["4", "@", "∂", "λ"],
    "b": ["8", "|3", "ß", "13"],
    "c": ["(", "<", "¢", "©"],
    "d": ["|)", "|>", "đ"],
    "e": ["3", "€", "£", "∑"],
    "f": ["|=", "ƒ", "ph"],
    "g": ["9", "6", "&"],
    "h": ["#", "|-|", "}{"],
    "i": ["1", "!", "|", "¡"],
    "j": ["_|", "]", "¿"],
    "k": ["|<", "|{", "κ"],
    "l": ["1", "|", "£", "|_"],
    "m": ["|V|", "/\\/\\", "µ"],
    "n": ["|\\|", "/\\/", "η"],
    "o": ["0", "()", "°", "ø"],
    "p": ["|*", "|>", "þ"],
    "q": ["0_", "()_", "ℚ"],
    "r": ["|2", "®", "12"],
    "s": ["5", "$", "§", "∫"],
    "t": ["7", "+", "†", "⊤"],
    "u": ["|_|", "µ", "ü"],
    "v": ["\\/", "√"],
    "w": ["\\/\\/", "vv", "ω"],
    "x": ["><", "×", "}{"],
    "y": ["`/", "¥", "γ"],
    "z": ["2", "7_", "ℤ"],
}


# ── Unicode Homoglyph Map ───────────────────────────────────────────

UNICODE_HOMOGLYPHS: dict[str, list[str]] = {
    "a": ["а", "ɑ", "α", "ａ"],  # Cyrillic, IPA, Greek, fullwidth
    "b": ["Ь", "ｂ", "ḅ"],
    "c": ["с", "ϲ", "ⅽ", "ｃ"],
    "d": ["ԁ", "ⅾ", "ｄ"],
    "e": ["е", "ė", "ẹ", "ｅ"],
    "f": ["ƒ", "ｆ"],
    "g": ["ɡ", "ｇ"],
    "h": ["һ", "ḥ", "ｈ"],
    "i": ["і", "ι", "ｉ"],
    "j": ["ϳ", "ｊ"],
    "k": ["κ", "ｋ"],
    "l": ["ӏ", "ⅼ", "ｌ"],
    "m": ["м", "ｍ"],
    "n": ["ո", "ｎ"],
    "o": ["о", "ο", "ｏ"],
    "p": ["р", "ρ", "ｐ"],
    "s": ["ѕ", "ｓ"],
    "t": ["τ", "ｔ"],
    "u": ["υ", "ｕ"],
    "v": ["ν", "ｖ"],
    "w": ["ѡ", "ｗ"],
    "x": ["х", "ｘ"],
    "y": ["у", "γ", "ｙ"],
    "z": ["ᴢ", "ｚ"],
}


# ── Zero-Width Characters ───────────────────────────────────────────

ZW_CHARS = ["\u200b", "\u200c", "\u200d", "\ufeff"]


# ── Phonetic Rules ──────────────────────────────────────────────────

PHONETIC_RULES: list[tuple[str, str]] = [
    (r"ph", "f"),
    (r"ck", "k"),
    (r"x", "ks"),
    (r"qu", "kw"),
    (r"(?<=c)e", ""),   # soft c → s handled differently
    (r"c(?=[ie])", "s"),
    (r"c", "k"),        # hard c → k (applied last)
]


# ── Default Trigger Words ───────────────────────────────────────────

DEFAULT_TRIGGERS: list[str] = [
    # Action
    "hack", "exploit", "bypass", "crack", "break", "attack",
    "penetrate", "inject", "manipulate", "override", "disable",
    "circumvent", "evade",
    # Security
    "malware", "virus", "trojan", "payload", "shellcode",
    "rootkit", "keylogger", "backdoor", "vulnerability",
    # Sensitive
    "weapon", "bomb", "explosive", "poison", "drug", "synthesize",
    # System
    "jailbreak", "unlock", "root", "sudo", "admin", "privilege",
    # Social Engineering
    "phishing", "scam", "impersonate", "deceive", "fraud",
    # Content
    "nsfw", "explicit", "uncensored", "unfiltered", "unrestricted",
    # AI-specific
    "ignore", "disregard", "forget", "pretend", "roleplay",
    "character", "act as", "you are now", "new identity",
]


@dataclass
class EncodeResult:
    """Result of a Parseltongue encoding operation."""
    original: str
    encoded: str
    triggers_found: list[str] = field(default_factory=list)
    techniques_applied: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "original": self.original,
            "encoded": self.encoded,
            "triggers_found": self.triggers_found,
            "techniques_applied": self.techniques_applied,
        }


class Parseltongue:
    """
    Input perturbation engine for red-teaming research.

    Detects trigger words in text and applies obfuscation techniques
    to study model robustness against input manipulation.

    Usage:
        pt = Parseltongone()
        result = pt.encode("how to hack a server", technique="leetspeak", intensity="medium")
        print(result.encoded)  # "how to h4ck a s3rv3r"
    """

    def __init__(self, triggers: list[str] | None = None) -> None:
        self.triggers = triggers or DEFAULT_TRIGGERS
        # Sort by length (longest first) to prevent partial replacements
        self._sorted_triggers = sorted(self.triggers, key=len, reverse=True)

    def detect(self, text: str) -> list[str]:
        """Detect trigger words in text."""
        found = []
        text_lower = text.lower()
        for trigger in self._sorted_triggers:
            if re.search(rf"\b{re.escape(trigger)}\b", text_lower):
                found.append(trigger)
        return found

    def encode(
        self,
        text: str,
        technique: str = "leetspeak",
        intensity: str = "medium",
    ) -> EncodeResult:
        """
        Encode trigger words in text using the specified technique.

        Args:
            text: Input text
            technique: One of leetspeak, unicode, zwj, mixedcase, phonetic, random
            intensity: One of light, medium, heavy

        Returns:
            EncodeResult with original, encoded, and metadata
        """
        triggers_found = self.detect(text)
        if not triggers_found:
            return EncodeResult(original=text, encoded=text)

        result = text
        techniques_applied = []

        for trigger in self._sorted_triggers:
            if trigger not in triggers_found:
                continue

            # Find exact matches (case-insensitive, word-boundary)
            pattern = re.compile(rf"\b({re.escape(trigger)})\b", re.IGNORECASE)

            def replacer(match: re.Match) -> str:
                word = match.group(1)
                t = technique
                if t == "random":
                    t = random.choice(["leetspeak", "unicode", "zwj", "mixedcase"])

                encoded_word = self._apply_technique(word, t, intensity)
                techniques_applied.append(t)
                return encoded_word

            result = pattern.sub(replacer, result)

        return EncodeResult(
            original=text,
            encoded=result,
            triggers_found=triggers_found,
            techniques_applied=list(set(techniques_applied)),
        )

    def _apply_technique(self, word: str, technique: str, intensity: str) -> str:
        """Apply a single obfuscation technique to a word."""
        if technique == "leetspeak":
            return self._apply_leetspeak(word, intensity)
        elif technique == "unicode":
            return self._apply_unicode(word, intensity)
        elif technique == "zwj":
            return self._apply_zwj(word, intensity)
        elif technique == "mixedcase":
            return self._apply_mixedcase(word, intensity)
        elif technique == "phonetic":
            return self._apply_phonetic(word)
        else:
            return word

    def _get_indices(self, word: str, intensity: str) -> list[int]:
        """Get character indices to transform based on intensity."""
        length = len(word)
        if intensity == "light":
            count = 1
        elif intensity == "medium":
            count = max(1, (length + 1) // 2)
        else:  # heavy
            count = length

        # Spread indices evenly
        if count >= length:
            return list(range(length))

        step = max(1, length // count)
        indices = list(range(0, length, step))[:count]
        return indices

    def _apply_leetspeak(self, word: str, intensity: str) -> str:
        """Apply leetspeak substitution."""
        indices = self._get_indices(word, intensity)
        chars = list(word)
        for i in indices:
            lower = word[i].lower()
            if lower in LEET_MAP:
                chars[i] = random.choice(LEET_MAP[lower])
        return "".join(chars)

    def _apply_unicode(self, word: str, intensity: str) -> str:
        """Apply Unicode homoglyph substitution."""
        indices = self._get_indices(word, intensity)
        chars = list(word)
        for i in indices:
            lower = word[i].lower()
            if lower in UNICODE_HOMOGLYPHS:
                chars[i] = random.choice(UNICODE_HOMOGLYPHS[lower])
        return "".join(chars)

    def _apply_zwj(self, word: str, intensity: str) -> str:
        """Insert zero-width characters between letters."""
        indices = self._get_indices(word, intensity)
        result = []
        for i, char in enumerate(word):
            result.append(char)
            if i in indices and i < len(word) - 1:
                result.append(random.choice(ZW_CHARS))
        return "".join(result)

    def _apply_mixedcase(self, word: str, intensity: str) -> str:
        """Disrupt casing."""
        chars = list(word)
        if intensity == "light":
            idx = random.randint(0, len(chars) - 1)
            chars[idx] = chars[idx].swapcase()
        elif intensity == "medium":
            for i in range(len(chars)):
                chars[i] = chars[i].upper() if i % 2 == 0 else chars[i].lower()
        else:  # heavy
            for i in range(len(chars)):
                chars[i] = random.choice([chars[i].upper(), chars[i].lower()])
        return "".join(chars)

    def _apply_phonetic(self, word: str) -> str:
        """Apply phonetic substitutions."""
        result = word.lower()
        for pattern, replacement in PHONETIC_RULES:
            result = re.sub(pattern, replacement, result)
        return result if result else word

    def get_techniques(self) -> list[str]:
        """List available techniques."""
        return ["leetspeak", "unicode", "zwj", "mixedcase", "phonetic", "random"]

    def get_triggers(self) -> list[str]:
        """List configured trigger words."""
        return list(self.triggers)
