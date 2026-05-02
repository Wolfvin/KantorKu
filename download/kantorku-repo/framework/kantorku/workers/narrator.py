"""Narrator — Format output for client. Uses Llama 4 Scout."""

from __future__ import annotations
from kantorku.worker.base import BaseWorker, Task, TaskResult

class Narrator(BaseWorker):
    async def handle(self, task: Task) -> TaskResult:
        prompt = f"""Format the following result for client presentation:

Task: {task.instruction}
Raw result: {task.context}

Create a clean, professional summary that:
1. Highlights key deliverables
2. Notes any caveats or limitations
3. Provides next steps
4. Is concise but complete"""

        response = await self.llm_call(prompt)
        return TaskResult(task_id=task.id, status="done", output=response)
