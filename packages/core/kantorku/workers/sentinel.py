"""Sentinel — Error logging and lessons. Uses Llama 4 Scout (local/free)."""

from __future__ import annotations
from kantorku.worker.base import BaseWorker, Task, TaskResult

class Sentinel(BaseWorker):
    async def handle(self, task: Task) -> TaskResult:
        session_ctx = self._build_context_section(task)
        conv_summary = self.get_conversation_summary(task.session_id)

        context_parts = [f"Log the following error/lesson:\n\nTask: {task.instruction}"]

        if session_ctx:
            context_parts.append(session_ctx)

        if conv_summary:
            context_parts.append(
                f"Previous errors logged in this session:\n{conv_summary}"
            )

        prompt = "\n\n".join(context_parts)
        prompt += "\n\nExtract:\n1. What went wrong\n2. Why it happened\n3. How to prevent it in the future\n4. Category (config, runtime, logic, integration, etc.)"

        response = await self.llm_call(prompt, session_id=task.session_id)
        return TaskResult(task_id=task.id, status="done", output=response)
