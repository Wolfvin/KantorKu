"""Scribe — Documentation writer. Uses DeepSeek V4 Flash."""

from __future__ import annotations
from kantorku.worker.base import BaseWorker, Task, TaskResult

class Scribe(BaseWorker):
    async def handle(self, task: Task) -> TaskResult:
        session_ctx = self._build_context_section(task)
        conv_summary = self.get_conversation_summary(task.session_id)

        context_parts = [f"Write documentation for:\n\nTask: {task.instruction}"]

        if session_ctx:
            context_parts.append(session_ctx)

        if conv_summary:
            context_parts.append(
                f"Previous documentation in this session:\n{conv_summary}"
            )

        prompt = "\n\n".join(context_parts)
        prompt += "\n\nCreate:\n1. API documentation\n2. Usage examples\n3. Configuration reference\n4. Migration guide (if applicable)\n\nBe clear, concise, and thorough."

        response = await self.llm_call(prompt, session_id=task.session_id)
        return TaskResult(task_id=task.id, status="done", output=response)
