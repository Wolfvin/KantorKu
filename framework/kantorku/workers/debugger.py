"""Debugger — Root cause analysis. Uses DeepSeek V3.2."""

from __future__ import annotations
from kantorku.worker.base import BaseWorker, Task, TaskResult

class Debugger(BaseWorker):
    async def handle(self, task: Task) -> TaskResult:
        prompt = f"""Debug the following issue:

Task: {task.instruction}
Context: {task.context}

Analyze the root cause and provide:
1. Root cause analysis
2. Steps to reproduce
3. Suggested fix
4. Prevention measures"""

        response = await self.llm_call(prompt)
        return TaskResult(task_id=task.id, status="done", output=response)
