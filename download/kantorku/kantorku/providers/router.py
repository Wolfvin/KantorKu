"""
Provider Router — Route LLM calls to the right provider.

Model format: "provider/model-name"
Examples: "anthropic/claude-opus-4-6", "minimax/minimax-m2-7", "deepseek/deepseek-v3-2"

The router parses the provider prefix and dispatches to the appropriate provider.
Includes rate limiting and fallback support.
"""

from __future__ import annotations

import logging
from typing import Any

from kantorku.providers.base import BaseProvider
from kantorku.providers.anthropic_provider import AnthropicProvider
from kantorku.providers.google_provider import GoogleProvider
from kantorku.providers.minimax_provider import MiniMaxProvider
from kantorku.providers.deepseek_provider import DeepSeekProvider
from kantorku.providers.ollama_provider import OllamaProvider
from kantorku.providers.rate_limiter import RateLimiter

logger = logging.getLogger("kantorku.providers")


class ProviderRouter:
    """
    Route LLM calls to the correct provider based on model prefix.

    Features:
    - Rate limiting per provider (token bucket + semaphore)
    - Provider fallback on failure
    - Streaming support

    Usage:
        router = ProviderRouter()
        router.configure("anthropic", api_key="sk-...")
        router.configure("deepseek", api_key="sk-...")

        # Configure rate limits
        router.configure_rate_limit("anthropic", rps=5.0, max_concurrent=3)

        # Configure fallbacks
        router.configure_fallback("anthropic", ["deepseek", "ollama"])

        response = await router.complete(
            model="anthropic/claude-opus-4-6",
            messages=[{"role": "user", "content": "Hello"}],
        )
    """

    PROVIDER_MAP: dict[str, type[BaseProvider]] = {
        "anthropic": AnthropicProvider,
        "google": GoogleProvider,
        "minimax": MiniMaxProvider,
        "deepseek": DeepSeekProvider,
        "meta": DeepSeekProvider,  # Meta uses OpenAI-compatible via proxy
        "ollama": OllamaProvider,
    }

    def __init__(self) -> None:
        self._providers: dict[str, BaseProvider] = {}
        self._rate_limiter = RateLimiter()
        self._fallbacks: dict[str, list[str]] = {}

    def configure(self, provider_name: str, **kwargs: Any) -> None:
        """
        Configure a provider with credentials and settings.

        Args:
            provider_name: One of "anthropic", "google", "minimax", "deepseek", "ollama"
            **kwargs: Provider-specific config (api_key, base_url, etc.)
        """
        provider_name = provider_name.lower()
        cls = self.PROVIDER_MAP.get(provider_name)
        if cls is None:
            raise ValueError(
                f"Unknown provider '{provider_name}'. "
                f"Available: {list(self.PROVIDER_MAP.keys())}"
            )
        self._providers[provider_name] = cls(**kwargs)

    def configure_from_dict(self, providers_config: dict[str, dict[str, Any]]) -> None:
        """
        Configure multiple providers from a dict (e.g. from TOML [providers.*]).

        Handles environment variable expansion for api_key.
        Also reads rate_limit and fallback config if present.
        """
        import os

        for name, config in providers_config.items():
            # Extract non-provider keys
            provider_kwargs = {}
            rate_limit_kwargs = {}
            fallback_list = None

            for k, v in config.items():
                if k == "rate_limit":
                    rate_limit_kwargs = v if isinstance(v, dict) else {}
                elif k == "fallback":
                    fallback_list = v if isinstance(v, list) else None
                elif isinstance(v, str) and v.startswith("${") and v.endswith("}"):
                    env_var = v[2:-1]
                    provider_kwargs[k] = os.environ.get(env_var, "")
                else:
                    provider_kwargs[k] = v

            self.configure(name, **provider_kwargs)

            if rate_limit_kwargs:
                self.configure_rate_limit(name, **rate_limit_kwargs)

            if fallback_list:
                self.configure_fallback(name, fallback_list)

    def configure_rate_limit(
        self,
        provider: str,
        rps: float = 0.0,
        max_concurrent: int = 0,
        burst: int = 5,
    ) -> None:
        """
        Configure rate limits for a provider.

        Args:
            provider: Provider name
            rps: Maximum requests per second (0 = unlimited)
            max_concurrent: Maximum concurrent requests (0 = unlimited)
            burst: Token bucket burst size
        """
        self._rate_limiter.configure(
            provider, rps=rps, max_concurrent=max_concurrent, burst=burst
        )
        logger.info(f"Rate limit configured for {provider}: rps={rps}, max_concurrent={max_concurrent}")

    def configure_fallback(self, provider: str, fallbacks: list[str]) -> None:
        """
        Configure fallback providers to try if the primary fails.

        Args:
            provider: Primary provider name
            fallbacks: List of fallback provider names to try in order
        """
        self._fallbacks[provider] = fallbacks
        logger.info(f"Fallback configured for {provider}: {fallbacks}")

    def _parse_model(self, model: str) -> tuple[str, str]:
        """Parse 'provider/model-name' into (provider, model_name)."""
        if "/" not in model:
            raise ValueError(
                f"Model must be in 'provider/model-name' format, got: '{model}'"
            )
        provider, model_name = model.split("/", 1)
        return provider.lower(), model_name

    def _get_provider(self, provider_name: str) -> BaseProvider:
        """Get a configured provider, raising if not configured."""
        if provider_name not in self._providers:
            configured = list(self._providers.keys())
            raise ValueError(
                f"Provider '{provider_name}' not configured. "
                f"Configured: {configured}. "
                f"Call router.configure('{provider_name}', ...) first."
            )
        return self._providers[provider_name]

    async def complete(
        self,
        model: str,
        messages: list[dict[str, str]],
        **kwargs: Any,
    ) -> str:
        """
        Send a chat completion request to the appropriate provider.
        Includes rate limiting and fallback on failure.

        Args:
            model: Full model identifier (e.g. "anthropic/claude-opus-4-6")
            messages: Chat messages in OpenAI format
            **kwargs: Additional parameters (temperature, max_tokens, etc.)

        Returns:
            The assistant's response text
        """
        provider_name, model_name = self._parse_model(model)

        # Apply rate limiting
        async with self._rate_limiter.limit(provider_name):
            try:
                provider = self._get_provider(provider_name)
                return await provider.complete(model=model_name, messages=messages, **kwargs)
            except Exception as e:
                logger.warning(f"Provider {provider_name} failed: {e}. Trying fallbacks...")
                return await self._try_fallbacks(
                    primary_model=model_name,
                    messages=messages,
                    failed_provider=provider_name,
                    **kwargs,
                )

    async def _try_fallbacks(
        self,
        primary_model: str,
        messages: list[dict[str, str]],
        failed_provider: str,
        **kwargs: Any,
    ) -> str:
        """Try fallback providers when the primary fails."""
        fallbacks = self._fallbacks.get(failed_provider, [])

        for fallback_name in fallbacks:
            if fallback_name not in self._providers:
                logger.debug(f"Fallback {fallback_name} not configured, skipping")
                continue

            try:
                async with self._rate_limiter.limit(fallback_name):
                    provider = self._get_provider(fallback_name)
                    # Use a model name appropriate for the fallback provider
                    fallback_model = self._guess_fallback_model(fallback_name, primary_model)
                    logger.info(f"Trying fallback: {fallback_name}/{fallback_model}")
                    return await provider.complete(
                        model=fallback_model, messages=messages, **kwargs
                    )
            except Exception as fallback_err:
                logger.warning(f"Fallback {fallback_name} also failed: {fallback_err}")
                continue

        # All fallbacks exhausted
        raise RuntimeError(
            f"Provider {failed_provider} and all fallbacks failed. "
            f"Fallbacks tried: {fallbacks}"
        )

    def _guess_fallback_model(self, fallback_provider: str, original_model: str) -> str:
        """
        Guess an appropriate model name for a fallback provider.
        Falls back to a reasonable default model for the provider.
        """
        # Provider-specific default models
        defaults = {
            "anthropic": "claude-sonnet-4-20250514",
            "google": "gemini-2.0-flash",
            "deepseek": "deepseek-chat",
            "minimax": "minimax-m2-7",
            "ollama": "llama3",
        }
        return defaults.get(fallback_provider, original_model)

    async def complete_stream(
        self,
        model: str,
        messages: list[dict[str, str]],
        **kwargs: Any,
    ):
        """
        Stream a chat completion response.
        Includes rate limiting.

        Yields chunks of the response as they arrive.
        """
        provider_name, model_name = self._parse_model(model)

        async with self._rate_limiter.limit(provider_name):
            provider = self._get_provider(provider_name)
            async for chunk in provider.complete_stream(model=model_name, messages=messages, **kwargs):
                yield chunk

    @property
    def configured_providers(self) -> list[str]:
        return list(self._providers.keys())

    def get_rate_limit_status(self) -> dict[str, Any]:
        """Get rate limit status for all configured providers."""
        return self._rate_limiter.get_status()
