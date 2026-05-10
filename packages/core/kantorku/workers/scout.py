"""Scout — Research and real-time search. Uses Gemini 2.5 Pro."""

from __future__ import annotations
from kantorku.worker.base import BaseWorker, Task, TaskResult

class Scout(BaseWorker):
    async def handle(self, task: Task) -> TaskResult:
        session_ctx = self._build_context_section(task)
        conv_summary = self.get_conversation_summary(task.session_id)

        context_parts = [f"Research the following topic:\n\nTask: {task.instruction}"]

        if session_ctx:
            context_parts.append(session_ctx)

        if conv_summary:
            context_parts.append(
                f"Your previous research in this session:\n{conv_summary}"
            )

        prompt = "\n\n".join(context_parts)
        prompt += "\n\nProvide:\n1. Key findings and current state\n2. Best practices and recommendations\n3. Relevant libraries, tools, or patterns\n4. Potential pitfalls to avoid"

        response = await self.llm_call(prompt, session_id=task.session_id)
        return TaskResult(task_id=task.id, status="done", output=response)
