"""Anthropic provider — Claude models via Anthropic API."""

from __future__ import annotations

from typing import Any, AsyncIterator

from kantorku.providers.base import BaseProvider


class AnthropicProvider(BaseProvider):
    """
    Anthropic Claude provider.

    Requires: pip install kantorku[anthropic]
    """

    def __init__(self, api_key: str = "", **kwargs: Any) -> None:
        self.api_key = api_key
        self._client: Any = None

    def _get_client(self) -> Any:
        if self._client is None:
            try:
                import anthropic
                self._client = anthropic.AsyncAnthropic(api_key=self.api_key)
            except ImportError:
                raise ImportError(
                    "Anthropic provider requires 'anthropic' package. "
                    "Install with: pip install kantorku[anthropic]"
                )
        return self._client

    async def complete(
        self,
        model: str,
        messages: list[dict[str, str]],
        **kwargs: Any,
    ) -> str:
        client = self._get_client()

        # Extract system message from messages
        system = None
        user_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system = msg["content"]
            else:
                user_messages.append(msg)

        response = await client.messages.create(
            model=model,
            max_tokens=kwargs.get("max_tokens", 8192),
            system=system or "",
            messages=user_messages,
            temperature=kwargs.get("temperature", 0.7),
        )

        return response.content[0].text

    async def complete_stream(
        self,
        model: str,
        messages: list[dict[str, str]],
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        client = self._get_client()

        system = None
        user_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system = msg["content"]
            else:
                user_messages.append(msg)

        async with client.messages.stream(
            model=model,
            max_tokens=kwargs.get("max_tokens", 8192),
            system=system or "",
            messages=user_messages,
            temperature=kwargs.get("temperature", 0.7),
        ) as stream:
            async for text in stream.text_stream:
                yield text

    @property
    def name(self) -> str:
        return "anthropic"
