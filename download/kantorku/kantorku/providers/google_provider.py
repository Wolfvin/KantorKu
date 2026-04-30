"""Google provider — Gemini models via Google GenAI API."""

from __future__ import annotations

from typing import Any, AsyncIterator

from kantorku.providers.base import BaseProvider


class GoogleProvider(BaseProvider):
    """
    Google Gemini provider.

    Requires: pip install kantorku[google]
    """

    def __init__(self, api_key: str = "", **kwargs: Any) -> None:
        self.api_key = api_key
        self._client: Any = None

    def _get_client(self) -> Any:
        if self._client is None:
            try:
                from google import genai
                self._client = genai.Client(api_key=self.api_key)
            except ImportError:
                raise ImportError(
                    "Google provider requires 'google-genai' package. "
                    "Install with: pip install kantorku[google]"
                )
        return self._client

    async def complete(
        self,
        model: str,
        messages: list[dict[str, str]],
        **kwargs: Any,
    ) -> str:
        client = self._get_client()

        # Convert messages to Gemini format
        contents = []
        system_instruction = None
        for msg in messages:
            if msg["role"] == "system":
                system_instruction = msg["content"]
            elif msg["role"] == "user":
                contents.append({"role": "user", "parts": [{"text": msg["content"]}]})
            elif msg["role"] == "assistant":
                contents.append({"role": "model", "parts": [{"text": msg["content"]}]})

        config: dict[str, Any] = {}
        if system_instruction:
            config["system_instruction"] = system_instruction
        if "temperature" in kwargs:
            config["temperature"] = kwargs["temperature"]
        if "max_tokens" in kwargs:
            config["max_output_tokens"] = kwargs["max_tokens"]

        response = await client.aio.models.generate_content(
            model=model,
            contents=contents,
            config=config if config else None,
        )
        return response.text

    async def complete_stream(
        self,
        model: str,
        messages: list[dict[str, str]],
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        client = self._get_client()

        contents = []
        system_instruction = None
        for msg in messages:
            if msg["role"] == "system":
                system_instruction = msg["content"]
            elif msg["role"] == "user":
                contents.append({"role": "user", "parts": [{"text": msg["content"]}]})
            elif msg["role"] == "assistant":
                contents.append({"role": "model", "parts": [{"text": msg["content"]}]})

        config: dict[str, Any] = {}
        if system_instruction:
            config["system_instruction"] = system_instruction

        response = await client.aio.models.generate_content_stream(
            model=model,
            contents=contents,
            config=config if config else None,
        )
        async for chunk in response:
            if chunk.text:
                yield chunk.text

    @property
    def name(self) -> str:
        return "google"
