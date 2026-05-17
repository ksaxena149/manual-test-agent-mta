import pytest

from mta.arbiter import Arbiter, Step


@pytest.fixture()
def arbiter() -> Arbiter:
    return Arbiter()


# --- structural actions → snapshot ---


def test_click_returns_snapshot(arbiter: Arbiter) -> None:
    result = arbiter.choose_channel(Step("click", "click the submit button"))
    assert result == "snapshot"


def test_type_returns_snapshot(arbiter: Arbiter) -> None:
    result = arbiter.choose_channel(Step("type", "type username into field"))
    assert result == "snapshot"


def test_select_returns_snapshot(arbiter: Arbiter) -> None:
    result = arbiter.choose_channel(Step("select", "select option from dropdown"))
    assert result == "snapshot"


def test_check_returns_snapshot(arbiter: Arbiter) -> None:
    result = arbiter.choose_channel(Step("check", "check the terms checkbox"))
    assert result == "snapshot"


def test_uncheck_returns_snapshot(arbiter: Arbiter) -> None:
    result = arbiter.choose_channel(Step("uncheck", "uncheck remember me"))
    assert result == "snapshot"


def test_fill_returns_snapshot(arbiter: Arbiter) -> None:
    result = arbiter.choose_channel(Step("fill", "fill in the email address"))
    assert result == "snapshot"


# --- visual/appearance descriptions → vision ---


def test_description_with_looks_returns_vision(arbiter: Arbiter) -> None:
    result = arbiter.choose_channel(Step("assert_visible", "button looks disabled"))
    assert result == "vision"


def test_description_with_appears_returns_vision(arbiter: Arbiter) -> None:
    result = arbiter.choose_channel(Step("assert_visible", "element appears blue"))
    assert result == "vision"


def test_description_with_color_returns_vision(arbiter: Arbiter) -> None:
    step = Step("assert_visible", "check the color of the header")
    assert arbiter.choose_channel(step) == "vision"


def test_description_with_highlighted_returns_vision(arbiter: Arbiter) -> None:
    result = arbiter.choose_channel(Step("assert_visible", "row is highlighted"))
    assert result == "vision"


# --- structural action wins over visual description ---


def test_structural_action_overrides_visual_description(arbiter: Arbiter) -> None:
    # "color" in description but action is structural → snapshot wins
    result = arbiter.choose_channel(Step("click", "click the color swatch"))
    assert result == "snapshot"


def test_structural_type_overrides_visual_description(arbiter: Arbiter) -> None:
    result = arbiter.choose_channel(Step("type", "type looks-like text"))
    assert result == "snapshot"


# --- default fallback: non-structural, no visual cue → snapshot ---


def test_non_structural_no_visual_cue_returns_snapshot(arbiter: Arbiter) -> None:
    result = arbiter.choose_channel(Step("assert_url", "check the page url"))
    assert result == "snapshot"
