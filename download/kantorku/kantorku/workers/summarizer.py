"""Summarizer — Long context compression. Uses DeepSeek V4 Flash."""

from __future__ import annotations
from kantorku.worker.base import BaseWorker, Task, TaskResult

class Summarizer(BaseWorker):
    async def handle(self, task: Task) -> TaskResult:
        prompt = f"""Summarize the following content:

Task: {task.instruction}
Content to summarize: {task.context}

Provide:
1. Executive summary (2-3 sentences)
2. Key points (bullet list)
3. Action items (if any)
4. Open questions (if any)"""

        response = await self.llm_call(prompt)
        return TaskResult(task_id=task.id, status="done", output=response)
