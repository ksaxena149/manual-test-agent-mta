"""Tests for LLMClient facade (issue 006)."""

from typing import Any
from unittest.mock import MagicMock

import pytest

from mta.config import Config, ConfigError, ModelRoles
from mta.llm import LLMClient, LLMResponse


def _config(
    default_model: str = "claude-haiku-4-5",
    author: str | None = None,
    vision: str | None = None,
    heal: str | None = None,
    anthropic_api_key: str | None = "ant-key",
    openrouter_api_key: str | None = "or-key",
) -> Config:
    return Config(
        default_model=default_model,
        model_roles=ModelRoles(author=author, vision=vision, heal=heal),
        anthropic_api_key=anthropic_api_key,
        openrouter_api_key=openrouter_api_key,
    )


def _fake_response(text: str = "ok") -> LLMResponse:
    return LLMResponse(kind="text", text=text)


# ---------------------------------------------------------------------------
# RED 1: unknown role → ConfigError
# ---------------------------------------------------------------------------


def test_unknown_role_raises():
    client = LLMClient(_config())
    with pytest.raises(ConfigError, match="unknown role"):
        client.complete([], [], role="admin")


# ---------------------------------------------------------------------------
# RED 2: default fallback — no role override uses default_model
# ---------------------------------------------------------------------------


def test_default_fallback_uses_default_model():
    fake = MagicMock(return_value=_fake_response())
    ant = MagicMock()
    ant.complete = fake

    cfg = _config(default_model="claude-haiku-4-5")
    client = LLMClient(cfg, anthropic_client=ant)

    msgs: list[dict[str, Any]] = [{"role": "user", "content": "hi"}]
    client.complete(msgs, [], role="author")

    fake.assert_called_once_with(msgs, [], "claude-haiku-4-5")


# ---------------------------------------------------------------------------
# RED 3: author role override used when present
# ---------------------------------------------------------------------------


def test_author_role_override():
    fake = MagicMock(return_value=_fake_response())
    ant = MagicMock()
    ant.complete = fake

    cfg = _config(default_model="claude-haiku-4-5", author="claude-sonnet-4-6")
    client = LLMClient(cfg, anthropic_client=ant)

    client.complete([], [], role="author")

    _, _, model = fake.call_args.args
    assert model == "claude-sonnet-4-6"


# ---------------------------------------------------------------------------
# RED 4: vision role override
# ---------------------------------------------------------------------------


def test_vision_role_override():
    fake = MagicMock(return_value=_fake_response())
    ant = MagicMock()
    ant.complete = fake

    cfg = _config(default_model="claude-haiku-4-5", vision="claude-opus-4-7")
    client = LLMClient(cfg, anthropic_client=ant)

    client.complete([], [], role="vision")

    _, _, model = fake.call_args.args
    assert model == "claude-opus-4-7"


# ---------------------------------------------------------------------------
# RED 5: heal role override
# ---------------------------------------------------------------------------


def test_heal_role_override():
    fake = MagicMock(return_value=_fake_response())
    ant = MagicMock()
    ant.complete = fake

    cfg = _config(default_model="claude-haiku-4-5", heal="claude-sonnet-4-6")
    client = LLMClient(cfg, anthropic_client=ant)

    client.complete([], [], role="heal")

    _, _, model = fake.call_args.args
    assert model == "claude-sonnet-4-6"


# ---------------------------------------------------------------------------
# RED 6: claude- prefix → AnthropicClient
# ---------------------------------------------------------------------------


def test_claude_prefix_routes_to_anthropic():
    ant_fake = MagicMock(return_value=_fake_response())
    or_fake = MagicMock(return_value=_fake_response())
    ant = MagicMock()
    ant.complete = ant_fake
    ort = MagicMock()
    ort.complete = or_fake

    cfg = _config(default_model="claude-haiku-4-5")
    client = LLMClient(cfg, anthropic_client=ant, openrouter_client=ort)
    client.complete([], [], role="author")

    ant_fake.assert_called_once()
    or_fake.assert_not_called()


# ---------------------------------------------------------------------------
# RED 7: non-claude model → OpenRouterClient
# ---------------------------------------------------------------------------


def test_non_claude_model_routes_to_openrouter():
    ant_fake = MagicMock(return_value=_fake_response())
    or_fake = MagicMock(return_value=_fake_response())
    ant = MagicMock()
    ant.complete = ant_fake
    ort = MagicMock()
    ort.complete = or_fake

    cfg = _config(default_model="qwen/qwen2.5-vl-72b-instruct")
    client = LLMClient(cfg, anthropic_client=ant, openrouter_client=ort)
    client.complete([], [], role="author")

    or_fake.assert_called_once()
    ant_fake.assert_not_called()


# ---------------------------------------------------------------------------
# RED 8: missing Anthropic key → ConfigError
# ---------------------------------------------------------------------------


def test_missing_anthropic_key_raises():
    cfg = _config(default_model="claude-haiku-4-5", anthropic_api_key=None)
    client = LLMClient(cfg)
    with pytest.raises(ConfigError, match="ANTHROPIC_API_KEY"):
        client.complete([], [], role="author")


# ---------------------------------------------------------------------------
# RED 9: missing OpenRouter key → ConfigError
# ---------------------------------------------------------------------------


def test_missing_openrouter_key_raises():
    cfg = _config(default_model="qwen/qwen2.5-vl-72b-instruct", openrouter_api_key=None)
    client = LLMClient(cfg)
    with pytest.raises(ConfigError, match="OPENROUTER_API_KEY"):
        client.complete([], [], role="author")
