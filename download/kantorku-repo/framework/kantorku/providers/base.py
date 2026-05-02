"""
BaseProvider — Abstract base for all LLM providers.

All providers must implement:
- complete(): Single chat completion (returns str, backwards compatible)
- complete_with_usage(): Returns ProviderResponse with token counts

New providers should implement complete_with_usage() natively.
The default complete() wraps complete_with_usage() for backwards compat.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, AsyncIterator

from kantorku.provider_response import ProviderResponse


class BaseProvider(ABC):
    """
    Abstract base class for LLM providers.

    Each provider wraps a specific LLM API (Anthropic, Google, etc.)
    and normalizes the interface to a common format.

    Providers should implement complete_with_usage() to return
    structured responses with token counts. The complete() method
    is kept for backwards compatibility.
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

    async def complete_with_usage(
        self,
        model: str,
        messages: list[dict[str, str]],
        **kwargs: Any,
    ) -> ProviderResponse:
        """
        Send a chat completion request and return structured response.

        Default implementation wraps complete() — providers should
        override this to return actual token counts from the API.

        Args:
            model: Model name (without provider prefix)
            messages: Chat messages in standard format
            **kwargs: Additional parameters

        Returns:
            ProviderResponse with content, token counts, and metadata
        """
        import time

        start = time.monotonic()
        content = await self.complete(model=model, messages=messages, **kwargs)
        latency_ms = (time.monotonic() - start) * 1000

        return ProviderResponse(
            content=content,
            model=model,
            provider_name=self.name,
            latency_ms=latency_ms,
        )

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
