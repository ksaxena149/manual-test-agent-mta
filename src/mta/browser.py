from contextlib import asynccontextmanager
from typing import AsyncIterator

from playwright.async_api import Browser, BrowserContext, Page, async_playwright

from mta.config import Config


def _resolve_headless(config: Config, env: dict[str, str] | None = None) -> bool:
    if config.browser.headless is not None:
        return config.browser.headless
    if env is None:
        import os
        env = dict(os.environ)
    return "DISPLAY" not in env or "CI" in env


@asynccontextmanager
async def launch_browser(
    config: Config,
) -> AsyncIterator[tuple[Browser, BrowserContext, Page]]:
    headless = _resolve_headless(config)
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=headless)
        try:
            context = await browser.new_context()
            page = await context.new_page()
            yield browser, context, page
        finally:
            await browser.close()
