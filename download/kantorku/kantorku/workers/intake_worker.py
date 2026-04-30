"""IntakeWorker — Parse and classify client messages. Uses Llama 4 Scout."""

from __future__ import annotations
from kantorku.worker.base import BaseWorker, Task, TaskResult

class IntakeWorker(BaseWorker):
    async def handle(self, task: Task) -> TaskResult:
        prompt = f"""Parse and classify this client message:

Message: {task.instruction}

Respond with JSON:
{{
    "type": "new_request|follow_up|revision|question|feedback",
    "urgency": "low|medium|high|critical",
    "domain": ["frontend", "backend", "api", ...],
    "technologies": ["rust", "python", ...],
    "summary": "one-line summary",
    "key_requirements": ["req1", "req2"],
    "estimated_complexity": "simple|moderate|complex"
}}"""

        result = await self.llm_call_structured(prompt)
        return TaskResult(
            task_id=task.id,
            status="done",
            output=str(result),
            data=result,
        )
