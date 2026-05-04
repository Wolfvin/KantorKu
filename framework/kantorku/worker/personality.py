"""
WorkerPersonality — When a worker speaks, when it stays quiet.

Every worker has a personality config that determines their behavior
in the ExecutionChannel. This isn't about making workers "cute" —
it's about efficient communication. Workers that speak too much
waste LLM tokens and time. Workers that speak too little miss
important coordination opportunities.

Personality is configured in plugin.json under the "personality" key.
Workers without a personality config default to reactive-only
(only speak when assigned a task).
"""

from __future__ import annotations

from typing import Any


class WorkerPersonality:
    """
    Configuration for when a worker speaks and when it stays quiet.

    Loaded from plugin.json "personality" section.

    Example plugin.json:
        {
          "id": "auditor",
          "personality": {
            "proactive": true,
            "speaks_when": ["sees_dead_code", "sees_security_issue"],
            "stays_quiet_when": ["task_outside_expertise"],
            "ask_before_change": true,
            "scan_interval_seconds": 60,
            "confidence_threshold": 0.7
          }
        }
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        config = config or {}
        self.proactive: bool = config.get("proactive", False)
        self.speaks_when: list[str] = config.get("speaks_when", ["assigned_to_task"])
        self.stays_quiet_when: list[str] = config.get("stays_quiet_when", [])
        self.ask_before_change: bool = config.get("ask_before_change", False)
        self.scan_interval: int = config.get("scan_interval_seconds", 0)
        self.confidence_threshold: float = config.get("confidence_threshold", 0.6)

    def should_speak(self, context: dict[str, Any]) -> bool:
        """
        Decide if a worker should speak up based on context.

        stay_quiet conditions take priority over speaks_when —
        if a stay_quiet condition matches, the worker stays silent
        even if a speaks_when condition also matches.

        Args:
            context: Situation info (trigger, topic, active_workers, etc.)

        Returns:
            True if the worker should speak, False if it should stay quiet
        """
        # Check stay_quiet first (higher priority)
        for condition in self.stays_quiet_when:
            if self._matches_condition(condition, context):
                return False

        # Check speaks_when
        for condition in self.speaks_when:
            if self._matches_condition(condition, context):
                return True

        return False

    def _matches_condition(self, condition: str, context: dict[str, Any]) -> bool:
        """
        Match a condition string to the current context.

        Built-in conditions:
        - "assigned_to_task": worker is directly assigned to the current task
        - "sees_dead_code": dead code detected
        - "sees_security_issue": security vulnerability detected
        - "sees_anti_pattern": anti-pattern detected
        - "sees_api_contract_change": API interface change proposed
        - "sees_ux_issue": UX issue in non-UX worker's design
        - "sees_performance_issue": performance issue detected
        - "sees_error_pattern": recurring error pattern detected
        - "sees_recurring_issue": same issue seen before
        - "pure_backend_discussion": only backend workers involved
        - "pure_frontend_discussion": only frontend workers involved
        - "pure_design_discussion": only design workers involved
        - "infrastructure_only": only infrastructure workers involved
        - "task_outside_expertise": topic is outside worker's domain
        - "already_addressed_by_others": someone else already raised the point
        """
        trigger = context.get("trigger", "")
        topic = context.get("topic", "")
        active_workers = context.get("active_workers", [])

        # Task assignment
        if condition == "assigned_to_task":
            return context.get("is_assigned", False)

        # Detection triggers
        if condition == "sees_dead_code":
            return "dead_code" in trigger or "dead_code" in topic.lower()
        if condition == "sees_security_issue":
            return "security" in trigger or "security" in topic.lower()
        if condition == "sees_anti_pattern":
            return "anti_pattern" in trigger or "anti-pattern" in topic.lower()
        if condition == "sees_api_contract_change":
            return "api_contract" in trigger or "interface_change" in trigger
        if condition == "sees_ux_issue":
            return "ux_issue" in trigger or "ux" in topic.lower()
        if condition == "sees_performance_issue":
            return "performance" in trigger or "performance" in topic.lower()
        if condition == "sees_error_pattern":
            return "error_pattern" in trigger or "recurring_error" in trigger
        if condition == "sees_recurring_issue":
            return "recurring" in trigger

        # Discussion scope conditions
        if condition == "pure_backend_discussion":
            backend_workers = {"coder_backend", "debugger"}
            return bool(active_workers) and all(
                w in backend_workers for w in active_workers
            )
        if condition == "pure_frontend_discussion":
            frontend_workers = {"coder_frontend", "verifier_designer"}
            return bool(active_workers) and all(
                w in frontend_workers for w in active_workers
            )
        if condition == "pure_design_discussion":
            design_workers = {"verifier_designer", "coder_frontend"}
            return bool(active_workers) and all(
                w in design_workers for w in active_workers
            )
        if condition == "infrastructure_only":
            infra_workers = {"coder_backend", "coder_wiring", "sentinel"}
            return bool(active_workers) and all(
                w in infra_workers for w in active_workers
            )

        # Context-based conditions
        if condition == "task_outside_expertise":
            return context.get("outside_expertise", False)
        if condition == "already_addressed_by_others":
            return context.get("already_addressed", False)

        # Unknown condition — try substring match against trigger/topic
        if condition in trigger or condition in topic.lower():
            return True

        return False

    def to_dict(self) -> dict[str, Any]:
        """Serialize personality config."""
        return {
            "proactive": self.proactive,
            "speaks_when": self.speaks_when,
            "stays_quiet_when": self.stays_quiet_when,
            "ask_before_change": self.ask_before_change,
            "scan_interval_seconds": self.scan_interval,
            "confidence_threshold": self.confidence_threshold,
        }
