"""Action Executor — runs browser actions via Playwright and returns structured results.

ActionResult shape:
    success: bool        — True if the action completed without error
    action: str          — action name: "navigate" | "click" | "type" | "select"
    selector: str | None — CSS/text selector used; None for navigate
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
