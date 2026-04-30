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
        context = await self.get_context(task.id)
        if context:
            prompt = f"""Task: {task.instruction}

Context already prepared:
{context.get('summary', '')}
Files: {context.get('files', [])}
Patterns: {context.get('patterns', [])}

Verify this context is still relevant, then implement based on it.
Focus on correctness, performance, and idiomatic code."""
        else:
            prompt = f"""Task: {task.instruction}

No prefetched context available. Implement from scratch.
Focus on correctness, performance, and idiomatic code."""

        response = await self.llm_call(prompt)
        return TaskResult(task_id=task.id, status="done", output=response, files=[])
