import pytest

from mta.llm.anthropic_client import LLMError, LLMResponse
from mta.tools import ACTION_TOOLS, Action, parse_tool_call

_EXPECTED_NAMES = {
    "navigate",
    "click",
    "type",
    "select",
    "scroll",
    "wait",
    "check",
    "uncheck",
    "upload",
    "assert_visible",
    "assert_text",
    "assert_url",
}


# --- ACTION_TOOLS structure ---


def test_action_tools_has_12_entries() -> None:
    assert len(ACTION_TOOLS) == 12


def test_action_tools_all_have_required_keys() -> None:
    for tool in ACTION_TOOLS:
        assert "name" in tool
        assert "description" in tool
        assert "input_schema" in tool


def test_action_tools_names_match_expected() -> None:
    names = {t["name"] for t in ACTION_TOOLS}
    assert names == _EXPECTED_NAMES


def test_navigate_required_fields() -> None:
    nav = next(t for t in ACTION_TOOLS if t["name"] == "navigate")
    assert nav["input_schema"]["required"] == ["url"]


def test_type_required_fields() -> None:
    t = next(tool for tool in ACTION_TOOLS if tool["name"] == "type")
    assert set(t["input_schema"]["required"]) == {"selector", "text"}


def test_assert_text_required_fields() -> None:
    t = next(tool for tool in ACTION_TOOLS if tool["name"] == "assert_text")
    assert set(t["input_schema"]["required"]) == {"selector", "expected"}


def test_wait_uses_oneof_schema() -> None:
    t = next(tool for tool in ACTION_TOOLS if tool["name"] == "wait")
    prop = t["input_schema"]["properties"]["ms_or_selector"]
    assert "oneOf" in prop


# --- parse_tool_call valid cases ---


def _tool(name: str, args: dict) -> LLMResponse:  # type: ignore[type-arg]
    return LLMResponse(kind="tool_use", tool_name=name, tool_args=args)


def test_parse_navigate() -> None:
    r = parse_tool_call(_tool("navigate", {"url": "https://example.com"}))
    assert r == Action(action_type="navigate", args={"url": "https://example.com"})


def test_parse_click() -> None:
    r = parse_tool_call(_tool("click", {"selector": "button#submit"}))
    assert r == Action(action_type="click", args={"selector": "button#submit"})


def test_parse_type() -> None:
    r = parse_tool_call(_tool("type", {"selector": "#email", "text": "user@test.com"}))
    assert r == Action(action_type="type", args={"selector": "#email", "text": "user@test.com"})


def test_parse_select() -> None:
    r = parse_tool_call(_tool("select", {"selector": "#role", "value": "admin"}))
    assert r == Action(action_type="select", args={"selector": "#role", "value": "admin"})


def test_parse_scroll() -> None:
    r = parse_tool_call(_tool("scroll", {"selector_or_direction": "down"}))
    assert r == Action(action_type="scroll", args={"selector_or_direction": "down"})


def test_parse_wait_int() -> None:
    r = parse_tool_call(_tool("wait", {"ms_or_selector": 500}))
    assert r == Action(action_type="wait", args={"ms_or_selector": 500})


def test_parse_wait_string() -> None:
    r = parse_tool_call(_tool("wait", {"ms_or_selector": "#loader"}))
    assert r == Action(action_type="wait", args={"ms_or_selector": "#loader"})


def test_parse_check() -> None:
    r = parse_tool_call(_tool("check", {"selector": "#terms"}))
    assert r == Action(action_type="check", args={"selector": "#terms"})


def test_parse_uncheck() -> None:
    r = parse_tool_call(_tool("uncheck", {"selector": "#remember"}))
    assert r == Action(action_type="uncheck", args={"selector": "#remember"})


def test_parse_upload() -> None:
    r = parse_tool_call(_tool("upload", {"selector": "#file", "path": "/tmp/doc.pdf"}))
    assert r == Action(action_type="upload", args={"selector": "#file", "path": "/tmp/doc.pdf"})


def test_parse_assert_visible() -> None:
    r = parse_tool_call(_tool("assert_visible", {"selector": ".modal"}))
    assert r == Action(action_type="assert_visible", args={"selector": ".modal"})


def test_parse_assert_text() -> None:
    r = parse_tool_call(_tool("assert_text", {"selector": "h1", "expected": "Welcome"}))
    assert r == Action(action_type="assert_text", args={"selector": "h1", "expected": "Welcome"})


def test_parse_assert_url() -> None:
    r = parse_tool_call(_tool("assert_url", {"expected": "/dashboard"}))
    assert r == Action(action_type="assert_url", args={"expected": "/dashboard"})


# --- parse_tool_call error cases ---


def test_text_response_raises() -> None:
    with pytest.raises(LLMError, match="expected tool_use response, got text"):
        parse_tool_call(LLMResponse(kind="text", text="some text"))


def test_unknown_tool_raises() -> None:
    with pytest.raises(LLMError, match="unknown tool"):
        parse_tool_call(_tool("hover", {"selector": "#btn"}))


def test_missing_required_arg_raises() -> None:
    with pytest.raises(LLMError, match="missing required arg"):
        parse_tool_call(_tool("click", {}))


def test_wrong_type_raises() -> None:
    with pytest.raises(LLMError):
        parse_tool_call(_tool("navigate", {"url": 123}))


def test_none_tool_name_raises() -> None:
    with pytest.raises(LLMError, match="unknown tool"):
        parse_tool_call(LLMResponse(kind="tool_use", tool_name=None, tool_args={}))
