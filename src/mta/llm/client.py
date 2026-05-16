"""LLMClient facade: resolves logical role → (provider, model) → response.

Provider inference rule: model string starting with "claude" → AnthropicClient,
any other prefix → OpenRouterClient.

Valid roles: "author", "vision", "heal". Unknown role raises ConfigError.
"""

from typing import Any

from mta.config import Config, ConfigError
from mta.llm.anthropic_client import AnthropicClient, LLMResponse
from mta.llm.openrouter_client import OpenRouterClient

_VALID_ROLES = frozenset({"author", "vision", "heal"})


class LLMClient:
    def __init__(
        self,
        config: Config,
        anthropic_client: AnthropicClient | None = None,
        openrouter_client: OpenRouterClient | None = None,
    ) -> None:
        self._config = config
        self._anthropic = anthropic_client
        self._openrouter = openrouter_client

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def complete(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        role: str,
    ) -> LLMResponse:
        if role not in _VALID_ROLES:
            raise ConfigError(f"unknown role: {role!r}")

        model = self._resolve_model(role)
        provider = self._provider_for(model)
        return provider.complete(messages, tools, model)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve_model(self, role: str) -> str:
        override: str | None = getattr(self._config.model_roles, role)
        return override if override is not None else self._config.default_model

    def _provider_for(self, model: str) -> AnthropicClient | OpenRouterClient:
        if model.startswith("claude"):
            return self._anthropic_client()
        return self._openrouter_client()

    def _anthropic_client(self) -> AnthropicClient:
        if self._anthropic is None:
            if not self._config.anthropic_api_key:
                raise ConfigError(
                    "ANTHROPIC_API_KEY is required for Claude models"
                )
            self._anthropic = AnthropicClient(self._config.anthropic_api_key)
        return self._anthropic

    def _openrouter_client(self) -> OpenRouterClient:
        if self._openrouter is None:
            if not self._config.openrouter_api_key:
                raise ConfigError(
                    "OPENROUTER_API_KEY is required for non-Claude models"
                )
            self._openrouter = OpenRouterClient(self._config.openrouter_api_key)
        return self._openrouter
