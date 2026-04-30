"""Auditor — Code review with nuance. Uses Claude Sonnet 4.6."""

from __future__ import annotations
from kantorku.worker.base import BaseWorker, Task, TaskResult

class Auditor(BaseWorker):
    async def handle(self, task: Task) -> TaskResult:
        prompt = f"""Audit the following code/output:

Task: {task.instruction}
Context: {task.context}

Review for:
1. Architectural soundness
2. Code quality and maintainability
3. Security considerations
4. Performance implications
5. Compliance with project standards"""

        response = await self.llm_call(prompt)
        return TaskResult(task_id=task.id, status="done", output=response)
