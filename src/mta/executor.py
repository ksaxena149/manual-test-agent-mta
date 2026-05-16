"""Action Executor — runs browser actions via Playwright and returns structured results.

ActionResult shape:
    success: bool        — True if the action completed without error
    action: str          — action name: "navigate" | "click" | "type" | "select" |
                           "scroll" | "wait" | "check" | "uncheck" | "upload" |
                           "assert_visible" | "assert_text" | "assert_url"
    selector: str | None — CSS/text selector used; None for navigate and ms-form wait
    duration_ms: float   — wall-clock time for the action in milliseconds
    error: str | None    — error message on failure; None on success
    attempts: int        — how many tries it took (1 = first try, >1 = retried)

On final failure after max_retries exhaustion, DriftError is raised (not returned).
"""

import asyncio
import time
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from typing import Any

from playwright.async_api import Page


@dataclass
class ActionResult:
    success: bool
    action: str
    selector: str | None
    duration_ms: float
    error: str | None
    attempts: int = field(default=1)


class DriftError(Exception):
    def __init__(
        self, action: str, selector: str | None, error: str, attempts: int
    ) -> None:
        super().__init__(f"{action} failed after {attempts} attempt(s): {error}")
        self.action = action
        self.selector = selector
        self.error = error
        self.attempts = attempts


class Executor:
    def __init__(self, page: Page, max_retries: int = 2) -> None:
        self._page = page
        self._max_retries = max_retries

    async def _run_with_retry(
        self,
        coro_fn: Callable[[], Coroutine[Any, Any, ActionResult]],
    ) -> ActionResult:
        last: ActionResult | None = None
        total = self._max_retries + 1
        for attempt in range(1, total + 1):
            result = await coro_fn()
            result.attempts = attempt
            if result.success:
                return result
            last = result
            if attempt < total:
                await asyncio.sleep(0.1 * attempt)
        assert last is not None
        raise DriftError(
            action=last.action,
            selector=last.selector,
            error=last.error or "",
            attempts=last.attempts,
        )

    async def navigate(self, url: str) -> ActionResult:
        async def _inner() -> ActionResult:
            t0 = time.monotonic()
            try:
                await self._page.goto(url)
                return ActionResult(
                    success=True,
                    action="navigate",
                    selector=None,
                    duration_ms=(time.monotonic() - t0) * 1000,
                    error=None,
                )
            except Exception as exc:
                return ActionResult(
                    success=False,
                    action="navigate",
                    selector=None,
                    duration_ms=(time.monotonic() - t0) * 1000,
                    error=str(exc),
                )

        return await self._run_with_retry(_inner)

    async def click(self, selector: str) -> ActionResult:
        async def _inner() -> ActionResult:
            t0 = time.monotonic()
            try:
                await self._page.locator(selector).click()
                return ActionResult(
                    success=True,
                    action="click",
                    selector=selector,
                    duration_ms=(time.monotonic() - t0) * 1000,
                    error=None,
                )
            except Exception as exc:
                return ActionResult(
                    success=False,
                    action="click",
                    selector=selector,
                    duration_ms=(time.monotonic() - t0) * 1000,
                    error=str(exc),
                )

        return await self._run_with_retry(_inner)

    async def type(self, selector: str, text: str) -> ActionResult:
        async def _inner() -> ActionResult:
            t0 = time.monotonic()
            try:
                await self._page.locator(selector).fill(text)
                return ActionResult(
                    success=True,
                    action="type",
                    selector=selector,
                    duration_ms=(time.monotonic() - t0) * 1000,
                    error=None,
                )
            except Exception as exc:
                return ActionResult(
                    success=False,
                    action="type",
                    selector=selector,
                    duration_ms=(time.monotonic() - t0) * 1000,
                    error=str(exc),
                )

        return await self._run_with_retry(_inner)

    async def select(self, selector: str, value: str) -> ActionResult:
        async def _inner() -> ActionResult:
            t0 = time.monotonic()
            try:
                await self._page.locator(selector).select_option(value=value)
                return ActionResult(
                    success=True,
                    action="select",
                    selector=selector,
                    duration_ms=(time.monotonic() - t0) * 1000,
                    error=None,
                )
            except Exception as exc:
                return ActionResult(
                    success=False,
                    action="select",
                    selector=selector,
                    duration_ms=(time.monotonic() - t0) * 1000,
                    error=str(exc),
                )

        return await self._run_with_retry(_inner)

    async def upload(self, selector: str, path: str) -> ActionResult:
        async def _inner() -> ActionResult:
            t0 = time.monotonic()
            try:
                await self._page.locator(selector).set_input_files(path)
                return ActionResult(
                    success=True,
                    action="upload",
                    selector=selector,
                    duration_ms=(time.monotonic() - t0) * 1000,
                    error=None,
                )
            except Exception as exc:
                return ActionResult(
                    success=False,
                    action="upload",
                    selector=selector,
                    duration_ms=(time.monotonic() - t0) * 1000,
                    error=str(exc),
                )

        return await self._run_with_retry(_inner)

    async def check(self, selector: str) -> ActionResult:
        async def _inner() -> ActionResult:
            t0 = time.monotonic()
            try:
                loc = self._page.locator(selector)
                await loc.check()
                if not await loc.is_checked():
                    return ActionResult(
                        success=False,
                        action="check",
                        selector=selector,
                        duration_ms=(time.monotonic() - t0) * 1000,
                        error="element is not checked after check()",
                    )
                return ActionResult(
                    success=True,
                    action="check",
                    selector=selector,
                    duration_ms=(time.monotonic() - t0) * 1000,
                    error=None,
                )
            except Exception as exc:
                return ActionResult(
                    success=False,
                    action="check",
                    selector=selector,
                    duration_ms=(time.monotonic() - t0) * 1000,
                    error=str(exc),
                )

        return await self._run_with_retry(_inner)

    async def uncheck(self, selector: str) -> ActionResult:
        async def _inner() -> ActionResult:
            t0 = time.monotonic()
            try:
                loc = self._page.locator(selector)
                await loc.uncheck()
                if await loc.is_checked():
                    return ActionResult(
                        success=False,
                        action="uncheck",
                        selector=selector,
                        duration_ms=(time.monotonic() - t0) * 1000,
                        error="element is still checked after uncheck()",
                    )
                return ActionResult(
                    success=True,
                    action="uncheck",
                    selector=selector,
                    duration_ms=(time.monotonic() - t0) * 1000,
                    error=None,
                )
            except Exception as exc:
                return ActionResult(
                    success=False,
                    action="uncheck",
                    selector=selector,
                    duration_ms=(time.monotonic() - t0) * 1000,
                    error=str(exc),
                )

        return await self._run_with_retry(_inner)

    async def wait(self, ms_or_selector: int | str) -> ActionResult:
        async def _inner() -> ActionResult:
            t0 = time.monotonic()
            try:
                if isinstance(ms_or_selector, int) or str(ms_or_selector).isdigit():
                    ms = int(ms_or_selector)
                    await self._page.wait_for_timeout(ms)
                    return ActionResult(
                        success=True,
                        action="wait",
                        selector=None,
                        duration_ms=(time.monotonic() - t0) * 1000,
                        error=None,
                    )
                else:
                    await self._page.locator(ms_or_selector).wait_for(state="visible")
                    return ActionResult(
                        success=True,
                        action="wait",
                        selector=ms_or_selector,
                        duration_ms=(time.monotonic() - t0) * 1000,
                        error=None,
                    )
            except Exception as exc:
                is_ms = isinstance(ms_or_selector, int) or str(ms_or_selector).isdigit()
                sel: str | None = None if is_ms else str(ms_or_selector)
                return ActionResult(
                    success=False,
                    action="wait",
                    selector=sel,
                    duration_ms=(time.monotonic() - t0) * 1000,
                    error=str(exc),
                )

        return await self._run_with_retry(_inner)

    async def scroll(self, selector_or_direction: str) -> ActionResult:
        async def _inner() -> ActionResult:
            t0 = time.monotonic()
            try:
                if selector_or_direction == "down":
                    await self._page.evaluate("window.scrollBy(0, window.innerHeight)")
                elif selector_or_direction == "up":
                    await self._page.evaluate("window.scrollBy(0, -window.innerHeight)")
                else:
                    loc = self._page.locator(selector_or_direction)
                    await loc.scroll_into_view_if_needed()
                return ActionResult(
                    success=True,
                    action="scroll",
                    selector=selector_or_direction,
                    duration_ms=(time.monotonic() - t0) * 1000,
                    error=None,
                )
            except Exception as exc:
                return ActionResult(
                    success=False,
                    action="scroll",
                    selector=selector_or_direction,
                    duration_ms=(time.monotonic() - t0) * 1000,
                    error=str(exc),
                )

        return await self._run_with_retry(_inner)

    async def assert_visible(self, selector: str) -> ActionResult:
        async def _inner() -> ActionResult:
            t0 = time.monotonic()
            try:
                visible = await self._page.locator(selector).is_visible()
                if not visible:
                    return ActionResult(
                        success=False,
                        action="assert_visible",
                        selector=selector,
                        duration_ms=(time.monotonic() - t0) * 1000,
                        error=f"element '{selector}' is not visible",
                    )
                return ActionResult(
                    success=True,
                    action="assert_visible",
                    selector=selector,
                    duration_ms=(time.monotonic() - t0) * 1000,
                    error=None,
                )
            except Exception as exc:
                return ActionResult(
                    success=False,
                    action="assert_visible",
                    selector=selector,
                    duration_ms=(time.monotonic() - t0) * 1000,
                    error=str(exc),
                )

        return await self._run_with_retry(_inner)

    async def assert_text(self, selector: str, expected: str) -> ActionResult:
        async def _inner() -> ActionResult:
            t0 = time.monotonic()
            try:
                actual = (await self._page.locator(selector).inner_text()).strip()
                if actual != expected:
                    return ActionResult(
                        success=False,
                        action="assert_text",
                        selector=selector,
                        duration_ms=(time.monotonic() - t0) * 1000,
                        error=f"expected '{expected}', got '{actual}'",
                    )
                return ActionResult(
                    success=True,
                    action="assert_text",
                    selector=selector,
                    duration_ms=(time.monotonic() - t0) * 1000,
                    error=None,
                )
            except Exception as exc:
                return ActionResult(
                    success=False,
                    action="assert_text",
                    selector=selector,
                    duration_ms=(time.monotonic() - t0) * 1000,
                    error=str(exc),
                )

        return await self._run_with_retry(_inner)

    async def assert_url(self, expected: str) -> ActionResult:
        """Passes when the current page URL contains `expected` as a substring."""

        async def _inner() -> ActionResult:
            t0 = time.monotonic()
            actual = self._page.url
            if expected not in actual:
                return ActionResult(
                    success=False,
                    action="assert_url",
                    selector=None,
                    duration_ms=(time.monotonic() - t0) * 1000,
                    error=f"expected URL to contain '{expected}', got '{actual}'",
                )
            return ActionResult(
                success=True,
                action="assert_url",
                selector=None,
                duration_ms=(time.monotonic() - t0) * 1000,
                error=None,
            )

        return await self._run_with_retry(_inner)
