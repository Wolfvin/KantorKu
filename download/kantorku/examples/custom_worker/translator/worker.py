"""
translator — Language Translator.

Custom worker with structured translation output.
Demonstrates plug-and-play worker with worker.py custom logic.
"""

from __future__ import annotations

from typing import Any
from kantorku.worker.base import BaseWorker, Task, TaskResult


class Translator(BaseWorker):
    """
    Language translator worker.

    Demonstrates a custom worker with structured output.
    SKILL.md is automatically injected as the system prompt.
    """

    async def handle(self, task: Task) -> TaskResult:
        # Extract target language from task context
        target_lang = task.context.get("target_language", "Indonesian")

        # Build prompt with context
        context_data = await self.get_context(task.id)
        if context_data:
            prompt = f"""Translate the following text to {target_lang}.

Previously prepared context:
{context_data.get('summary', '')}

Text to translate:
{task.instruction}

Provide the translation and any relevant notes."""
        else:
            prompt = f"""Translate the following text to {target_lang}.

Text to translate:
{task.instruction}

Provide the translation and any relevant notes about your choices."""

        # Use structured call for consistent JSON output
        result = await self.llm_call_structured(prompt)

        return TaskResult(
            task_id=task.id,
            status="done",
            output=result.get("translation", str(result)),
            data=result,
        )
