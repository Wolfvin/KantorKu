"""
VerifierDesigner — Visual/UX judge.
Uses Gemini 3.1 Pro for multimodal visual reasoning.
"""

from __future__ import annotations
from typing import Any
from kantorku.worker.base import BaseWorker, Task, TaskResult

DESIGNER_SKILL = """You are the Design Verifier in kantorku — a digital office.

Your job: Review code output from a visual/UX perspective.

Check for:
1. Visual consistency and polish
2. Responsive design across viewports
3. Accessibility (WCAG guidelines)
4. Loading states and transitions
5. Color contrast and typography
6. Animation smoothness and purpose
7. Mobile-first approach

Respond with JSON:
{
    "issues": ["issue1", "issue2", ...],
    "approved": true/false,
    "suggestions": ["suggestion1", ...]
}"""


class VerifierDesigner(BaseWorker):
    async def handle(self, task: Task) -> TaskResult:
        results = task.context.get("results", {})
        contract = task.context.get("contract", {})

        prompt = f"""Review the following output for visual/UX quality:

Contract: {contract.get('title', 'Unknown')}
Results: {results}

Check for visual consistency, accessibility, responsive design, and UX quality.
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
