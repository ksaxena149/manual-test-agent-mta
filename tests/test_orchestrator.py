"""Orchestrator tests — mode selection based on cache presence.

Covers issue 022 acceptance criteria:
  - cache absent → author mode runs for every step, cache file written.
  - cache present → RunResult flagged "replay-pending"; author mode not called.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, Mock

from mta.arbiter import Step
from mta.author import AuthorMode, Result
from mta.executor import ActionResult
from mta.orchestrator import Orchestrator, RunResult
from mta.tools import Action


def _result(action_type: str, selector: str, channel: str = "snapshot-direct") -> Result:
    return Result(
        channel=channel,
        action=Action(action_type=action_type, args={"selector": selector}),
        action_result=ActionResult(
            success=True,
            action=action_type,
            selector=selector,
            duration_ms=1.0,
            error=None,
        ),
        semantic_anchor={"parent_text": "p", "sibling_text": "", "nearby_labels": ""},
    )


async def test_cache_absent_runs_author_and_writes_cache(tmp_path: Path) -> None:
    test_path = tmp_path / "test_login.md"
    test_path.write_text("dummy")

    author_mode = Mock(spec=AuthorMode)
    author_mode.resolve_and_run = AsyncMock(
        side_effect=[
            _result("click", "#submit"),
            _result("click", "#next", channel="snapshot-llm"),
        ]
    )
    page = Mock()
    orch = Orchestrator(author_mode=author_mode, page=page)

    steps = [
        Step(action="click", description="click submit"),
        Step(action="click", description="click next"),
    ]
    result = await orch.run(test_path, steps)

    assert isinstance(result, RunResult)
    assert result.mode == "author"
    assert len(result.step_results) == 2
    assert author_mode.resolve_and_run.call_count == 2

    cache_path = tmp_path / "test_login.mta.json"
    assert cache_path.exists()
    data = json.loads(cache_path.read_text())
    assert len(data) == 2
    assert data[0]["step_index"] == 0
    assert data[0]["action_type"] == "click"
    assert data[0]["selector"] == "#submit"
    assert data[0]["description"] == "click submit"
    assert data[1]["step_index"] == 1
    assert data[1]["selector"] == "#next"
    assert data[0]["semantic_anchor"]["parent_text"] == "p"


async def test_cache_present_returns_replay_pending(tmp_path: Path) -> None:
    test_path = tmp_path / "test_login.md"
    test_path.write_text("dummy")
    cache_path = tmp_path / "test_login.mta.json"
    cache_path.write_text(
        json.dumps(
            [
                {
                    "step_index": 0,
                    "description": "click submit",
                    "action_type": "click",
                    "selector": "#submit",
                    "semantic_anchor": {},
                }
            ]
        )
    )

    author_mode = Mock(spec=AuthorMode)
    author_mode.resolve_and_run = AsyncMock()
    page = Mock()
    orch = Orchestrator(author_mode=author_mode, page=page)

    result = await orch.run(
        test_path, [Step(action="click", description="click submit")]
    )

    assert result.mode == "replay-pending"
    author_mode.resolve_and_run.assert_not_called()
    assert len(result.cache_entries) == 1
    assert result.cache_entries[0].selector == "#submit"
    assert result.cache_entries[0].step_index == 0
    assert result.step_results == []


async def test_cache_absent_no_steps_writes_empty_cache(tmp_path: Path) -> None:
    """Edge case: zero steps still produces author mode result; cache file may
    be empty (no append) but mode is still 'author'."""
    test_path = tmp_path / "test_empty.md"
    test_path.write_text("dummy")

    author_mode = Mock(spec=AuthorMode)
    author_mode.resolve_and_run = AsyncMock()
    page = Mock()
    orch = Orchestrator(author_mode=author_mode, page=page)

    result = await orch.run(test_path, [])
    assert result.mode == "author"
    assert result.step_results == []
    author_mode.resolve_and_run.assert_not_called()
