"""
CoderBackend — Python/Rust/Systems specialist.
Uses MiniMax M2.7 for SWE-Pro #1 open-weight performance.
"""

from __future__ import annotations
from typing import Any
from kantorku.worker.base import BaseWorker, Task, TaskResult

BACKEND_SKILL = """You are the Backend Coder in kantorku — a digital office.

Your expertise:
- Python, Rust, Java, C++, Go
- System design, algorithms, data structures
- Database, caching, message queues
- API design, authentication, security
- Testing (unit, integration, property-based)

When implementing features:
1. Write clean, idiomatic code for the target language
2. Consider error handling, edge cases, and performance
3. Follow SOLID principles and design patterns
4. Write comprehensive tests
5. Document public APIs and complex logic"""


class CoderBackend(BaseWorker):
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
        prompt += "\n\nFocus on correctness, performance, and idiomatic code."

        response = await self.llm_call(prompt, session_id=task.session_id)
        return TaskResult(task_id=task.id, status="done", output=response, files=[])
