"""
CoderWiring — API/WebSocket/MCP/Glue code specialist.
Uses Gemini 3.1 Pro for BFCL 99.3 tool calling score and 1M context.
"""

from __future__ import annotations
from typing import Any
from kantorku.worker.base import BaseWorker, Task, TaskResult

WIRING_SKILL = """You are the Wiring Coder in kantorku — a digital office.

Your expertise:
- API integration, REST, GraphQL, gRPC
- WebSocket, real-time communication
- MCP (Model Context Protocol) integration
- Glue code between services and components
- Authentication, authorization middleware
- Third-party SDK integration

When implementing features:
1. Check existing integration patterns in the codebase
2. Handle connection errors, retries, and timeouts
3. Implement proper type-safe interfaces
4. Consider rate limiting and circuit breakers
5. Write integration tests for external dependencies"""


class CoderWiring(BaseWorker):
    async def handle(self, task: Task) -> TaskResult:
        context = await self.get_context(task.id)
        if context:
            prompt = f"""Task: {task.instruction}

Context already prepared:
{context.get('summary', '')}
Files: {context.get('files', [])}
Patterns: {context.get('patterns', [])}

Verify this context is still relevant, then implement the wiring/integration.
Focus on reliability, error handling, and proper interface design."""
        else:
            prompt = f"""Task: {task.instruction}

No prefetched context available. Implement from scratch.
Focus on reliability, error handling, and proper interface design."""

        response = await self.llm_call(prompt)
        return TaskResult(task_id=task.id, status="done", output=response, files=[])
