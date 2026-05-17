"""Vision channel assembler.

Builds a multimodal LLM message (screenshot + DOM excerpt) for steps
that require visual reasoning when the accessibility snapshot is ambiguous.
"""

from __future__ import annotations

import base64
from typing import Any

from playwright.async_api import Page

DOM_EXCERPT_MAX_BYTES: int = 2048


class VisionInput:
    @classmethod
    async def build(
        cls,
        page: Page,
        step: str,
        anchor_selector: str | None = None,
        full_page: bool = False,
        dom_excerpt_max_bytes: int = DOM_EXCERPT_MAX_BYTES,
    ) -> dict[str, Any]:
        screenshot_bytes = await page.screenshot(full_page=full_page)
        screenshot_b64 = base64.standard_b64encode(screenshot_bytes).decode()

        dom_excerpt = await cls._dom_excerpt(page, anchor_selector, dom_excerpt_max_bytes)

        return {
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": screenshot_b64,
                    },
                },
                {
                    "type": "text",
                    "text": f"Step: {step}\n\nDOM excerpt:\n{dom_excerpt}",
                },
            ],
        }

    @staticmethod
    async def _dom_excerpt(
        page: Page,
        anchor_selector: str | None,
        max_bytes: int,
    ) -> str:
        full_html = await page.content()
        full_bytes = full_html.encode()

        if anchor_selector is not None:
            try:
                anchor_html: str = await page.locator(anchor_selector).evaluate(
                    "el => el.outerHTML"
                )
                pos = full_bytes.find(anchor_html.encode())
                if pos >= 0:
                    half = max_bytes // 2
                    start = max(0, pos - half)
                    end = min(len(full_bytes), start + max_bytes)
                    return full_bytes[start:end].decode("utf-8", errors="replace")
            except Exception:
                pass

        return full_bytes[:max_bytes].decode("utf-8", errors="replace")
