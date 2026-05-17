"""Replay mode — deterministic, cache-driven execution. Never calls the LLM.

Walks an ordered list of CacheEntry objects and dispatches each via the
Executor using the cached action_type + args. Returns a list[Result] with
mode="cache" so the reporter (issue 027) can tag the cost bucket.

Drift handling: when the Executor exhausts max_retries it raises DriftError;
ReplayMode lets it propagate so the heal engine (issue 033) can react. No
silent retry beyond the executor's wrapper.

Legacy entries (written before issue 023 extended CacheEntry with args) only
carry the selector field. ReplayMode falls back to {"selector": entry.selector}
in that case so existing caches remain replayable. Note: legacy entries for
type / select / navigate / etc. lack the extra args (text, value, url) and
will fail at dispatch with KeyError — re-author those tests to refresh cache.

The LLMClient is held on construction only to make the no-LLM-call invariant
visible in tests (mock the client, assert .complete is never called).
"""

from __future__ import annotations

import logging

from playwright.async_api import Page

logger = logging.getLogger(__name__)

from mta.author import Result, _dispatch
from mta.cache import CacheEntry
from mta.executor import Executor
from mta.llm.client import LLMClient
from mta.tools import Action


class ReplayMode:
    def __init__(self, llm_client: LLMClient, max_retries: int = 2) -> None:
        self._llm = llm_client
        self._max_retries = max_retries

    async def run(self, page: Page, entries: list[CacheEntry]) -> list[Result]:
        executor = Executor(page, max_retries=self._max_retries)
        results: list[Result] = []
        for entry in entries:
            logger.debug("replay step=%d action=%s", entry.step_index, entry.action_type)
            args = entry.args or (
                {"selector": entry.selector} if entry.selector else {}
            )
            action = Action(action_type=entry.action_type, args=dict(args))
            action_result = await _dispatch(executor, action)
            results.append(
                Result(
                    channel="cache",
                    action=action,
                    action_result=action_result,
                    semantic_anchor=entry.semantic_anchor,
                    mode="cache",
                )
            )
        return results
