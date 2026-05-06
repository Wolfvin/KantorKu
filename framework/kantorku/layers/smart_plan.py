"""
Smart Plan — O10: Structured planning with validation and risk assessment.

Provides rule-based plan drafting with LLM fallback, plan validation
through quality gates, complexity estimation, and risk identification.

Like a project manager who creates detailed project plans before
starting work — not just jumping in.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Complexity(Enum):
    """Plan complexity levels."""
    SIMPLE = "simple"
    MEDIUM = "medium"
    COMPLEX = "complex"


@dataclass
class PlanPhase:
    """A single phase in the execution plan."""
    name: str = ""
    objective: str = ""
    tasks: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    estimated_complexity: str = "medium"
    gate_criteria: list[str] = field(default_factory=list)


@dataclass
class PlanSchema:
    """Complete execution plan schema."""
    goal: str = ""
    scope_in: list[str] = field(default_factory=list)
    scope_out: list[str] = field(default_factory=list)
    phases: list[PlanPhase] = field(default_factory=list)
    risks: list[dict[str, Any]] = field(default_factory=list)
    verification: list[str] = field(default_factory=list)
    next_step: str = ""


# Default worker assignments by task type
_DEFAULT_WORKER_MAP: dict[str, str] = {
    "frontend": "coder_frontend",
    "backend": "coder_backend",
    "api": "coder_wiring",
    "database": "coder_backend",
    "testing": "verifier_engineer",
    "design": "verifier_designer",
    "debug": "debugger",
    "research": "scout",
    "documentation": "scribe",
}


class SmartPlan:
    """
    Smart Plan — structured planning with validation and risk assessment.

    Creates detailed, validated plans from objectives with:
    - Rule-based plan drafting (LLM fallback available)
    - 4-gate validation: context_sufficient, plan_realistic,
      results_verifiable, summary_actionable
    - Complexity estimation
    - Risk identification
    - Conductor-compatible contract format

    Usage:
        planner = SmartPlan()
        plan = planner.draft_plan("Build auth system", {"stack": "fastapi"}, ["coder_backend"])
        is_valid, issues = planner.validate_plan(plan)
        complexity = planner.estimate_complexity("Build auth system", {"stack": "fastapi"})
    """

    def draft_plan(
        self,
        objective: str,
        context: dict[str, Any] | None = None,
        available_workers: list[str] | None = None,
    ) -> PlanSchema:
        """
        Draft an execution plan from an objective.

        Uses rule-based logic to create a structured plan.
        Falls back to a basic plan if context is insufficient for
        detailed planning.

        Args:
            objective: The goal or task description
            context: Available context (tech stack, requirements, etc.)
            available_workers: List of available worker IDs

        Returns:
            PlanSchema with the drafted plan
        """
        context = context or {}
        available_workers = available_workers or []

        # Extract scope from objective and context
        scope_in = self._extract_scope_in(objective, context)
        scope_out = self._extract_scope_out(objective, context)

        # Determine complexity
        complexity = self.estimate_complexity(objective, context)

        # Build phases based on objective analysis
        phases = self._build_phases(objective, context, available_workers, complexity)

        # Identify risks
        plan_for_risk = PlanSchema(
            goal=objective,
            scope_in=scope_in,
            scope_out=scope_out,
            phases=phases,
        )
        risks = self.identify_risks(plan_for_risk, context)

        # Build verification steps
        verification = self._build_verification(phases)

        # Determine next step
        next_step = "begin_phase_1" if phases else "clarify_requirements"

        return PlanSchema(
            goal=objective,
            scope_in=scope_in,
            scope_out=scope_out,
            phases=phases,
            risks=risks,
            verification=verification,
            next_step=next_step,
        )

    def validate_plan(self, plan: PlanSchema) -> tuple[bool, list[str]]:
        """
        Validate a plan through 4 quality gates.

        Gates:
        1. context_sufficient — Plan has enough context to proceed
        2. plan_realistic — Plan phases are achievable
        3. results_verifiable — Outcomes can be verified
        4. summary_actionable — Next steps are concrete

        Args:
            plan: The PlanSchema to validate

        Returns:
            Tuple of (is_valid, list of issues)
        """
        issues: list[str] = []

        # Gate 1: context_sufficient
        if not plan.goal or not plan.goal.strip():
            issues.append("GATE context_sufficient FAIL: No goal defined")
        if not plan.scope_in:
            issues.append("GATE context_sufficient WARN: No scope_in defined — may be too vague")

        # Gate 2: plan_realistic
        if not plan.phases:
            issues.append("GATE plan_realistic FAIL: No phases defined")
        else:
            for i, phase in enumerate(plan.phases):
                if not phase.tasks:
                    issues.append(
                        f"GATE plan_realistic WARN: Phase '{phase.name}' has no tasks"
                    )
                if phase.estimated_complexity == "complex" and len(phase.tasks) < 2:
                    issues.append(
                        f"GATE plan_realistic WARN: Phase '{phase.name}' is complex "
                        f"but has only {len(phase.tasks)} task(s)"
                    )

        # Gate 3: results_verifiable
        if not plan.verification:
            issues.append("GATE results_verifiable WARN: No verification steps defined")
        else:
            for v in plan.verification:
                if not v or not v.strip():
                    issues.append("GATE results_verifiable WARN: Empty verification step")

        # Gate 4: summary_actionable
        if not plan.next_step or not plan.next_step.strip():
            issues.append("GATE summary_actionable FAIL: No next step defined")
        elif plan.next_step in ("tbd", "todo", "unknown"):
            issues.append("GATE summary_actionable WARN: Vague next step")

        is_valid = not any("FAIL" in issue for issue in issues)
        return is_valid, issues

    def estimate_complexity(
        self, objective: str, context: dict[str, Any] | None = None
    ) -> str:
        """
        Estimate the complexity of an objective.

        Based on:
        - Number of distinct concerns mentioned
        - Presence of integration/cross-cutting keywords
        - Context richness

        Args:
            objective: The objective text
            context: Available context

        Returns:
            Complexity level as string: "simple", "medium", or "complex"
        """
        context = context or {}
        score = 0

        obj_lower = (objective or "").lower()

        # Multi-concern indicators
        concern_keywords = [
            "and", "also", "plus", "integrate", "connect", "both",
            "multiple", "several", "various", "cross-cutting",
        ]
        for kw in concern_keywords:
            if kw in obj_lower:
                score += 1

        # Complex domain indicators
        complex_keywords = [
            "authentication", "authorization", "payment", "real-time",
            "concurrent", "distributed", "microservice", "migration",
            "refactor", "optimize", "scale", "security",
        ]
        for kw in complex_keywords:
            if kw in obj_lower:
                score += 2

        # Context richness bonus
        if context:
            score -= len(context) * 0.5

        if score <= 1:
            return Complexity.SIMPLE.value
        elif score <= 4:
            return Complexity.MEDIUM.value
        else:
            return Complexity.COMPLEX.value

    def identify_risks(
        self,
        plan: PlanSchema,
        context: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Identify risks in a plan.

        Args:
            plan: The PlanSchema to analyze
            context: Additional context for risk assessment

        Returns:
            List of risk dicts with name, likelihood, impact, mitigation
        """
        context = context or {}
        risks: list[dict[str, Any]] = []

        # Risk: unclear scope
        if not plan.scope_in or len(plan.scope_in) < 2:
            risks.append({
                "name": "Unclear scope",
                "likelihood": "medium",
                "impact": "high",
                "mitigation": "Clarify scope with client before execution",
            })

        # Risk: too many phases without dependencies
        if len(plan.phases) > 3:
            has_deps = any(
                phase.dependencies for phase in plan.phases if phase.dependencies
            )
            if not has_deps:
                risks.append({
                    "name": "No phase dependencies defined",
                    "likelihood": "medium",
                    "impact": "medium",
                    "mitigation": "Define phase ordering and dependencies",
                })

        # Risk: no verification
        if not plan.verification:
            risks.append({
                "name": "No verification steps",
                "likelihood": "high",
                "impact": "high",
                "mitigation": "Add verification steps for each phase output",
            })

        # Risk: context-dependent risks
        context_str = str(context).lower()
        if "third-party" in context_str or "external" in context_str or "api" in context_str:
            risks.append({
                "name": "External dependency",
                "likelihood": "medium",
                "impact": "high",
                "mitigation": "Add fallback/mock for external services, set timeouts",
            })

        # Risk: complex phase with many tasks
        for phase in plan.phases:
            if len(phase.tasks) > 5:
                risks.append({
                    "name": f"Phase '{phase.name}' has too many tasks ({len(phase.tasks)})",
                    "likelihood": "medium",
                    "impact": "medium",
                    "mitigation": f"Split phase '{phase.name}' into smaller sub-phases",
                })

        # Risk: missing context
        if not context:
            risks.append({
                "name": "No context provided",
                "likelihood": "high",
                "impact": "medium",
                "mitigation": "Gather context before proceeding",
            })

        return risks

    def to_contract_format(self, plan: PlanSchema) -> dict[str, Any]:
        """
        Convert a PlanSchema to a dict compatible with Conductor Contract.

        Args:
            plan: The PlanSchema to convert

        Returns:
            Dict in Conductor Contract format
        """
        execution_order = []
        parallel_groups = []
        prefetch_queries: dict[str, str] = {}
        relevant_workers: list[str] = []
        todos: list[dict[str, Any]] = []

        for phase in plan.phases:
            phase_parallel = []
            for task in phase.tasks:
                task_id = f"{phase.name}_{len(phase_parallel)}"
                execution_order.append(task_id)
                phase_parallel.append(task_id)
                prefetch_queries[task_id] = task

                # Assign worker based on task keywords
                worker = self._infer_worker(task)
                if worker and worker not in relevant_workers:
                    relevant_workers.append(worker)

                todos.append({
                    "id": task_id,
                    "description": task,
                    "assigned_to": worker,
                    "phase": phase.name,
                    "dependencies": phase.dependencies,
                })

            if phase_parallel:
                parallel_groups.append(phase_parallel)

        return {
            "relevant_workers": relevant_workers,
            "prefetch_queries": prefetch_queries,
            "parallel_groups": parallel_groups,
            "verification_needed": ["verifier_engineer"],
            "execution_order": execution_order,
            "todos": todos,
            "goal": plan.goal,
            "risks": plan.risks,
            "next_step": plan.next_step,
        }

    # ── Private helpers ──────────────────────────────────────────

    def _extract_scope_in(
        self, objective: str, context: dict[str, Any]
    ) -> list[str]:
        """Extract what's in scope from objective and context."""
        items = []
        if objective:
            items.append(objective.strip())
        for key in ("features", "requirements", "deliverables"):
            val = context.get(key)
            if val:
                if isinstance(val, list):
                    items.extend(str(v) for v in val)
                else:
                    items.append(str(val))
        return items

    def _extract_scope_out(
        self, objective: str, context: dict[str, Any]
    ) -> list[str]:
        """Extract what's out of scope from context."""
        items = []
        for key in ("exclusions", "out_of_scope", "not_included"):
            val = context.get(key)
            if val:
                if isinstance(val, list):
                    items.extend(str(v) for v in val)
                else:
                    items.append(str(val))
        return items

    def _build_phases(
        self,
        objective: str,
        context: dict[str, Any],
        available_workers: list[str],
        complexity: str,
    ) -> list[PlanPhase]:
        """Build execution phases based on objective analysis."""
        phases: list[PlanPhase] = []

        # Phase 1: Understanding/Setup
        setup_tasks = ["Clarify requirements", "Set up project structure"]
        if context.get("framework"):
            setup_tasks.append(f"Initialize {context['framework']} project")
        phases.append(PlanPhase(
            name="setup",
            objective="Understand requirements and set up project",
            tasks=setup_tasks,
            dependencies=[],
            estimated_complexity="simple",
            gate_criteria=["Requirements documented", "Project initialized"],
        ))

        # Phase 2: Implementation (always present)
        impl_tasks = self._generate_impl_tasks(objective, context)
        phases.append(PlanPhase(
            name="implementation",
            objective="Implement the core functionality",
            tasks=impl_tasks,
            dependencies=["setup"],
            estimated_complexity=complexity,
            gate_criteria=["Core functionality implemented", "No compilation errors"],
        ))

        # Phase 3: Testing/Verification (if complexity > simple)
        if complexity != "simple":
            phases.append(PlanPhase(
                name="verification",
                objective="Test and verify the implementation",
                tasks=[
                    "Write unit tests for core logic",
                    "Run integration tests",
                    "Verify against specification",
                ],
                dependencies=["implementation"],
                estimated_complexity="medium",
                gate_criteria=["All tests pass", "Spec requirements met"],
            ))

        # Phase 4: Polish (if complex)
        if complexity == "complex":
            phases.append(PlanPhase(
                name="polish",
                objective="Polish and optimize",
                tasks=[
                    "Code review and refactoring",
                    "Performance optimization",
                    "Documentation",
                ],
                dependencies=["verification"],
                estimated_complexity="medium",
                gate_criteria=["Code reviewed", "Documentation complete"],
            ))

        return phases

    def _generate_impl_tasks(
        self, objective: str, context: dict[str, Any]
    ) -> list[str]:
        """Generate implementation tasks from objective."""
        tasks = []
        obj_lower = (objective or "").lower()

        # Common task patterns
        if "api" in obj_lower or "endpoint" in obj_lower:
            tasks.append("Design API schema")
            tasks.append("Implement API endpoints")
        if "database" in obj_lower or "model" in obj_lower or "schema" in obj_lower:
            tasks.append("Design data models")
            tasks.append("Implement database schema")
        if "auth" in obj_lower:
            tasks.append("Implement authentication")
            tasks.append("Implement authorization")
        if "ui" in obj_lower or "frontend" in obj_lower or "page" in obj_lower:
            tasks.append("Build UI components")
            tasks.append("Connect UI to backend")
        if "test" in obj_lower:
            tasks.append("Write tests")

        # If no specific tasks matched, create generic ones
        if not tasks:
            tasks = [f"Implement: {objective}"]

        return tasks

    def _build_verification(self, phases: list[PlanPhase]) -> list[str]:
        """Build verification steps from phases."""
        steps = []
        for phase in phases:
            for criterion in phase.gate_criteria:
                steps.append(f"[{phase.name}] {criterion}")
        return steps

    def _infer_worker(self, task_description: str) -> str:
        """Infer the best worker for a task based on keywords."""
        task_lower = (task_description or "").lower()
        for keyword, worker in _DEFAULT_WORKER_MAP.items():
            if keyword in task_lower:
                return worker
        return "coder_backend"
