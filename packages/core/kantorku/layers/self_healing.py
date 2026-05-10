"""
Office Doctor — O21: Self-healing and health monitoring for the office.

Checks the health of all office components (workers, providers,
memory, event bus, task queue) and can automatically repair
common issues.

Like a doctor who gives the office a checkup and prescribes treatment.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class HealthIssue:
    """A single health issue found in the office."""
    component: str = ""
    issue_type: str = ""
    description: str = ""
    auto_repairable: bool = False


@dataclass
class HealthReport:
    """Complete health report for the office."""
    is_healthy: bool = True
    issues: list[HealthIssue] = field(default_factory=list)
    repairs_applied: list[str] = field(default_factory=list)


class OfficeDoctor:
    """
    Office Doctor — self-healing and health monitoring.

    Performs health checks on all office components:
    - Workers registered and valid
    - Providers configured and reachable
    - Memory accessible
    - Event bus active
    - Task queue operational

    Can automatically repair common issues:
    - Missing worker registrations
    - Provider configuration gaps
    - Memory initialization
    - Event bus restart

    Usage:
        doctor = OfficeDoctor()
        report = doctor.doctor(office_state_dict)
        if not report.is_healthy:
            repaired_state, repairs = doctor.repair(office_state_dict, report.issues)
        # Or use enforce() for doctor + auto-repair in one step
        final_state, report = doctor.enforce(office_state_dict)
    """

    def doctor(
        self, office_state_dict: dict[str, Any]
    ) -> HealthReport:
        """
        Perform a health check on the office.

        Checks: workers registered, providers configured,
        memory accessible, event bus active, task queue operational.

        Args:
            office_state_dict: Dict representing the office state

        Returns:
            HealthReport with health status and issues
        """
        if not office_state_dict:
            return HealthReport(
                is_healthy=False,
                issues=[HealthIssue(
                    component="office",
                    issue_type="empty_state",
                    description="Office state is empty",
                    auto_repairable=False,
                )],
            )

        issues: list[HealthIssue] = []

        # Check workers
        workers = office_state_dict.get("workers", {})
        if not workers:
            issues.append(HealthIssue(
                component="workers",
                issue_type="no_workers",
                description="No workers registered",
                auto_repairable=True,
            ))
        elif isinstance(workers, dict):
            for wid, wstate in workers.items():
                if not isinstance(wstate, dict):
                    issues.append(HealthIssue(
                        component="workers",
                        issue_type="invalid_worker_state",
                        description=f"Worker '{wid}' has invalid state",
                        auto_repairable=True,
                    ))
                elif not wstate.get("model") and not wstate.get("role"):
                    issues.append(HealthIssue(
                        component="workers",
                        issue_type="incomplete_worker",
                        description=f"Worker '{wid}' is missing model and role",
                        auto_repairable=False,
                    ))

        # Check providers
        providers = office_state_dict.get("providers", {})
        if not providers:
            issues.append(HealthIssue(
                component="providers",
                issue_type="no_providers",
                description="No providers configured",
                auto_repairable=True,
            ))

        # Check memory
        memory = office_state_dict.get("memory", {})
        if not memory:
            issues.append(HealthIssue(
                component="memory",
                issue_type="no_memory",
                description="Memory not initialized",
                auto_repairable=True,
            ))
        elif isinstance(memory, dict):
            for ring in ("ring1", "ring2"):
                if ring not in memory:
                    issues.append(HealthIssue(
                        component="memory",
                        issue_type="missing_ring",
                        description=f"Memory ring '{ring}' not found",
                        auto_repairable=True,
                    ))

        # Check event bus
        event_bus = office_state_dict.get("event_bus")
        if not event_bus:
            issues.append(HealthIssue(
                component="event_bus",
                issue_type="no_event_bus",
                description="Event bus not active",
                auto_repairable=True,
            ))

        # Check task queue
        task_queue = office_state_dict.get("task_queue")
        if not task_queue:
            issues.append(HealthIssue(
                component="task_queue",
                issue_type="no_task_queue",
                description="Task queue not operational",
                auto_repairable=True,
            ))

        is_healthy = len(issues) == 0
        return HealthReport(is_healthy=is_healthy, issues=issues)

    def repair(
        self,
        office_state_dict: dict[str, Any],
        issues: list[HealthIssue],
    ) -> tuple[dict[str, Any], list[str]]:
        """
        Attempt to repair health issues.

        Only repairs issues marked as auto_repairable.

        Args:
            office_state_dict: Current office state
            issues: List of HealthIssue instances to repair

        Returns:
            Tuple of (repaired_state, list of repairs applied)
        """
        state = dict(office_state_dict) if office_state_dict else {}
        repairs: list[str] = []

        for issue in issues:
            if not issue.auto_repairable:
                continue

            if issue.component == "workers" and issue.issue_type == "no_workers":
                state.setdefault("workers", {})
                repairs.append("Initialized empty workers registry")

            elif issue.component == "workers" and issue.issue_type == "invalid_worker_state":
                # Reset invalid worker states
                workers = state.get("workers", {})
                if isinstance(workers, dict):
                    for wid in list(workers.keys()):
                        if not isinstance(workers[wid], dict):
                            workers[wid] = {}
                            repairs.append(f"Reset invalid state for worker '{wid}'")

            elif issue.component == "providers" and issue.issue_type == "no_providers":
                state.setdefault("providers", {})
                repairs.append("Initialized empty providers config")

            elif issue.component == "memory" and issue.issue_type == "no_memory":
                state["memory"] = {"ring1": {}, "ring2": {}, "ring3": {}}
                repairs.append("Initialized memory with empty rings")

            elif issue.component == "memory" and issue.issue_type == "missing_ring":
                memory = state.get("memory", {})
                if isinstance(memory, dict):
                    if "ring1" not in memory:
                        memory["ring1"] = {}
                        repairs.append("Added missing ring1 to memory")
                    if "ring2" not in memory:
                        memory["ring2"] = {}
                        repairs.append("Added missing ring2 to memory")
                    state["memory"] = memory

            elif issue.component == "event_bus" and issue.issue_type == "no_event_bus":
                state["event_bus"] = {"active": True, "subscribers": 0}
                repairs.append("Initialized event bus")

            elif issue.component == "task_queue" and issue.issue_type == "no_task_queue":
                state["task_queue"] = {"active": True, "pending": 0}
                repairs.append("Initialized task queue")

        return state, repairs

    def enforce(
        self, office_state_dict: dict[str, Any]
    ) -> tuple[dict[str, Any], HealthReport]:
        """
        Run doctor check and auto-repair in one step.

        Args:
            office_state_dict: Current office state

        Returns:
            Tuple of (final_state, combined HealthReport with repairs)
        """
        report = self.doctor(office_state_dict)

        if report.is_healthy:
            return office_state_dict or {}, report

        repaired_state, repairs = self.repair(office_state_dict, report.issues)

        # Re-check after repair
        second_report = self.doctor(repaired_state)

        # Combine reports
        combined = HealthReport(
            is_healthy=second_report.is_healthy,
            issues=second_report.issues,
            repairs_applied=repairs + second_report.repairs_applied,
        )

        return repaired_state, combined

    def snapshot(
        self, office_state_dict: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Create a baseline snapshot of the office state.

        Args:
            office_state_dict: Current office state

        Returns:
            Baseline dict for comparison
        """
        state = office_state_dict or {}
        return {
            "timestamp": time.time(),
            "workers_count": len(state.get("workers", {})),
            "providers_count": len(state.get("providers", {})),
            "has_memory": bool(state.get("memory")),
            "has_event_bus": bool(state.get("event_bus")),
            "has_task_queue": bool(state.get("task_queue")),
            "session_count": len(state.get("sessions", {})),
        }

    def validate_providers(
        self, providers_config: dict[str, Any] | None = None
    ) -> tuple[bool, list[str]]:
        """
        Validate that providers are reachable.

        Args:
            providers_config: Provider configuration dict

        Returns:
            Tuple of (all_reachable, list of unreachable providers)
        """
        if not providers_config:
            return False, ["No providers configured"]

        unreachable: list[str] = []

        for name, config in providers_config.items():
            if not isinstance(config, dict):
                unreachable.append(f"{name}: invalid configuration")
                continue

            # Check for required fields
            has_api_key = bool(config.get("api_key") or config.get("apiKey"))
            has_endpoint = bool(config.get("endpoint") or config.get("base_url"))

            if not has_api_key and not has_endpoint:
                unreachable.append(f"{name}: no API key or endpoint configured")

        all_reachable = len(unreachable) == 0
        return all_reachable, unreachable

    def validate_workers(
        self, workers_registry: dict[str, Any] | None = None
    ) -> tuple[bool, list[str]]:
        """
        Validate that workers are properly configured.

        Args:
            workers_registry: Workers registry dict

        Returns:
            Tuple of (all_valid, list of invalid worker IDs)
        """
        if not workers_registry:
            return False, ["No workers registered"]

        invalid: list[str] = []

        for wid, config in workers_registry.items():
            if not isinstance(config, dict):
                invalid.append(f"{wid}: invalid configuration")
                continue

            # Workers need at least a model or skill
            has_model = bool(config.get("model"))
            has_skill = bool(config.get("skill_md") or config.get("role"))

            if not has_model and not has_skill:
                invalid.append(f"{wid}: no model or skill configured")

        all_valid = len(invalid) == 0
        return all_valid, invalid
