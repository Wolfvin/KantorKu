"""Summarizer — Long context compression. Uses DeepSeek V4 Flash."""

from __future__ import annotations
from kantorku.worker.base import BaseWorker, Task, TaskResult

class Summarizer(BaseWorker):
    async def handle(self, task: Task) -> TaskResult:
        session_ctx = self._build_context_section(task)
        conv_summary = self.get_conversation_summary(task.session_id)

        context_parts = [f"Summarize the following content:\n\nTask: {task.instruction}"]

        if session_ctx:
            context_parts.append(session_ctx)

        if conv_summary:
            context_parts.append(
                f"Your previous summaries in this session:\n{conv_summary}"
            )

        prompt = "\n\n".join(context_parts)
        prompt += "\n\nProvide:\n1. Executive summary (2-3 sentences)\n2. Key points (bullet list)\n3. Action items (if any)\n4. Open questions (if any)"

        response = await self.llm_call(prompt, session_id=task.session_id)
        return TaskResult(task_id=task.id, status="done", output=response)
