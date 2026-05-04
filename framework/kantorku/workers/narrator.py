"""Narrator — Format output for client. Uses Llama 4 Scout."""

from __future__ import annotations
from kantorku.worker.base import BaseWorker, Task, TaskResult

class Narrator(BaseWorker):
    async def handle(self, task: Task) -> TaskResult:
        session_ctx = self._build_context_section(task)
        conv_summary = self.get_conversation_summary(task.session_id)

        context_parts = [f"Format the following result for client presentation:\n\nTask: {task.instruction}"]

        if session_ctx:
            context_parts.append(session_ctx)

        if conv_summary:
            context_parts.append(
                f"Your previous formatting in this session:\n{conv_summary}"
            )

        prompt = "\n\n".join(context_parts)
        prompt += "\n\nCreate a clean, professional summary that:\n1. Highlights key deliverables\n2. Notes any caveats or limitations\n3. Provides next steps\n4. Is concise but complete"

        response = await self.llm_call(prompt, session_id=task.session_id)
        return TaskResult(task_id=task.id, status="done", output=response)
