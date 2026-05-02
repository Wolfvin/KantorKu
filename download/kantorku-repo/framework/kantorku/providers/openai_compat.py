"""
OpenAI-compatible provider — MiniMax, DeepSeek, xAI, and any OpenAI-compatible API.

Uses the OpenAI Python client for compatibility with any API
that follows the OpenAI chat completions format.
"""

from __future__ import annotations

import time
from typing import Any, AsyncIterator

from kantorku.providers.base import BaseProvider
from kantorku.provider_response import ProviderResponse


class OpenAICompatProvider(BaseProvider):
    """
    OpenAI-compatible provider.

    Works with any API that follows the OpenAI chat completions format.
    Used for: OpenAI, xAI, and any custom OpenAI-compatible endpoint.

    Requires: pip install openai
    """

    def __init__(
        self,
        provider_name: str = "openai",
        api_key: str = "",
        base_url: str | None = None,
        **kwargs: Any,
    ) -> None:
        self._provider_name = provider_name
        self.api_key = api_key
        self.base_url = base_url
        self._client: Any = None

    def _get_client(self) -> Any:
        if self._client is None:
            try:
                from openai import AsyncOpenAI
                kwargs: dict[str, Any] = {"api_key": self.api_key}
                if self.base_url:
                    kwargs["base_url"] = self.base_url
                self._client = AsyncOpenAI(**kwargs)
            except ImportError:
                raise ImportError(
                    f"{self._provider_name} provider requires 'openai' package. "
                    f"Install with: pip install kantorku[{self._provider_name}]"
                )
        return self._client

    async def complete(
        self,
        model: str,
        messages: list[dict[str, str]],
        **kwargs: Any,
    ) -> str:
        response = await self.complete_with_usage(model=model, messages=messages, **kwargs)
        return response.content

    async def complete_with_usage(
        self,
        model: str,
        messages: list[dict[str, str]],
        **kwargs: Any,
    ) -> ProviderResponse:
        client = self._get_client()

        start = time.monotonic()
        response = await client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=kwargs.get("temperature", 0.7),
            max_tokens=kwargs.get("max_tokens", 8192),
        )
        latency_ms = (time.monotonic() - start) * 1000

        return ProviderResponse.from_openai_format(
            response, provider_name=self._provider_name, latency_ms=latency_ms,
        )

    async def complete_stream(
        self,
        model: str,
        messages: list[dict[str, str]],
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        client = self._get_client()
        stream = await client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=kwargs.get("temperature", 0.7),
            max_tokens=kwargs.get("max_tokens", 8192),
            stream=True,
        )
        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    @property
    def name(self) -> str:
        return self._provider_name


# Backwards-compatible aliases
class MiniMaxProvider(OpenAICompatProvider):
    """MiniMax provider (OpenAI-compatible). Uses OpenAI client with custom base_url."""

    BASE_URL = "https://api.minimax.chat/v1"

    def __init__(self, api_key: str = "", base_url: str | None = None, **kwargs: Any) -> None:
        super().__init__(
            provider_name="minimax",
            api_key=api_key,
            base_url=base_url or self.BASE_URL,
            **kwargs,
        )


class DeepSeekProvider(OpenAICompatProvider):
    """
    DeepSeek provider (OpenAI-compatible).

    Uses OpenAI client with DeepSeek base_url.
    Supports context caching for repeated prefixes.
    """

    BASE_URL = "https://api.deepseek.com/v1"

    def __init__(self, api_key: str = "", base_url: str | None = None, **kwargs: Any) -> None:
        super().__init__(
            provider_name="deepseek",
            api_key=api_key,
            base_url=base_url or self.BASE_URL,
            **kwargs,
        )

    async def complete_with_usage(
        self,
        model: str,
        messages: list[dict[str, str]],
        **kwargs: Any,
    ) -> ProviderResponse:
        client = self._get_client()

        # DeepSeek supports context caching via prefix matching
        extra: dict[str, Any] = {}
        if kwargs.get("enable_cache"):
            extra["enable_search"] = True

        start = time.monotonic()
        response = await client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=kwargs.get("temperature", 0.7),
            max_tokens=kwargs.get("max_tokens", 8192),
            **extra,
        )
        latency_ms = (time.monotonic() - start) * 1000

        return ProviderResponse.from_openai_format(
            response, provider_name="deepseek", latency_ms=latency_ms,
        )
