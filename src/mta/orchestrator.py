"""Orchestrator — selects run mode based on cache presence and drives author mode.

Mode selection:
  - cache file (test_path.with_suffix('.mta.json')) absent → "author"
  - cache file present + ReplayMode injected → "replay" (dispatch cached actions)
  - cache file present + no ReplayMode → "replay-pending" (entries loaded, not dispatched)

In author mode, every step is resolved via AuthorMode.resolve_and_run and the
resulting selector + semantic anchor is appended to the per-test cache file.
The cache file is written atomically per CacheWriter's contract.

In replay mode the cache entries are loaded via CacheReader and dispatched via
ReplayMode.run, returning Result objects tagged mode="cache". The legacy
"replay-pending" path is retained for callers (e.g. unit tests) that don't
wire a ReplayMode — they still get the loaded entries on RunResult.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from playwright.async_api import Page

from mta.arbiter import Step
from mta.author import AuthorMode, Result
from mta.cache import CacheEntry, CacheReader, CacheWriter
from mta.replay import ReplayMode
from mta.tools import Action

Mode = Literal["author", "replay", "replay-pending"]


@dataclass
class RunResult:
    mode: Mode
    test_path: Path
    step_results: list[Result] = field(default_factory=list)
    cache_entries: list[CacheEntry] = field(default_factory=list)


def _selector_arg(action: Action) -> str:
    sel = action.args.get("selector")
    return sel if isinstance(sel, str) else ""


class Orchestrator:
    def __init__(
        self,
        author_mode: AuthorMode,
        page: Page,
        replay_mode: ReplayMode | None = None,
    ) -> None:
        self._author_mode = author_mode
        self._page = page
        self._replay_mode = replay_mode

    async def run(self, test_path: Path, steps: list[Step]) -> RunResult:
        cache_path = test_path.with_suffix(".mta.json")
        if cache_path.exists():
            entries = CacheReader.load(test_path)
            if self._replay_mode is not None:
                step_results = await self._replay_mode.run(self._page, entries)
                return RunResult(
                    mode="replay",
                    test_path=test_path,
                    step_results=step_results,
                    cache_entries=entries,
                )
            return RunResult(
                mode="replay-pending",
                test_path=test_path,
                cache_entries=entries,
            )

        writer = CacheWriter(test_path)
        results: list[Result] = []
        for i, step in enumerate(steps):
            result = await self._author_mode.resolve_and_run(self._page, step)
            entry = CacheEntry(
                step_index=i,
                description=step.description,
                action_type=result.action.action_type,
                selector=_selector_arg(result.action),
                semantic_anchor=result.semantic_anchor,
                args=dict(result.action.args),
            )
            writer.append(entry)
            results.append(result)
        return RunResult(mode="author", test_path=test_path, step_results=results)
