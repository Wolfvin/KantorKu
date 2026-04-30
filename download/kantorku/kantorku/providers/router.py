"""
Provider Router — Route LLM calls to the right provider.

Model format: "provider/model-name"
Examples: "anthropic/claude-opus-4-6", "minimax/minimax-m2-7", "deepseek/deepseek-v3-2"

The router parses the provider prefix and dispatches to the appropriate provider.
"""

from __future__ import annotations

from typing import Any

from kantorku.providers.base import BaseProvider
from kantorku.providers.anthropic_provider import AnthropicProvider
from kantorku.providers.google_provider import GoogleProvider
from kantorku.providers.minimax_provider import MiniMaxProvider
from kantorku.providers.deepseek_provider import DeepSeekProvider
from kantorku.providers.ollama_provider import OllamaProvider


class ProviderRouter:
    """
    Route LLM calls to the correct provider based on model prefix.

    Usage:
        router = ProviderRouter()
        router.configure("anthropic", api_key="sk-...")
        router.configure("deepseek", api_key="sk-...")

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
        """
        import os

        for name, config in providers_config.items():
            resolved = {}
            for k, v in config.items():
                if isinstance(v, str) and v.startswith("${") and v.endswith("}"):
                    env_var = v[2:-1]
                    resolved[k] = os.environ.get(env_var, "")
                else:
                    resolved[k] = v
            self.configure(name, **resolved)

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

        Args:
            model: Full model identifier (e.g. "anthropic/claude-opus-4-6")
            messages: Chat messages in OpenAI format
            **kwargs: Additional parameters (temperature, max_tokens, etc.)

        Returns:
            The assistant's response text
        """
        provider_name, model_name = self._parse_model(model)
        provider = self._get_provider(provider_name)
        return await provider.complete(model=model_name, messages=messages, **kwargs)

    async def complete_stream(
        self,
        model: str,
        messages: list[dict[str, str]],
        **kwargs: Any,
    ):
        """
        Stream a chat completion response.

        Yields chunks of the response as they arrive.
        """
        provider_name, model_name = self._parse_model(model)
        provider = self._get_provider(provider_name)
        async for chunk in provider.complete_stream(model=model_name, messages=messages, **kwargs):
            yield chunk

    @property
    def configured_providers(self) -> list[str]:
        return list(self._providers.keys())
