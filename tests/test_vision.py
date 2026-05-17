from playwright.async_api import async_playwright

from mta.vision import VisionInput


async def test_build_returns_image_and_text_parts() -> None:
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        try:
            page = await browser.new_page()
            await page.set_content("<button>Submit</button>")
            msg = await VisionInput.build(page, "click the submit button")
            assert msg["role"] == "user"
            content = msg["content"]
            assert len(content) == 2
            types = {block["type"] for block in content}
            assert "image" in types
            assert "text" in types
            img = next(b for b in content if b["type"] == "image")
            assert img["source"]["media_type"] == "image/png"
            assert img["source"]["type"] == "base64"
            assert img["source"]["data"]
        finally:
            await browser.close()
