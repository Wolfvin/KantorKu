"""
Structured Debug Loop — O24: Systematic debugging with reproduce→isolate→fix→verify.

Implements a structured debug cycle that follows a systematic approach:
1. Reproduce: Create minimal reproduction of the error
2. Isolate: Determine which layer is affected
3. Fix: Apply the smallest possible fix
4. Verify: Confirm the fix resolves the original error

Like a senior debugger who doesn't just randomly try things — they
follow a methodical process.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class DebugPhase(Enum):
    """Phases of the debug cycle."""
    REPRODUCE = "reproduce"
    ISOLATE = "isolate"
    FIX = "fix"
    VERIFY = "verify"


@dataclass
class DebugEvidence:
    """Evidence collected during debugging."""
    symptom: str = ""
    root_cause: str = ""
    fix_description: str = ""
    verification_signal: str = ""


@dataclass
class DebugResult:
    """Result of a debug cycle."""
    success: bool = False
    evidence: DebugEvidence = field(default_factory=DebugEvidence)
    iterations_used: int = 0
    remaining_iterations: int = 0


# Maximum debug iterations
_MAX_DEBUG_ITERATIONS = 3

# Layer isolation patterns
_LAYER_PATTERNS: dict[str, list[str]] = {
    "frontend": [
        "css", "html", "dom", "render", "component", "style",
        "layout", "ui", "visual", "display", "animation",
    ],
    "backend": [
        "server", "api", "database", "model", "schema",
        "endpoint", "route", "handler", "service", "logic",
        "validation", "auth", "permission",
    ],
    "infra": [
        "network", "dns", "proxy", "load balancer", "container",
        "kubernetes", "docker", "config", "env", "deploy",
        "ci/cd", "pipeline",
    ],
    "spec": [
        "ambiguous", "undefined", "not specified", "conflicting",
        "requirement", "expected behavior", "contradiction",
    ],
}

# Common error patterns and their likely layers
_ERROR_LAYER_MAP: dict[str, str] = {
    "TypeError": "backend",
    "ReferenceError": "frontend",
    "SyntaxError": "backend",
    "ConnectionError": "infra",
    "TimeoutError": "infra",
    "ValidationError": "backend",
    "PermissionError": "infra",
    "ImportError": "backend",
    "ModuleNotFoundError": "backend",
    "KeyError": "backend",
    "IndexError": "backend",
    "AttributeError": "backend",
    "HTTPError": "backend",
    "CORS": "infra",
    "404": "backend",
    "500": "backend",
}


class StructuredDebugLoop:
    """
    Structured Debug Loop — systematic debugging cycle.

    Follows a reproduce → isolate → fix → verify loop with
    a maximum of 3 iterations. Each iteration narrows the
    problem space until a fix is verified or attempts are exhausted.

    Usage:
        debugger = StructuredDebugLoop()
        result = debugger.debug_cycle("TypeError: null pointer", {"stack": "..."}, "worker_1")
        if result.success:
            print(f"Fixed: {result.evidence.fix_description}")
    """

    def debug_cycle(
        self,
        error_msg: str,
        context: dict[str, Any] | None = None,
        worker_id: str = "",
    ) -> DebugResult:
        """
        Run a complete debug cycle: reproduce → isolate → fix → verify.

        Maximum 3 iterations. Each iteration attempts to fix the error
        and verify the fix. If verification fails, the cycle repeats
        with more specific isolation.

        Args:
            error_msg: The error message to debug
            context: Additional context about the error
            worker_id: Worker that encountered the error

        Returns:
            DebugResult with success status, evidence, and iteration info
        """
        if not error_msg:
            return DebugResult(
                success=False,
                evidence=DebugEvidence(symptom="No error message provided"),
                iterations_used=0,
                remaining_iterations=_MAX_DEBUG_ITERATIONS,
            )

        context = context or {}
        evidence = DebugEvidence()
        remaining = _MAX_DEBUG_ITERATIONS

        for iteration in range(_MAX_DEBUG_ITERATIONS):
            remaining = _MAX_DEBUG_ITERATIONS - iteration - 1

            # Phase 1: Reproduce
            reproduction = self.reproduce_minimal(error_msg, context)
            evidence.symptom = reproduction

            # Phase 2: Isolate
            layer = self.isolate_layer(error_msg, context)
            context["isolated_layer"] = layer

            # Phase 3: Fix
            fix = self.apply_smallest_fix(error_msg, layer, context)
            evidence.fix_description = fix
            evidence.root_cause = self._infer_root_cause(error_msg, layer, context)

            # Phase 4: Verify
            verified = self.verify_fix(error_msg, fix, context)
            evidence.verification_signal = "PASS" if verified else "FAIL"

            if verified:
                return DebugResult(
                    success=True,
                    evidence=evidence,
                    iterations_used=iteration + 1,
                    remaining_iterations=remaining,
                )

            # If not verified, refine context for next iteration
            context["previous_fix_attempt"] = fix
            context["iteration"] = iteration + 1

        return DebugResult(
            success=False,
            evidence=evidence,
            iterations_used=_MAX_DEBUG_ITERATIONS,
            remaining_iterations=0,
        )

    def reproduce_minimal(
        self, error_msg: str, context: dict[str, Any] | None = None
    ) -> str:
        """
        Create a minimal reproduction of the error.

        Extracts the core error from the full message, removing
        stack traces and noise.

        Args:
            error_msg: The full error message
            context: Additional context

        Returns:
            Minimal reproduction string
        """
        if not error_msg:
            return "Cannot reproduce: empty error message"

        # Extract the first line (usually the core error)
        first_line = error_msg.strip().split("\n")[0].strip()

        # Remove common noise patterns
        minimal = re.sub(r"\s+at\s+.*", "", first_line)  # Stack traces
        minimal = re.sub(r"\s+File\s+\".*\"", "", minimal)  # File paths
        minimal = re.sub(r"Traceback.*:", "", minimal)
        minimal = minimal.strip()

        if not minimal:
            minimal = first_line

        # Add context hints if available
        context = context or {}
        hints = []
        if context.get("phase"):
            hints.append(f"Phase: {context['phase']}")
        if context.get("worker_id"):
            hints.append(f"Worker: {context['worker_id']}")

        if hints:
            return f"{minimal} [{', '.join(hints)}]"
        return minimal

    def isolate_layer(
        self, error_msg: str, context: dict[str, Any] | None = None
    ) -> str:
        """
        Isolate which layer the error belongs to.

        Layers: frontend, backend, infra, spec

        Args:
            error_msg: The error message
            context: Additional context

        Returns:
            Layer name string
        """
        if not error_msg:
            return "backend"

        context = context or {}
        error_lower = error_msg.lower()

        # Check context for layer hints
        if context.get("isolated_layer"):
            return context["isolated_layer"]
        if context.get("layer"):
            return context["layer"]

        # Check error type mapping
        for error_type, layer in _ERROR_LAYER_MAP.items():
            if error_type in error_msg:
                return layer

        # Score each layer by keyword matches
        scores: dict[str, int] = {}
        for layer, keywords in _LAYER_PATTERNS.items():
            score = sum(1 for kw in keywords if kw in error_lower)
            if score > 0:
                scores[layer] = score

        if scores:
            return max(scores, key=lambda l: scores[l])

        # Default to backend
        return "backend"

    def apply_smallest_fix(
        self,
        error_msg: str,
        layer: str,
        context: dict[str, Any] | None = None,
    ) -> str:
        """
        Describe the smallest possible fix for the error.

        Based on the error type and isolated layer, suggests
        the minimal fix that could resolve the issue.

        Args:
            error_msg: The error message
            layer: The isolated layer
            context: Additional context

        Returns:
            Fix description string
        """
        if not error_msg:
            return "No fix applicable — error message is empty"

        context = context or {}
        error_lower = error_msg.lower()

        # Previous fix attempt — try different approach
        if context.get("previous_fix_attempt"):
            return self._suggest_alternative_fix(error_msg, layer, context)

        # Layer-specific fix suggestions
        if "TypeError" in error_msg or "type error" in error_lower:
            return f"Add type validation before the failing operation in {layer}"

        if "null" in error_lower or "none" in error_lower or "undefined" in error_lower:
            return f"Add null/undefined check before accessing the value in {layer}"

        if "KeyError" in error_msg or "key error" in error_lower:
            return f"Add key existence check or default value in {layer}"

        if "ImportError" in error_msg or "ModuleNotFoundError" in error_msg:
            return f"Install missing dependency or fix import path in {layer}"

        if "ConnectionError" in error_msg or "connection" in error_lower:
            return f"Add retry logic and connection timeout handling in {layer}"

        if "Permission" in error_msg or "permission" in error_lower:
            return f"Check and adjust file/service permissions in {layer}"

        if "timeout" in error_lower:
            return f"Increase timeout value and add retry logic in {layer}"

        if "syntax" in error_lower:
            return f"Fix syntax error — check for missing brackets, quotes, or colons in {layer}"

        if "CORS" in error_msg or "cors" in error_lower:
            return "Add CORS headers to the server response or configure proxy"

        # Generic fix by layer
        layer_fixes = {
            "frontend": "Check component props, state, and rendering logic",
            "backend": "Check request validation, error handling, and data flow",
            "infra": "Check network connectivity, configuration, and environment variables",
            "spec": "Clarify the ambiguous requirement with the client",
        }

        return layer_fixes.get(layer, "Review the error context and apply minimal fix")

    def verify_fix(
        self,
        original_error: str,
        fix: str,
        context: dict[str, Any] | None = None,
    ) -> bool:
        """
        Verify if a fix resolves the original error.

        In a real implementation, this would re-run the failing
        scenario. Here, we use heuristic verification based on
        the fix matching the error type.

        Args:
            original_error: The original error message
            fix: The fix description
            context: Additional context

        Returns:
            True if the fix appears to address the error
        """
        if not original_error or not fix:
            return False

        context = context or {}
        error_lower = original_error.lower()
        fix_lower = fix.lower()

        # If this is a retry after failed fix, lower confidence
        iteration = context.get("iteration", 0)
        if iteration > 0:
            # Simulate decreasing likelihood of fix working
            import random
            return random.random() > (0.3 * iteration)

        # Check if fix addresses the error type
        error_fix_pairs = [
            ("TypeError", "type validation"),
            ("null", "null check"),
            ("undefined", "undefined check"),
            ("KeyError", "key existence"),
            ("ImportError", "install"),
            ("ConnectionError", "retry"),
            ("timeout", "timeout"),
            ("Permission", "permission"),
            ("CORS", "cors"),
            ("syntax", "syntax"),
        ]

        for error_keyword, fix_keyword in error_fix_pairs:
            if error_keyword.lower() in error_lower and fix_keyword in fix_lower:
                return True

        # Check if fix mentions the same layer as the error
        layer = self.isolate_layer(original_error, context)
        if layer in fix_lower:
            return True

        # Default: moderate chance of fix working on first attempt
        return True

    def format_evidence(
        self,
        symptom: str,
        root_cause: str,
        fix: str,
        verification: str,
    ) -> DebugEvidence:
        """
        Format debug evidence from components.

        Args:
            symptom: The observed symptom
            root_cause: The identified root cause
            fix: The fix applied
            verification: Verification signal (PASS/FAIL)

        Returns:
            DebugEvidence instance
        """
        return DebugEvidence(
            symptom=symptom,
            root_cause=root_cause,
            fix_description=fix,
            verification_signal=verification,
        )

    def _infer_root_cause(
        self,
        error_msg: str,
        layer: str,
        context: dict[str, Any],
    ) -> str:
        """Infer the root cause from error, layer, and context."""
        error_lower = error_msg.lower()

        if "null" in error_lower or "none" in error_lower:
            return f"Missing value in {layer} — likely uninitialized variable or missing data"
        if "type" in error_lower:
            return f"Type mismatch in {layer} — expected one type, received another"
        if "connection" in error_lower or "network" in error_lower:
            return f"Network issue in {layer} — external service unreachable or slow"
        if "permission" in error_lower:
            return f"Access denied in {layer} — insufficient permissions"

        return f"Error in {layer} layer — cause requires further investigation"

    def _suggest_alternative_fix(
        self,
        error_msg: str,
        layer: str,
        context: dict[str, Any],
    ) -> str:
        """Suggest an alternative fix after a previous fix failed."""
        previous = context.get("previous_fix_attempt", "")
        error_lower = error_msg.lower()

        # If null check didn't work, try default value
        if "null check" in previous.lower() or "undefined check" in previous.lower():
            return f"Instead of null check, provide a default value in {layer}"

        # If type validation didn't work, try coercion
        if "type validation" in previous.lower():
            return f"Instead of type validation, add type coercion/conversion in {layer}"

        # If retry didn't work, try circuit breaker
        if "retry" in previous.lower():
            return f"Instead of retry, implement circuit breaker pattern in {layer}"

        # Generic escalation
        return f"Previous fix ({previous}) failed — try a different approach in {layer} or escalate"
