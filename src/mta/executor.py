"""Action Executor — runs browser actions via Playwright and returns structured results.

ActionResult shape:
    success: bool        — True if the action completed without error
    action: str          — action name: "navigate" | "click" | "type" | "select" |
                           "scroll" | "wait" | "check" | "uncheck" | "upload"
    selector: str | None — CSS/text selector used; None for navigate and ms-form wait
    duration_ms: float   — wall-clock time for the action in milliseconds
    error: str | None    — error message on failure; None on success

No action method raises an exception to the caller.  All Playwright errors are
caught and returned as ActionResult(success=False, error=...).
"""

import time
from dataclasses import dataclass

from playwright.async_api import Page


@dataclass
class ActionResult:
    success: bool
    action: str
    selector: str | None
    duration_ms: float
    error: str | None


class Executor:
    def __init__(self, page: Page) -> None:
        self._page = page

    async def navigate(self, url: str) -> ActionResult:
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

    async def type(self, selector: str, text: str) -> ActionResult:
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

    async def select(self, selector: str, value: str) -> ActionResult:
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

    async def upload(self, selector: str, path: str) -> ActionResult:
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

    async def check(self, selector: str) -> ActionResult:
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

    async def uncheck(self, selector: str) -> ActionResult:
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

    async def wait(self, ms_or_selector: int | str) -> ActionResult:
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
            selector: str | None = None if is_ms else str(ms_or_selector)
            return ActionResult(
                success=False,
                action="wait",
                selector=selector,
                duration_ms=(time.monotonic() - t0) * 1000,
                error=str(exc),
            )

    async def scroll(self, selector_or_direction: str) -> ActionResult:
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

    async def click(self, selector: str) -> ActionResult:
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
