"""Ollama provider — Local LLM via Ollama API."""

from __future__ import annotations

from typing import Any, AsyncIterator

from kantorku.providers.base import BaseProvider


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
        return "ollama"
