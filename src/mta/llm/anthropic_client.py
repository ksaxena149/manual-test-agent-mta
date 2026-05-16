"""Anthropic provider for the LLM Client module.

Response convention:
- First tool_use block in content wins; remaining blocks ignored.
- If no tool_use block, all text blocks are concatenated.
- max_tokens defaults to 4096.
"""

from dataclasses import dataclass
from typing import Any, Literal, cast

import anthropic
from anthropic.types import MessageParam


class LLMError(Exception):
    """SDK error wrapped with provider context."""


@dataclass
class LLMResponse:
    kind: Literal["text", "tool_use"]
    text: str | None = None
    tool_name: str | None = None
    tool_args: dict[str, object] | None = None


class AnthropicClient:
    def __init__(self, api_key: str) -> None:
        self._client = anthropic.Anthropic(api_key=api_key)

    def complete(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        model: str,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        try:
            response = self._client.messages.create(
                model=model,
                max_tokens=max_tokens,
                messages=cast(list[MessageParam], messages),
                tools=tools,  # type: ignore[arg-type]
            )
        except anthropic.APIError as exc:
            raise LLMError(f"Anthropic API error: {exc}") from exc

        for block in response.content:
            if block.type == "tool_use":
                return LLMResponse(
                    kind="tool_use",
                    tool_name=block.name,
                    tool_args=dict(block.input),
                )

        text = "".join(
            block.text for block in response.content if block.type == "text"
        )
        return LLMResponse(kind="text", text=text)
