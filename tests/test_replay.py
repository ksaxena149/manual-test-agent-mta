"""ReplayMode tests — deterministic cache-driven execution, zero LLM cost.

Covers issue 023 acceptance criteria:
  - run(page, entries) executes every entry and returns ordered results.
  - Mocked LLM client records zero calls.
  - Each Result records mode == "cache".
  - Executor failure (DriftError after max_retries) propagates.
"""

from __future__ import annotations

from unittest.mock import Mock

import pytest
from playwright.async_api import async_playwright

from mta.cache import CacheEntry
from mta.executor import DriftError
from mta.llm.client import LLMClient
from mta.replay import ReplayMode


async def test_replay_executes_all_entries_in_order_with_zero_llm_calls() -> None:
    """End-to-end replay against a real page: click, type, click — no LLM call."""
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        try:
            page = await browser.new_page()
            await page.set_content(
                """
                <button id="a">A</button>
                <input id="name" />
                <button id="b">B</button>
                """
            )

            llm = Mock(spec=LLMClient)
            entries = [
                CacheEntry(
                    step_index=0,
                    description="click A",
                    action_type="click",
                    selector="#a",
                    semantic_anchor={},
                    args={"selector": "#a"},
                ),
                CacheEntry(
                    step_index=1,
                    description="type name",
                    action_type="type",
                    selector="#name",
                    semantic_anchor={},
                    args={"selector": "#name", "text": "Alice"},
                ),
                CacheEntry(
                    step_index=2,
                    description="click B",
                    action_type="click",
                    selector="#b",
                    semantic_anchor={},
                    args={"selector": "#b"},
                ),
            ]

            mode = ReplayMode(llm_client=llm)
            results = await mode.run(page, entries)

            assert len(results) == 3
            assert [r.mode for r in results] == ["cache", "cache", "cache"]
            assert [r.action.action_type for r in results] == ["click", "type", "click"]
            assert all(r.action_result.success for r in results)
            assert await page.locator("#name").input_value() == "Alice"
            llm.complete.assert_not_called()
        finally:
            await browser.close()


async def test_replay_result_mode_is_cache() -> None:
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        try:
            page = await browser.new_page()
            await page.set_content("<button id='go'>Go</button>")

            llm = Mock(spec=LLMClient)
            mode = ReplayMode(llm_client=llm)
            entries = [
                CacheEntry(
                    step_index=0,
                    description="click go",
                    action_type="click",
                    selector="#go",
                    semantic_anchor={},
                    args={"selector": "#go"},
                )
            ]
            results = await mode.run(page, entries)

            assert results[0].mode == "cache"
            llm.complete.assert_not_called()
        finally:
            await browser.close()


async def test_replay_propagates_drift_error_on_executor_failure() -> None:
    """Missing selector → executor exhausts retries → DriftError propagates."""
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        try:
            page = await browser.new_page()
            page.set_default_timeout(500)
            await page.set_content("<div>nothing to click</div>")

            llm = Mock(spec=LLMClient)
            mode = ReplayMode(llm_client=llm, max_retries=0)
            entries = [
                CacheEntry(
                    step_index=0,
                    description="click missing",
                    action_type="click",
                    selector="#nope",
                    semantic_anchor={},
                    args={"selector": "#nope"},
                )
            ]
            with pytest.raises(DriftError):
                await mode.run(page, entries)
            llm.complete.assert_not_called()
        finally:
            await browser.close()


async def test_replay_falls_back_to_selector_only_for_legacy_entries() -> None:
    """Older cache entries without args still replay using selector field."""
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        try:
            page = await browser.new_page()
            await page.set_content("<button id='legacy'>Legacy</button>")

            llm = Mock(spec=LLMClient)
            mode = ReplayMode(llm_client=llm)
            # args defaults to {} — legacy cache shape
            entries = [
                CacheEntry(
                    step_index=0,
                    description="click legacy",
                    action_type="click",
                    selector="#legacy",
                    semantic_anchor={},
                )
            ]
            results = await mode.run(page, entries)

            assert results[0].action_result.success is True
            assert results[0].mode == "cache"
            llm.complete.assert_not_called()
        finally:
            await browser.close()
