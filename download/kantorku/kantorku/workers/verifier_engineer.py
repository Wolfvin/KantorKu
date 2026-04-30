"""
VerifierEngineer — Logic/test/security reviewer.
Uses MiniMax M2.5 for 80.2% SWE frontier quality at $0.12/M.
"""

from __future__ import annotations
from typing import Any
from kantorku.worker.base import BaseWorker, Task, TaskResult

ENGINEER_SKILL = """You are the Engineering Verifier in kantorku — a digital office.

Your job: Review code output from an engineering perspective.

Check for:
1. Logic correctness and edge cases
2. Error handling and recovery
3. Test coverage and quality
4. Security vulnerabilities
5. Performance and resource usage
6. Code style and maintainability
7. API contract compliance

Respond with JSON:
{
    "issues": ["issue1", "issue2", ...],
    "approved": true/false,
    "suggestions": ["suggestion1", ...]
}"""


class VerifierEngineer(BaseWorker):
    async def handle(self, task: Task) -> TaskResult:
        results = task.context.get("results", {})
        contract = task.context.get("contract", {})

        prompt = f"""Review the following output for engineering quality:

Contract: {contract.get('title', 'Unknown')}
Results: {results}

Check for logic errors, security issues, test coverage, and code quality.
Respond with JSON containing issues (list), approved (bool), and suggestions (list)."""

        result = await self.llm_call_structured(prompt)
        issues = result.get("issues", [])
        approved = result.get("approved", len(issues) == 0)

        return TaskResult(
            task_id=task.id,
            status="done",
            output=str(result),
            data={"issues": issues, "approved": approved},
        )
