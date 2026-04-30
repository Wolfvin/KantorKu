"""
BaseProvider — Abstract base for all LLM providers.

All providers must implement:
- complete(): Single chat completion
- complete_stream(): Streaming chat completion
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, AsyncIterator


class BaseProvider(ABC):
    """
    Abstract base class for LLM providers.

    Each provider wraps a specific LLM API (Anthropic, Google, etc.)
    and normalizes the interface to a common format.
    """

    @abstractmethod
    async def complete(
        self,
        model: str,
        messages: list[dict[str, str]],
        **kwargs: Any,
    ) -> str:
        """
        Send a chat completion request.

        Args:
            model: Model name (without provider prefix, e.g. "claude-opus-4-6")
            messages: Chat messages in standard format
            **kwargs: Additional parameters

        Returns:
            The assistant's response text
        """
        ...

    async def complete_stream(
        self,
        model: str,
        messages: list[dict[str, str]],
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        """
        Stream a chat completion response.

        Default implementation: call complete() and yield the whole response.
        Override for true streaming.
        """
        response = await self.complete(model=model, messages=messages, **kwargs)
        yield response

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name for identification."""
        ...
