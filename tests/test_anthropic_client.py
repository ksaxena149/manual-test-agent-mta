"""Tests for AnthropicClient — mocked SDK, no real API calls."""

from unittest.mock import MagicMock, patch

import anthropic as _anthropic
import pytest

from mta.llm import AnthropicClient, LLMError

# ---------------------------------------------------------------------------
# Cycle 1: constructor
# ---------------------------------------------------------------------------


def test_constructor_accepts_api_key() -> None:
    with patch("mta.llm.anthropic_client.anthropic.Anthropic") as mock_cls:
        client = AnthropicClient(api_key="sk-test")
        mock_cls.assert_called_once_with(api_key="sk-test")
        assert client is not None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_client() -> tuple[AnthropicClient, MagicMock]:
    """Return (client, mock_messages_create) with patched SDK."""
    with patch("mta.llm.anthropic_client.anthropic.Anthropic") as mock_cls:
        mock_create = MagicMock()
        mock_cls.return_value.messages.create = mock_create
        client = AnthropicClient(api_key="sk-test")
    return client, mock_create


# ---------------------------------------------------------------------------
# Cycle 2: text response
# ---------------------------------------------------------------------------


def test_complete_returns_text_response() -> None:
    client, mock_create = _make_client()

    text_block = MagicMock()
    text_block.type = "text"
    text_block.text = "Hello world"

    mock_create.return_value = MagicMock(content=[text_block])

    result = client.complete(
        messages=[{"role": "user", "content": "hi"}],
        tools=[],
        model="claude-haiku-4-5-20251001",
    )

    assert result.kind == "text"
    assert result.text == "Hello world"
    assert result.tool_name is None
    assert result.tool_args is None


# ---------------------------------------------------------------------------
# Cycle 3: tool-use response
# ---------------------------------------------------------------------------


def test_complete_returns_tool_use_response() -> None:
    client, mock_create = _make_client()

    tool_block = MagicMock()
    tool_block.type = "tool_use"
    tool_block.name = "click"
    tool_block.input = {"selector": "#submit"}

    mock_create.return_value = MagicMock(content=[tool_block])

    result = client.complete(
        messages=[{"role": "user", "content": "click submit"}],
        tools=[{"name": "click", "description": "click", "input_schema": {}}],
        model="claude-sonnet-4-6",
    )

    assert result.kind == "tool_use"
    assert result.tool_name == "click"
    assert result.tool_args == {"selector": "#submit"}
    assert result.text is None


def test_tool_use_block_wins_over_text_block() -> None:
    """First tool_use block wins even when text blocks are also present."""
    client, mock_create = _make_client()

    text_block = MagicMock()
    text_block.type = "text"
    text_block.text = "I will click"

    tool_block = MagicMock()
    tool_block.type = "tool_use"
    tool_block.name = "click"
    tool_block.input = {"selector": "button"}

    mock_create.return_value = MagicMock(content=[text_block, tool_block])

    result = client.complete(
        messages=[{"role": "user", "content": "click the button"}],
        tools=[],
        model="claude-sonnet-4-6",
    )

    assert result.kind == "tool_use"
    assert result.tool_name == "click"


# ---------------------------------------------------------------------------
# Cycle 4: SDK errors wrapped in LLMError
# ---------------------------------------------------------------------------


def test_sdk_error_wrapped_in_llm_error() -> None:
    client, mock_create = _make_client()

    mock_response = MagicMock()
    mock_response.status_code = 401
    mock_response.headers = {}
    sdk_exc = _anthropic.AuthenticationError(
        message="invalid api key",
        response=mock_response,
        body=None,
    )
    mock_create.side_effect = sdk_exc

    with pytest.raises(LLMError, match="Anthropic API error"):
        client.complete(
            messages=[{"role": "user", "content": "hi"}],
            tools=[],
            model="claude-sonnet-4-6",
        )


def test_llm_error_chains_original_exception() -> None:
    client, mock_create = _make_client()

    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.headers = {}
    sdk_exc = _anthropic.InternalServerError(
        message="server error",
        response=mock_response,
        body=None,
    )
    mock_create.side_effect = sdk_exc

    with pytest.raises(LLMError) as exc_info:
        client.complete(
            messages=[{"role": "user", "content": "hi"}],
            tools=[],
            model="claude-sonnet-4-6",
        )
    assert exc_info.value.__cause__ is sdk_exc
