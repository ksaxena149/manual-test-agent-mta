import pytest

from mta.arbiter import Arbiter, Candidate, Step
from mta.snapshot import Snapshot


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


# --- score_candidates ---


def _snap(*elements: dict[str, str]) -> Snapshot:
    return Snapshot(elements=list(elements))


def _el(role: str, name: str) -> dict[str, str]:
    return {"role": role, "name": name, "selector": f'role={role}[name="{name}"]'}


def test_score_candidates_returns_list_sorted_descending(arbiter: Arbiter) -> None:
    snap = _snap(_el("button", "Submit"), _el("link", "Cancel"))
    candidates = arbiter.score_candidates(snap, "click the submit button")
    assert len(candidates) == 2
    assert isinstance(candidates[0], Candidate)
    assert candidates[0].score >= candidates[1].score


def test_score_candidates_clear_winner_exceeds_threshold(arbiter: Arbiter) -> None:
    # "submit button" matches name "Submit" (jaccard) + role "button" in desc → > 0.3
    snap = _snap(_el("button", "Submit"), _el("link", "Cancel"))
    candidates = arbiter.score_candidates(snap, "click the submit button")
    assert candidates[0].element["name"] == "Submit"
    assert candidates[0].score > 0.3


def test_score_candidates_no_matches_scores_near_zero(arbiter: Arbiter) -> None:
    snap = _snap(_el("button", "Xyzzy"), _el("link", "Frobnik"))
    candidates = arbiter.score_candidates(snap, "do something entirely different")
    # No token overlap, no role match → all scores 0.0
    assert all(c.score == 0.0 for c in candidates)


# --- resolve_from_snapshot ---


def test_resolve_clear_winner_returns_snapshot_and_candidate(arbiter: Arbiter) -> None:
    # "Submit" button scores ~0.35 (jaccard 0.25 + role bonus 0.1); "Cancel" link ~0
    snap = _snap(_el("button", "Submit"), _el("link", "Cancel"))
    channel, candidate = arbiter.resolve_from_snapshot(snap, "click the submit button")
    assert channel == "snapshot"
    assert candidate is not None
    assert candidate.element["name"] == "Submit"


def test_resolve_tie_returns_vision(arbiter: Arbiter) -> None:
    # Both score 0.5 (tied) ≥ tie_threshold(0.15) → vision
    snap = _snap(_el("button", "Submit Now"), _el("button", "Submit Later"))
    channel, candidate = arbiter.resolve_from_snapshot(snap, "submit")
    assert channel == "vision"
    assert candidate is None


def test_resolve_no_matches_returns_vision(arbiter: Arbiter) -> None:
    snap = _snap(_el("button", "Xyzzy"), _el("link", "Frobnik"))
    channel, candidate = arbiter.resolve_from_snapshot(
        snap, "do something entirely different"
    )
    assert channel == "vision"
    assert candidate is None


def test_resolve_empty_snapshot_returns_vision(arbiter: Arbiter) -> None:
    channel, candidate = arbiter.resolve_from_snapshot(Snapshot(), "click submit")
    assert channel == "vision"
    assert candidate is None


def test_resolve_borderline_just_above_threshold_returns_snapshot() -> None:
    # Top score = 0.31 (just over 0.3), second = 0.0 → snapshot
    arbiter = Arbiter(high_confidence_threshold=0.3, tie_threshold=0.15)
    snap = _snap(
        {"role": "button", "name": "Submit", "selector": "role=button[name='Submit']"},
    )
    channel, candidate = arbiter.resolve_from_snapshot(snap, "click submit button")
    # Verify score is above the threshold before asserting channel
    candidates = arbiter.score_candidates(snap, "click submit button")
    assert candidates[0].score > 0.3
    assert channel == "snapshot"


def test_resolve_custom_thresholds_respected() -> None:
    # Raise high_confidence_threshold so a normally-passing score now fails
    arbiter = Arbiter(high_confidence_threshold=0.9, tie_threshold=0.15)
    snap = _snap(_el("button", "Submit"), _el("link", "Cancel"))
    channel, candidate = arbiter.resolve_from_snapshot(snap, "click the submit button")
    assert channel == "vision"  # score ~0.35 < 0.9 threshold


def test_score_candidates_tie_scores_are_equal(arbiter: Arbiter) -> None:
    # "Submit Now" and "Submit Later" both share one token ("submit") with desc,
    # same union size (2) → identical Jaccard 0.5; same role → equal scores
    snap = _snap(_el("button", "Submit Now"), _el("button", "Submit Later"))
    candidates = arbiter.score_candidates(snap, "submit")
    assert candidates[0].score == candidates[1].score
