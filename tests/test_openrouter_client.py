"""Tests for OpenRouterClient — mocked httpx, no real network."""

import json
from unittest.mock import MagicMock, patch

import httpx
import pytest

from mta.llm import LLMError, OpenRouterClient

# ---------------------------------------------------------------------------
# Cycle 1: constructor
# ---------------------------------------------------------------------------


def test_constructor_stores_api_key_and_base_url() -> None:
    client = OpenRouterClient(api_key="sk-test")
    assert client._api_key == "sk-test"
    assert client._base_url == "https://openrouter.ai/api/v1"


def test_constructor_accepts_custom_base_url() -> None:
    client = OpenRouterClient(api_key="sk-test", base_url="http://localhost:8080/v1")
    assert client._base_url == "http://localhost:8080/v1"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_response(body: dict[str, object], status_code: int = 200) -> MagicMock:
    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = status_code
    mock_resp.json.return_value = body
    mock_resp.raise_for_status.side_effect = (
        None
        if status_code < 400
        else httpx.HTTPStatusError(
            f"HTTP {status_code}",
            request=MagicMock(),
            response=mock_resp,
        )
    )
    return mock_resp


def _text_body(content: str) -> dict[str, object]:
    return {
        "choices": [
            {"message": {"content": content, "tool_calls": None}}
        ]
    }


def _tool_body(name: str, args: dict[str, object]) -> dict[str, object]:
    return {
        "choices": [
            {
                "message": {
                    "content": None,
                    "tool_calls": [
                        {
                            "function": {
                                "name": name,
                                "arguments": json.dumps(args),
                            }
                        }
                    ],
                }
            }
        ]
    }


# ---------------------------------------------------------------------------
# Cycle 2: text response
# ---------------------------------------------------------------------------


def test_complete_returns_text_response() -> None:
    client = OpenRouterClient(api_key="sk-test")
    mock_resp = _make_response(_text_body("Hello world"))

    with patch("mta.llm.openrouter_client.httpx.post", return_value=mock_resp):
        result = client.complete(
            messages=[{"role": "user", "content": "hi"}],
            tools=[],
            model="qwen/qwen2.5-vl-72b-instruct",
        )

    assert result.kind == "text"
    assert result.text == "Hello world"
    assert result.tool_name is None
    assert result.tool_args is None


# ---------------------------------------------------------------------------
# Cycle 3: tool_calls response
# ---------------------------------------------------------------------------


def test_complete_returns_tool_use_response() -> None:
    client = OpenRouterClient(api_key="sk-test")
    mock_resp = _make_response(_tool_body("click", {"selector": "#submit"}))

    with patch("mta.llm.openrouter_client.httpx.post", return_value=mock_resp):
        result = client.complete(
            messages=[{"role": "user", "content": "click submit"}],
            tools=[{"name": "click", "description": "click", "input_schema": {}}],
            model="qwen/qwen2.5-vl-72b-instruct",
        )

    assert result.kind == "tool_use"
    assert result.tool_name == "click"
    assert result.tool_args == {"selector": "#submit"}
    assert result.text is None


# ---------------------------------------------------------------------------
# Cycle 4: HTTP errors → LLMError
# ---------------------------------------------------------------------------


def test_http_status_error_raises_llm_error() -> None:
    client = OpenRouterClient(api_key="sk-bad")
    mock_resp = _make_response({}, status_code=401)

    with patch("mta.llm.openrouter_client.httpx.post", return_value=mock_resp):
        with pytest.raises(LLMError, match="OpenRouter HTTP error"):
            client.complete(
                messages=[{"role": "user", "content": "hi"}],
                tools=[],
                model="qwen/qwen2.5-vl-72b-instruct",
            )


def test_network_error_raises_llm_error() -> None:
    client = OpenRouterClient(api_key="sk-test")

    with patch(
        "mta.llm.openrouter_client.httpx.post",
        side_effect=httpx.ConnectError("connection refused"),
    ):
        with pytest.raises(LLMError, match="OpenRouter HTTP error"):
            client.complete(
                messages=[{"role": "user", "content": "hi"}],
                tools=[],
                model="qwen/qwen2.5-vl-72b-instruct",
            )


# ---------------------------------------------------------------------------
# Cycle 5: tool schema translated from Anthropic → OpenAI format
# ---------------------------------------------------------------------------


def test_tools_translated_to_openai_format() -> None:
    client = OpenRouterClient(api_key="sk-test")
    mock_resp = _make_response(_text_body("ok"))
    captured: list[dict[str, object]] = []

    def capture_post(url: str, **kwargs: object) -> MagicMock:
        captured.append(kwargs)  # type: ignore[arg-type]
        return mock_resp

    anthropic_tools = [
        {
            "name": "click",
            "description": "Click an element",
            "input_schema": {
                "type": "object",
                "properties": {"selector": {"type": "string"}},
                "required": ["selector"],
            },
        }
    ]

    with patch("mta.llm.openrouter_client.httpx.post", side_effect=capture_post):
        client.complete(
            messages=[{"role": "user", "content": "hi"}],
            tools=anthropic_tools,
            model="qwen/qwen2.5-vl-72b-instruct",
        )

    sent_tools = captured[0]["json"]["tools"]  # type: ignore[index]
    assert len(sent_tools) == 1
    tool = sent_tools[0]
    assert tool["type"] == "function"
    assert tool["function"]["name"] == "click"
    assert tool["function"]["description"] == "Click an element"
    assert tool["function"]["parameters"]["properties"]["selector"]["type"] == "string"
