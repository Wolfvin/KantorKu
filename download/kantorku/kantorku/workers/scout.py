"""Scout — Research and real-time search. Uses Gemini 2.5 Pro."""

from __future__ import annotations
from kantorku.worker.base import BaseWorker, Task, TaskResult

class Scout(BaseWorker):
    async def handle(self, task: Task) -> TaskResult:
        prompt = f"""Research the following topic:

Task: {task.instruction}

Provide:
1. Key findings and current state
2. Best practices and recommendations
3. Relevant libraries, tools, or patterns
4. Potential pitfalls to avoid"""

        response = await self.llm_call(prompt)
        return TaskResult(task_id=task.id, status="done", output=response)
