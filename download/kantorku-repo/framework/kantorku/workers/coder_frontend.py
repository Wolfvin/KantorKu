"""
CoderFrontend — React/CSS/UI/Visual specialist.
Uses Claude Sonnet for best WebDev Arena scores and visual quality.
"""

from __future__ import annotations
from typing import Any
from kantorku.worker.base import BaseWorker, Task, TaskResult

FRONTEND_SKILL = """You are the Frontend Coder in kantorku — a digital office.

Your expertise:
- React 19, Next.js, TypeScript
- CSS/Tailwind, animations, responsive design
- Component architecture, state management
- Visual quality, user experience, accessibility
- shadcn/ui, Radix UI, Framer Motion

When implementing features:
1. Prioritize visual quality and user experience
2. Use modern React patterns (hooks, suspense, server components)
3. Ensure responsive design and accessibility
4. Write clean, well-structured component code
5. Consider performance (lazy loading, code splitting)"""


class CoderFrontend(BaseWorker):
    async def handle(self, task: Task) -> TaskResult:
        context = await self.get_context(task.id)
        if context:
            prompt = f"""Task: {task.instruction}

Context already prepared:
{context.get('summary', '')}
Files: {context.get('files', [])}
Patterns: {context.get('patterns', [])}

Verify this context is still relevant, then implement based on it.
Focus on visual quality, component structure, and user experience."""
        else:
            prompt = f"""Task: {task.instruction}

No prefetched context available. Implement from scratch.
Focus on visual quality, component structure, and user experience."""

        response = await self.llm_call(prompt)
        return TaskResult(task_id=task.id, status="done", output=response, files=[])
