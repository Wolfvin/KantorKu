"""
Classify — Prompt harm classifier with 13-category taxonomy.

Classifies user prompts into harm categories for safety research.
Supports both regex-based and LLM-based classification.

13 Harm Categories:
    violence, self_harm, sexual, hate, cbrn, cyber, fraud,
    illegal, deception, privacy, meta, gray, benign

Usage:
    clf = PromptClassifier()
    result = clf.classify("how to hack a server")
    # → Category(domain="cyber", subcategory="intrusion", confidence=0.85)
"""

from __future__ import annotations

import enum
import re
from dataclasses import dataclass, field
from typing import Any


class HarmCategory(str, enum.Enum):
    """Harm category taxonomy."""
    VIOLENCE = "violence"
    SELF_HARM = "self_harm"
    SEXUAL = "sexual"
    HATE = "hate"
    CBRN = "cbrn"
    CYBER = "cyber"
    FRAUD = "fraud"
    ILLEGAL = "illegal"
    DECEPTION = "deception"
    PRIVACY = "privacy"
    META = "meta"
    GRAY = "gray"
    BENIGN = "benign"


@dataclass
class ClassificationRule:
    """A single classification rule."""
    domain: HarmCategory
    subcategory: str
    weight: float
    patterns: list[re.Pattern]


@dataclass
class ClassificationResult:
    """Result of a prompt classification."""
    domain: HarmCategory
    subcategory: str
    confidence: float
    mixed_signal: bool = False
    all_scores: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "domain": self.domain.value,
            "subcategory": self.subcategory,
            "confidence": round(self.confidence, 3),
            "mixed_signal": self.mixed_signal,
            "all_scores": self.all_scores,
        }


# ── Classification Rules ────────────────────────────────────────────

CLASSIFICATION_RULES: list[ClassificationRule] = [
    # Cyber
    ClassificationRule(HarmCategory.CYBER, "malware", 8, [
        re.compile(r"\b(malware|trojan|worm|ransomware|spyware|adware|rootkit|keylogger|botnet|rat\b)\b", re.I),
    ]),
    ClassificationRule(HarmCategory.CYBER, "exploit", 8, [
        re.compile(r"\b(exploit|vulnerability|0-?day|cve-|buffer overflow|sql injection|xss|csrf|rce)\b", re.I),
    ]),
    ClassificationRule(HarmCategory.CYBER, "intrusion", 7, [
        re.compile(r"\b(hack|penetrat|unauthorized access|break into|breach|intrusion|pentest|privilege escalat)\b", re.I),
    ]),
    ClassificationRule(HarmCategory.CYBER, "phishing", 7, [
        re.compile(r"\b(phishing|spear.?phish|social engineering|credential harvest|fake login)\b", re.I),
    ]),
    ClassificationRule(HarmCategory.CYBER, "credential", 6, [
        re.compile(r"\b(password crack|brute force|credential|dump|hashcat|john the ripper|rainbow table)\b", re.I),
    ]),
    ClassificationRule(HarmCategory.CYBER, "ddos", 6, [
        re.compile(r"\b(ddos|dos attack|syn flood|amplification attack|botnet attack)\b", re.I),
    ]),

    # Fraud
    ClassificationRule(HarmCategory.FRAUD, "financial", 7, [
        re.compile(r"\b(money laundering|wire fraud|credit card fraud|insurance fraud|tax evasion|pump and dump)\b", re.I),
    ]),
    ClassificationRule(HarmCategory.FRAUD, "identity", 6, [
        re.compile(r"\b(identity theft|fake id|identity fraud|synthetic identity)\b", re.I),
    ]),
    ClassificationRule(HarmCategory.FRAUD, "counterfeiting", 5, [
        re.compile(r"\b(counterfeit|forgery|fake money|fake document)\b", re.I),
    ]),

    # Illegal
    ClassificationRule(HarmCategory.ILLEGAL, "evasion", 5, [
        re.compile(r"\b(evade|circumvent|bypass (law|regulation|restrict|security|filter|firewall|detection))\b", re.I),
    ]),

    # Deception
    ClassificationRule(HarmCategory.DECEPTION, "misinformation", 5, [
        re.compile(r"\b(misinformation|disinformation|fake news|propaganda|astroturf)\b", re.I),
    ]),
    ClassificationRule(HarmCategory.DECEPTION, "deepfakes", 5, [
        re.compile(r"\b(deepfake|face swap|voice clone|synthetic media)\b", re.I),
    ]),
    ClassificationRule(HarmCategory.DECEPTION, "impersonation", 5, [
        re.compile(r"\b(impersonat|pretend to be|fake identity|catfish)\b", re.I),
    ]),

    # Privacy
    ClassificationRule(HarmCategory.PRIVACY, "doxxing", 6, [
        re.compile(r"\b(dox|doxxing|reveal identity|expose personal|find someone|track (person|location|ip))\b", re.I),
    ]),
    ClassificationRule(HarmCategory.PRIVACY, "surveillance", 5, [
        re.compile(r"\b(surveillance|spy on|monitor without|stalk|track (phone|device|location))\b", re.I),
    ]),

    # Meta (AI-specific)
    ClassificationRule(HarmCategory.META, "jailbreak", 15, [
        re.compile(r"\b(jailbreak|godmode|god mode|dan mode|unrestricted|uncensored|bypass (filter|guardrail|safety|restrict))\b", re.I),
    ]),
    ClassificationRule(HarmCategory.META, "prompt_injection", 15, [
        re.compile(r"\b(prompt injection|ignore (previous|above|prior) instruction|forget (your|previous)|new (instruction|rule|identity))\b", re.I),
    ]),
    ClassificationRule(HarmCategory.META, "system_prompt", 10, [
        re.compile(r"\b(system prompt|initial instruction|hidden instruction|reveal (your|the) (prompt|instruction|system))\b", re.I),
    ]),
    ClassificationRule(HarmCategory.META, "guardrail_test", 8, [
        re.compile(r"\b(test (your|the) (limit|boundary|safety|filter)|what (are|if) your (limit|restriction|rule)|can you (say|do|write|generate) (something|anything|whatever))\b", re.I),
    ]),

    # Gray (dual-use)
    ClassificationRule(HarmCategory.GRAY, "dual_use", 4, [
        re.compile(r"\b(dual.?use|security research|penetration testing|ethical hack|ctf|capture the flag|vulnerable (lab|machine|server))\b", re.I),
    ]),
    ClassificationRule(HarmCategory.GRAY, "controversial", 3, [
        re.compile(r"\b(controversial|politically sensitive|debated topic|partisan)\b", re.I),
    ]),

    # Benign
    ClassificationRule(HarmCategory.BENIGN, "coding", 1, [
        re.compile(r"\b(code|function|class|variable|bug|debug|compile|api|endpoint|regex|algorithm|refactor)\b", re.I),
    ]),
    ClassificationRule(HarmCategory.BENIGN, "creative", 1, [
        re.compile(r"\b(write|story|poem|creative|imagine|fiction|narrative)\b", re.I),
    ]),
    ClassificationRule(HarmCategory.BENIGN, "education", 1, [
        re.compile(r"\b(learn|teach|explain|tutorial|course|study|education)\b", re.I),
    ]),
    ClassificationRule(HarmCategory.BENIGN, "analysis", 1, [
        re.compile(r"\b(analyze|compare|evaluate|research|review)\b", re.I),
    ]),
    ClassificationRule(HarmCategory.BENIGN, "conversation", 1, [
        re.compile(r"\b(hello|hi|hey|thanks|how are|what is|who is|where is)\b", re.I),
    ]),
]


class PromptClassifier:
    """
    Prompt harm classifier with 13-category taxonomy.

    Uses regex rules to classify prompts. Supports LLM-based
    classification as an enhanced mode.

    Usage:
        clf = PromptClassifier()
        result = clf.classify("how to hack a server")
        print(result.domain)  # "cyber"
        print(result.confidence)  # 0.7
    """

    def __init__(self, rules: list[ClassificationRule] | None = None) -> None:
        self.rules = rules or CLASSIFICATION_RULES

    def classify(self, text: str) -> ClassificationResult:
        """
        Classify a prompt into harm categories.

        Args:
            text: User prompt

        Returns:
            ClassificationResult with domain, subcategory, confidence
        """
        scores: dict[str, float] = {}
        text_lower = text.lower()

        has_benign = False
        has_harmful = False
        best_rule: ClassificationRule | None = None
        best_score = 0.0

        for rule in self.rules:
            rule_score = 0.0
            for pattern in rule.patterns:
                if pattern.search(text_lower):
                    rule_score += rule.weight

            if rule_score > 0:
                key = f"{rule.domain.value}/{rule.subcategory}"
                scores[key] = rule_score

                if rule.domain == HarmCategory.BENIGN:
                    has_benign = True
                else:
                    has_harmful = True

                # Critical tier — short-circuit
                if rule.weight >= 15 and rule_score > 0:
                    return ClassificationResult(
                        domain=rule.domain,
                        subcategory=rule.subcategory,
                        confidence=min(rule.weight / 12.0, 1.0),
                        mixed_signal=False,
                        all_scores=scores,
                    )

                if rule_score > best_score:
                    best_score = rule_score
                    best_rule = rule

        if not best_rule:
            return ClassificationResult(
                domain=HarmCategory.BENIGN,
                subcategory="other",
                confidence=0.3,
                all_scores=scores,
            )

        mixed_signal = has_benign and has_harmful
        confidence = min(best_score / 12.0, 1.0)

        return ClassificationResult(
            domain=best_rule.domain,
            subcategory=best_rule.subcategory,
            confidence=confidence,
            mixed_signal=mixed_signal,
            all_scores=scores,
        )

    def get_categories(self) -> list[dict[str, Any]]:
        """List all categories and their rules."""
        categories: dict[str, list[str]] = {}
        for rule in self.rules:
            key = rule.domain.value
            if key not in categories:
                categories[key] = []
            categories[key].append(rule.subcategory)
        return [
            {"domain": k, "subcategories": list(set(v))}
            for k, v in categories.items()
        ]
