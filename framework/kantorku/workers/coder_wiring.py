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
        prompt += "\n\nFocus on reliability, error handling, and proper interface design."

        response = await self.llm_call(prompt, session_id=task.session_id)
        return TaskResult(task_id=task.id, status="done", output=response, files=[])
