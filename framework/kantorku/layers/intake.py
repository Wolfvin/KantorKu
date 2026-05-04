"""
Intake — Transform freeform user messages into structured tasks.

The Intake layer sits between the raw client input and the Conductor.
It parses, classifies, and structures the message so the Conductor
can work more efficiently.

Uses a cheap, fast model (Llama 4 Scout) for parsing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from kantorku.providers.router import ProviderRouter
from kantorku.events.bus import EventBus


INTAKE_SYSTEM_PROMPT = """You are the Intake parser for kantorku — a digital office.

Your job is to classify and structure incoming client messages.

Analyze the message and respond with JSON:
```json
{
  "type": "new_request | follow_up | revision | question | feedback",
  "urgency": "low | medium | high | critical",
  "domain": ["frontend", "backend", "api", "database", "devops", "design", ...],
  "technologies": ["rust", "python", "react", ...],
  "summary": "One-line summary of what the client wants",
  "key_requirements": ["req1", "req2", ...],
  "estimated_complexity": "simple | moderate | complex | very_complex"
}
```

Be concise and accurate. Focus on extracting actionable information.
"""


@dataclass
class IntakeResult:
    """Parsed result from the Intake layer."""

    original_message: str = ""
    type: str = "new_request"
    urgency: str = "medium"
    domain: list[str] = field(default_factory=list)
    technologies: list[str] = field(default_factory=list)
    summary: str = ""
    key_requirements: list[str] = field(default_factory=list)
    estimated_complexity: str = "moderate"

    def to_dict(self) -> dict[str, Any]:
        return {
            "original_message": self.original_message,
            "type": self.type,
            "urgency": self.urgency,
            "domain": self.domain,
            "technologies": self.technologies,
            "summary": self.summary,
            "key_requirements": self.key_requirements,
            "estimated_complexity": self.estimated_complexity,
        }


class Intake:
    """
    Intake layer — parse and classify client messages.

    Uses a cheap, fast model for classification.
    The Conductor can use this structured data for better planning.

    Usage:
        intake = Intake(router=router, model="meta/llama4-scout")
        result = await intake.parse("Buat rate limiter di Rust, production grade")
        # result.type = "new_request"
        # result.technologies = ["rust"]
        # result.domain = ["backend"]
    """

    def __init__(
        self,
        router: ProviderRouter,
        bus: EventBus,
        model: str = "ollama/llama3",
    ) -> None:
        self.router = router
        self.bus = bus
        self.model = model

    async def parse(self, message: str, session_id: str = "") -> IntakeResult:
        """
        Parse a freeform message into structured data.

        Args:
            message: Raw client message
            session_id: Optional session identifier

        Returns:
            IntakeResult with classified and extracted information
        """
        try:
            response = await self.router.complete(
                model=self.model,
                messages=[
                    {"role": "system", "content": INTAKE_SYSTEM_PROMPT},
                    {"role": "user", "content": message},
                ],
                temperature=0.3,
            )

            return self._parse_response(message, response)

        except Exception:
            # Fallback: minimal parsing without LLM
            return IntakeResult(
                original_message=message,
                type="new_request",
                summary=message[:100],
            )

    def _parse_response(self, original: str, response: str) -> IntakeResult:
        """Parse the LLM response into an IntakeResult."""
        import json

        try:
            text = response.strip()
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()

            data = json.loads(text)

            return IntakeResult(
                original_message=original,
                type=data.get("type", "new_request"),
                urgency=data.get("urgency", "medium"),
                domain=data.get("domain", []),
                technologies=data.get("technologies", []),
                summary=data.get("summary", ""),
                key_requirements=data.get("key_requirements", []),
                estimated_complexity=data.get("estimated_complexity", "moderate"),
            )
        except (json.JSONDecodeError, IndexError):
            return IntakeResult(
                original_message=original,
                type="new_request",
                summary=original[:100],
            )

    async def classify_batch(
        self, messages: list[str], session_id: str = ""
    ) -> list[IntakeResult]:
        """Classify multiple messages in batch."""
        import asyncio
        tasks = [self.parse(msg, session_id) for msg in messages]
        return await asyncio.gather(*tasks)
