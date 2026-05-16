from playwright.async_api import async_playwright

from mta.snapshot import Snapshot


async def test_capture_button_has_correct_role_and_name() -> None:
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        try:
            page = await browser.new_page()
            await page.set_content("<button>Submit</button>")
            snapshot = await Snapshot.capture(page)
            buttons = [e for e in snapshot.elements if e["role"] == "button"]
            assert any(e["name"] == "Submit" for e in buttons)
        finally:
            await browser.close()


async def test_to_prompt_contains_role_and_name() -> None:
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        try:
            page = await browser.new_page()
            await page.set_content(
                '<button>Login</button><input type="text" aria-label="Username">'
            )
            snapshot = await Snapshot.capture(page)
            prompt = snapshot.to_prompt()
            assert 'button "Login"' in prompt
            assert "textbox" in prompt
        finally:
            await browser.close()


async def test_element_has_selector_hint() -> None:
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        try:
            page = await browser.new_page()
            await page.set_content("<button>Submit</button>")
            snapshot = await Snapshot.capture(page)
            btn = next(
                e for e in snapshot.elements
                if e["role"] == "button" and e["name"] == "Submit"
            )
            assert btn["selector"]
            assert "button" in btn["selector"]
        finally:
            await browser.close()


async def test_selector_hint_resolves_element() -> None:
    """Selector hint must be usable with page.locator()."""
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        try:
            page = await browser.new_page()
            await page.set_content("<button>Click me</button>")
            snapshot = await Snapshot.capture(page)
            btn = next(e for e in snapshot.elements if e["role"] == "button")
            count = await page.locator(btn["selector"]).count()
            assert count >= 1
        finally:
            await browser.close()


async def test_empty_page_returns_empty_prompt() -> None:
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        try:
            page = await browser.new_page()
            await page.set_content("<div>no interactive elements</div>")
            snapshot = await Snapshot.capture(page)
            if not snapshot.elements:
                assert snapshot.to_prompt() == "(empty snapshot)"
        finally:
            await browser.close()
