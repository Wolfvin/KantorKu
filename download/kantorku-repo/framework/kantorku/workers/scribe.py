"""Scribe — Documentation writer. Uses DeepSeek V4 Flash."""

from __future__ import annotations
from kantorku.worker.base import BaseWorker, Task, TaskResult

class Scribe(BaseWorker):
    async def handle(self, task: Task) -> TaskResult:
        prompt = f"""Write documentation for:

Task: {task.instruction}
Context: {task.context}

Create:
1. API documentation
2. Usage examples
3. Configuration reference
4. Migration guide (if applicable)

Be clear, concise, and thorough."""

        response = await self.llm_call(prompt)
        return TaskResult(task_id=task.id, status="done", output=response)
