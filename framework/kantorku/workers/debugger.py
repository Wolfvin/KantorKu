"""Debugger — Root cause analysis. Uses DeepSeek V3.2."""

from __future__ import annotations
from kantorku.worker.base import BaseWorker, Task, TaskResult

class Debugger(BaseWorker):
    async def handle(self, task: TaskResult) -> TaskResult:
        session_ctx = self._build_context_section(task)
        conv_summary = self.get_conversation_summary(task.session_id)

        context_parts = [f"Debug the following issue:\n\nTask: {task.instruction}"]

        if session_ctx:
            context_parts.append(session_ctx)

        if conv_summary:
            context_parts.append(
                f"Your previous debugging in this session:\n{conv_summary}"
            )

        prompt = "\n\n".join(context_parts)
        prompt += "\n\nAnalyze the root cause and provide:\n1. Root cause analysis\n2. Steps to reproduce\n3. Suggested fix\n4. Prevention measures"

        response = await self.llm_call(prompt, session_id=task.session_id)
        return TaskResult(task_id=task.id, status="done", output=response)
