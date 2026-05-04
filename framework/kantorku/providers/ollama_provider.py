"""Ollama provider — Local LLM via Ollama API."""

from __future__ import annotations

import time
from typing import Any, AsyncIterator

from kantorku.providers.base import BaseProvider
from kantorku.provider_response import ProviderResponse


class OllamaProvider(BaseProvider):
    """
    Ollama provider for local LLM inference.

    Uses OpenAI-compatible endpoint provided by Ollama.
    Requires: pip install kantorku[ollama]
    """

    DEFAULT_BASE_URL = "http://localhost:11434/v1"

    def __init__(self, base_url: str = "", api_key: str = "ollama", **kwargs: Any) -> None:
        self.base_url = base_url or self.DEFAULT_BASE_URL
        self.api_key = api_key
        self._client: Any = None

    def _get_client(self) -> Any:
        if self._client is None:
            try:
                from openai import AsyncOpenAI
                self._client = AsyncOpenAI(
                    api_key=self.api_key or "ollama",
                    base_url=self.base_url,
                )
            except ImportError:
                raise ImportError(
                    "Ollama provider requires 'openai' package. "
                    "Install with: pip install kantorku[ollama]"
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
            response, provider_name="ollama", latency_ms=latency_ms,
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
        return "ollama"
