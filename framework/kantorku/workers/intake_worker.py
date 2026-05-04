"""IntakeWorker — Parse and classify client messages. Uses Llama 4 Scout."""

from __future__ import annotations
from kantorku.worker.base import BaseWorker, Task, TaskResult

class IntakeWorker(BaseWorker):
    async def handle(self, task: Task) -> TaskResult:
        session_ctx = self._build_context_section(task)
        conv_summary = self.get_conversation_summary(task.session_id)
        ring1_ctx = await self.get_context(task.id)

        context_parts = [f"""Parse and classify this client message:

Message: {task.instruction}"""]

        if session_ctx:
            context_parts.append(session_ctx)

        if conv_summary:
            context_parts.append(
                f"Your previous work in this session:\n{conv_summary}"
            )

        if ring1_ctx:
            context_parts.append(
                f"Prefetched context:\n"
                f"{ring1_ctx.get('summary', '')}\n"
                f"Files: {ring1_ctx.get('files', [])}\n"
                f"Patterns: {ring1_ctx.get('patterns', [])}"
            )

        context_parts.append("""Respond with JSON:
{{
    "type": "new_request|follow_up|revision|question|feedback",
    "urgency": "low|medium|high|critical",
    "domain": ["frontend", "backend", "api", ...],
    "technologies": ["rust", "python", ...],
    "summary": "one-line summary",
    "key_requirements": ["req1", "req2"],
    "estimated_complexity": "simple|moderate|complex"
}}""")

        prompt = "\n\n".join(context_parts)

        result = await self.llm_call_structured(prompt, session_id=task.session_id)
        return TaskResult(
            task_id=task.id,
            status="done",
            output=str(result),
            data=result,
        )
