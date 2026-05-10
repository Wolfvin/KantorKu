"""
ProviderResponse — Structured response from LLM providers.

Every provider call returns a ProviderResponse with:
- content: The text response
- model: Actual model used (may differ from requested)
- prompt_tokens / completion_tokens: Token usage
- latency_ms: Round-trip time in milliseconds
- cached: Whether this response was served from cache
- provider_name: Which provider served the response
- raw_response: Original API response (for provider-specific data)

This enables cost tracking, metrics, and observability
without scraping string responses.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ProviderResponse:
    """
    Structured response from an LLM provider call.

    All providers should return this instead of bare strings.
    The Router, CostTracker, LLMCache, and Metrics all depend on it.

    Attributes:
        content: The assistant's response text
        model: The actual model name used (may differ from requested)
        provider_name: Which provider served this response
        prompt_tokens: Number of tokens in the prompt
        completion_tokens: Number of tokens in the completion
        total_tokens: prompt_tokens + completion_tokens
        latency_ms: Round-trip time in milliseconds
        cached: Whether this was served from cache
        finish_reason: Why the model stopped generating (stop, length, etc.)
        raw_response: Original API response object (provider-specific)
    """

    content: str = ""
    model: str = ""
    provider_name: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    latency_ms: float = 0.0
    cached: bool = False
    finish_reason: str = ""
    raw_response: Any = None

    def __post_init__(self) -> None:
        if not self.total_tokens and (self.prompt_tokens or self.completion_tokens):
            self.total_tokens = self.prompt_tokens + self.completion_tokens

    @property
    def is_empty(self) -> bool:
        """Check if the response content is empty."""
        return not self.content

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict for logging/storage."""
        return {
            "content": self.content,
            "model": self.model,
            "provider_name": self.provider_name,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "latency_ms": self.latency_ms,
            "cached": self.cached,
            "finish_reason": self.finish_reason,
        }

    @classmethod
    def from_openai_format(cls, response: Any, provider_name: str = "", latency_ms: float = 0.0) -> ProviderResponse:
        """
        Create a ProviderResponse from an OpenAI-compatible API response.

        Works with OpenAI, DeepSeek, MiniMax, xAI, and any
        provider that follows the OpenAI chat completions format.

        Args:
            response: The raw response from openai.AsyncOpenAI.chat.completions.create
            provider_name: Name of the provider for tracking
            latency_ms: Measured latency in milliseconds
        """
        content = ""
        finish_reason = ""
        model = ""
        prompt_tokens = 0
        completion_tokens = 0
        total_tokens = 0

        try:
            if response.choices:
                choice = response.choices[0]
                content = choice.message.content or ""
                finish_reason = choice.finish_reason or ""

            model = getattr(response, "model", "")

            if hasattr(response, "usage") and response.usage:
                prompt_tokens = getattr(response.usage, "prompt_tokens", 0) or 0
                completion_tokens = getattr(response.usage, "completion_tokens", 0) or 0
                total_tokens = getattr(response.usage, "total_tokens", 0) or 0
        except (IndexError, AttributeError):
            pass

        return cls(
            content=content,
            model=model,
            provider_name=provider_name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens or (prompt_tokens + completion_tokens),
            latency_ms=latency_ms,
            finish_reason=finish_reason,
            raw_response=response,
        )

    @classmethod
    def from_anthropic_format(cls, response: Any, provider_name: str = "anthropic", latency_ms: float = 0.0) -> ProviderResponse:
        """
        Create a ProviderResponse from an Anthropic API response.

        Args:
            response: The raw response from anthropic.Anthropic.messages.create
            provider_name: Name of the provider
            latency_ms: Measured latency in milliseconds
        """
        content = ""
        model = ""
        prompt_tokens = 0
        completion_tokens = 0
        finish_reason = ""

        try:
            if response.content:
                # Anthropic returns list of content blocks
                text_parts = []
                for block in response.content:
                    if hasattr(block, "text"):
                        text_parts.append(block.text)
                content = "\n".join(text_parts)

            model = getattr(response, "model", "")

            if hasattr(response, "usage"):
                prompt_tokens = getattr(response.usage, "input_tokens", 0) or 0
                completion_tokens = getattr(response.usage, "output_tokens", 0) or 0

            finish_reason = getattr(response, "stop_reason", "") or ""
        except (IndexError, AttributeError):
            pass

        return cls(
            content=content,
            model=model,
            provider_name=provider_name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            latency_ms=latency_ms,
            finish_reason=finish_reason,
            raw_response=response,
        )

    @classmethod
    def from_google_format(cls, response: Any, provider_name: str = "google", latency_ms: float = 0.0) -> ProviderResponse:
        """
        Create a ProviderResponse from a Google Gemini API response.

        Args:
            response: The raw response from google.genai
            provider_name: Name of the provider
            latency_ms: Measured latency in milliseconds
        """
        content = ""
        model = ""
        prompt_tokens = 0
        completion_tokens = 0
        finish_reason = ""

        try:
            # Google SDK: response.text or response.candidates
            if hasattr(response, "text"):
                content = response.text or ""
            elif hasattr(response, "candidates") and response.candidates:
                parts = []
                for candidate in response.candidates:
                    if hasattr(candidate, "content") and hasattr(candidate.content, "parts"):
                        for part in candidate.content.parts:
                            if hasattr(part, "text"):
                                parts.append(part.text)
                content = "\n".join(parts)

            model = getattr(response, "model", "") or ""

            if hasattr(response, "usage_metadata"):
                um = response.usage_metadata
                prompt_tokens = getattr(um, "prompt_token_count", 0) or 0
                completion_tokens = getattr(um, "candidates_token_count", 0) or 0

            if hasattr(response, "candidates") and response.candidates:
                c = response.candidates[0]
                finish_reason = getattr(c, "finish_reason", "") or ""
                if hasattr(finish_reason, "name"):
                    finish_reason = finish_reason.name

        except (IndexError, AttributeError):
            pass

        return cls(
            content=content,
            model=model,
            provider_name=provider_name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            latency_ms=latency_ms,
            finish_reason=finish_reason,
            raw_response=response,
        )

    @classmethod
    def cached_response(cls, content: str, model: str = "", provider_name: str = "cache") -> ProviderResponse:
        """
        Create a ProviderResponse that represents a cache hit.

        Used by the LLMCache integration to return cached responses
        with correct metadata (cached=True, latency=0).
        """
        return cls(
            content=content,
            model=model,
            provider_name=provider_name,
            cached=True,
            latency_ms=0.0,
        )
