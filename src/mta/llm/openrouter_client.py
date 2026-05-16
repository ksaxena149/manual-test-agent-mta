"""OpenRouter provider for the LLM Client module.

Uses plain HTTP (httpx) against OpenRouter's OpenAI-compatible chat completions
endpoint.

Response convention:
- First tool_call wins; remaining ignored.
- If no tool_calls, content string returned as text.
- max_tokens defaults to 4096.

Tool schema translation:
  Anthropic: {name, description, input_schema}
  OpenAI:    {type:"function", function:{name, description, parameters}}
"""

import json as _json
from typing import Any

import httpx

from mta.llm.anthropic_client import LLMError, LLMResponse


def _to_openai_tool(tool: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": tool["name"],
            "description": tool.get("description", ""),
            "parameters": tool.get("input_schema", {}),
        },
    }


class OpenRouterClient:
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://openrouter.ai/api/v1",
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url

    def complete(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        model: str,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        try:
            resp = httpx.post(
                f"{self._base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "max_tokens": max_tokens,
                    "messages": messages,
                    "tools": [_to_openai_tool(t) for t in tools] if tools else [],
                },
                timeout=120.0,
            )
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise LLMError(f"OpenRouter HTTP error: {exc}") from exc

        data = resp.json()
        message = data["choices"][0]["message"]

        tool_calls = message.get("tool_calls") or []
        if tool_calls:
            fn = tool_calls[0]["function"]
            return LLMResponse(
                kind="tool_use",
                tool_name=fn["name"],
                tool_args=_json.loads(fn["arguments"]),
            )

        return LLMResponse(kind="text", text=message.get("content") or "")
