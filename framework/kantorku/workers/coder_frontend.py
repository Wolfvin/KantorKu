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
        # Gather all context sources
        ring1_ctx = await self.get_context(task.id)
        session_ctx = self._build_context_section(task)
        conv_summary = self.get_conversation_summary(task.session_id)

        context_parts = [f"Task: {task.instruction}"]

        if session_ctx:
            context_parts.append(session_ctx)

        if conv_summary:
            context_parts.append(
                f"Your previous work in this session:\n{conv_summary}"
            )

        if ring1_ctx:
            context_parts.append(
                f"Prefetched context:\n"
                f"{ring1_ctx.get('summary', '')}\n"
                f"Files: {ring1_ctx.get('files', [])}\n"
                f"Patterns: {ring1_ctx.get('patterns', [])}"
            )
        else:
            context_parts.append("No prefetched context available. Implement from scratch.")

        prompt = "\n\n".join(context_parts)
        prompt += "\n\nFocus on visual quality, component structure, and user experience."

        response = await self.llm_call(prompt, session_id=task.session_id)
        return TaskResult(task_id=task.id, status="done", output=response, files=[])
