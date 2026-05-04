"""Auditor — Code review with nuance. Uses Claude Sonnet 4.6."""

from __future__ import annotations
from kantorku.worker.base import BaseWorker, Task, TaskResult

class Auditor(BaseWorker):
    async def handle(self, task: Task) -> TaskResult:
        session_ctx = self._build_context_section(task)
        conv_summary = self.get_conversation_summary(task.session_id)

        context_parts = [f"Audit the following code/output:\n\nTask: {task.instruction}"]

        if session_ctx:
            context_parts.append(session_ctx)

        if conv_summary:
            context_parts.append(
                f"Your previous audits in this session:\n{conv_summary}"
            )

        prompt = "\n\n".join(context_parts)
        prompt += "\n\nReview for:\n1. Architectural soundness\n2. Code quality and maintainability\n3. Security considerations\n4. Performance implications\n5. Compliance with project standards"

        response = await self.llm_call(prompt, session_id=task.session_id)
        return TaskResult(task_id=task.id, status="done", output=response)
