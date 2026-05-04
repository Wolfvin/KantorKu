"""Sentinel — Error logging and lessons. Uses Llama 4 Scout (local/free)."""

from __future__ import annotations
from kantorku.worker.base import BaseWorker, Task, TaskResult

class Sentinel(BaseWorker):
    async def handle(self, task: Task) -> TaskResult:
        prompt = f"""Log the following error/lesson:

Task: {task.instruction}
Error details: {task.context}

Extract:
1. What went wrong
2. Why it happened
3. How to prevent it in the future
4. Category (config, runtime, logic, integration, etc.)"""

        response = await self.llm_call(prompt)
        return TaskResult(task_id=task.id, status="done", output=response)
