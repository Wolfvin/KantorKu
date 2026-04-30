"""
OpenAI-compatible provider — MiniMax, DeepSeek, and any OpenAI-compatible API.

Uses the OpenAI Python client for compatibility with any API
that follows the OpenAI chat completions format.
"""

from __future__ import annotations

from typing import Any, AsyncIterator

from kantorku.providers.base import BaseProvider


class MiniMaxProvider(BaseProvider):
    """
    MiniMax provider (OpenAI-compatible).

    Uses OpenAI client with custom base_url.
    Requires: pip install kantorku[minimax]
    """

    BASE_URL = "https://api.minimax.chat/v1"

    def __init__(self, api_key: str = "", base_url: str | None = None, **kwargs: Any) -> None:
        self.api_key = api_key
        self.base_url = base_url or self.BASE_URL
        self._client: Any = None

    def _get_client(self) -> Any:
        if self._client is None:
            try:
                from openai import AsyncOpenAI
                self._client = AsyncOpenAI(
                    api_key=self.api_key,
                    base_url=self.base_url,
                )
            except ImportError:
                raise ImportError(
                    "MiniMax provider requires 'openai' package. "
                    "Install with: pip install kantorku[minimax]"
                )
        return self._client

    async def complete(
        self,
        model: str,
        messages: list[dict[str, str]],
        **kwargs: Any,
    ) -> str:
        client = self._get_client()
        response = await client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=kwargs.get("temperature", 0.7),
            max_tokens=kwargs.get("max_tokens", 8192),
        )
        return response.choices[0].message.content or ""

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
        return "minimax"


class DeepSeekProvider(BaseProvider):
    """
    DeepSeek provider (OpenAI-compatible).

    Uses OpenAI client with DeepSeek base_url.
    Supports context caching for repeated prefixes.
    Requires: pip install kantorku[deepseek]
    """

    BASE_URL = "https://api.deepseek.com/v1"

    def __init__(self, api_key: str = "", base_url: str | None = None, **kwargs: Any) -> None:
        self.api_key = api_key
        self.base_url = base_url or self.BASE_URL
        self._client: Any = None

    def _get_client(self) -> Any:
        if self._client is None:
            try:
                from openai import AsyncOpenAI
                self._client = AsyncOpenAI(
                    api_key=self.api_key,
                    base_url=self.base_url,
                )
            except ImportError:
                raise ImportError(
                    "DeepSeek provider requires 'openai' package. "
                    "Install with: pip install kantorku[deepseek]"
                )
        return self._client

    async def complete(
        self,
        model: str,
        messages: list[dict[str, str]],
        **kwargs: Any,
    ) -> str:
        client = self._get_client()

        # DeepSeek supports context caching via prefix matching
        extra: dict[str, Any] = {}
        if kwargs.get("enable_cache"):
            extra["enable_search"] = True

        response = await client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=kwargs.get("temperature", 0.7),
            max_tokens=kwargs.get("max_tokens", 8192),
            **extra,
        )
        return response.choices[0].message.content or ""

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
        return "deepseek"
