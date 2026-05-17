"""LLM tool-use schema and action parser for MTA.

ACTION_TOOLS mirrors the executor's action vocabulary one-to-one.
parse_tool_call converts an LLMResponse into a typed Action.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from mta.llm.anthropic_client import LLMError, LLMResponse

_STR = {"type": "string"}
_INT = {"type": "integer"}


def _schema(
    properties: dict[str, Any],
    required: list[str],
) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": properties,
        "required": required,
    }


ACTION_TOOLS: list[dict[str, Any]] = [
    {
        "name": "navigate",
        "description": "Navigate the browser to a URL.",
        "input_schema": _schema({"url": _STR}, ["url"]),
    },
    {
        "name": "click",
        "description": "Click an element identified by a selector.",
        "input_schema": _schema({"selector": _STR}, ["selector"]),
    },
    {
        "name": "type",
        "description": "Fill an input field with text.",
        "input_schema": _schema({"selector": _STR, "text": _STR}, ["selector", "text"]),
    },
    {
        "name": "select",
        "description": "Select an option from a <select> element.",
        "input_schema": _schema({"selector": _STR, "value": _STR}, ["selector", "value"]),
    },
    {
        "name": "scroll",
        "description": "Scroll the page or an element into view.",
        "input_schema": _schema({"selector_or_direction": _STR}, ["selector_or_direction"]),
    },
    {
        "name": "wait",
        "description": "Wait a number of milliseconds or until a selector is visible.",
        "input_schema": _schema(
            {
                "ms_or_selector": {
                    "oneOf": [{"type": "integer"}, {"type": "string"}],
                    "description": "Milliseconds (int) or a CSS selector to wait for.",
                }
            },
            ["ms_or_selector"],
        ),
    },
    {
        "name": "check",
        "description": "Check a checkbox or radio button.",
        "input_schema": _schema({"selector": _STR}, ["selector"]),
    },
    {
        "name": "uncheck",
        "description": "Uncheck a checkbox.",
        "input_schema": _schema({"selector": _STR}, ["selector"]),
    },
    {
        "name": "upload",
        "description": "Upload a file to an input[type=file] element.",
        "input_schema": _schema({"selector": _STR, "path": _STR}, ["selector", "path"]),
    },
    {
        "name": "assert_visible",
        "description": "Assert that an element is visible.",
        "input_schema": _schema({"selector": _STR}, ["selector"]),
    },
    {
        "name": "assert_text",
        "description": "Assert that an element's text matches the expected string.",
        "input_schema": _schema(
            {"selector": _STR, "expected": _STR}, ["selector", "expected"]
        ),
    },
    {
        "name": "assert_url",
        "description": "Assert that the current URL contains the expected substring.",
        "input_schema": _schema({"expected": _STR}, ["expected"]),
    },
]

_TOOL_INDEX: dict[str, dict[str, Any]] = {t["name"]: t for t in ACTION_TOOLS}


@dataclass
class Action:
    action_type: str
    args: dict[str, Any]


def _validate_arg_type(name: str, value: object, schema: dict[str, Any]) -> None:
    """Raise LLMError if value doesn't match the property schema."""
    if "oneOf" in schema:
        for sub in schema["oneOf"]:
            try:
                _validate_arg_type(name, value, sub)
                return
            except LLMError:
                pass
        raise LLMError(f"arg '{name}' type invalid: got {type(value).__name__}")
    expected = schema.get("type")
    if expected == "string" and not isinstance(value, str):
        raise LLMError(f"arg '{name}' must be a string, got {type(value).__name__}")
    if expected == "integer" and not isinstance(value, int):
        raise LLMError(f"arg '{name}' must be an integer, got {type(value).__name__}")


def parse_tool_call(response: LLMResponse) -> Action:
    """Parse an LLMResponse tool_use block into a typed Action.

    Raises LLMError on: non-tool response, unknown tool, missing required arg, wrong type.
    """
    if response.kind != "tool_use":
        raise LLMError("expected tool_use response, got text")

    name = response.tool_name
    if name is None or name not in _TOOL_INDEX:
        raise LLMError(f"unknown tool: {name!r}")

    tool = _TOOL_INDEX[name]
    schema = tool["input_schema"]
    args: dict[str, Any] = dict(response.tool_args or {})

    for req in schema.get("required", []):
        if req not in args:
            raise LLMError(f"missing required arg: '{req}' for tool '{name}'")

    props: dict[str, Any] = schema.get("properties", {})
    for arg_name, value in args.items():
        if arg_name in props:
            _validate_arg_type(arg_name, value, props[arg_name])

    return Action(action_type=name, args=args)
