from playwright.async_api import async_playwright

from mta.executor import Executor


async def test_navigate_success() -> None:
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        try:
            page = await browser.new_page()
            ex = Executor(page)
            result = await ex.navigate("about:blank")
            assert result.success is True
            assert result.action == "navigate"
            assert result.selector is None
            assert result.duration_ms > 0
            assert result.error is None
        finally:
            await browser.close()


async def test_click_success() -> None:
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        try:
            page = await browser.new_page()
            await page.goto("about:blank")
            await page.set_content("<button id='btn'>Click me</button>")
            ex = Executor(page)
            result = await ex.click("#btn")
            assert result.success is True
            assert result.action == "click"
            assert result.selector == "#btn"
            assert result.duration_ms > 0
            assert result.error is None
        finally:
            await browser.close()


async def test_click_missing_selector() -> None:
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        try:
            page = await browser.new_page()
            page.set_default_timeout(2000)  # keep test fast; 30 s default is too slow
            await page.goto("about:blank")
            ex = Executor(page)
            result = await ex.click("#does-not-exist")
            assert result.success is False
            assert result.action == "click"
            assert result.selector == "#does-not-exist"
            assert result.error is not None
        finally:
            await browser.close()


async def test_result_shape() -> None:
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        try:
            page = await browser.new_page()
            ex = Executor(page)
            result = await ex.navigate("about:blank")
            assert isinstance(result.success, bool)
            assert isinstance(result.action, str)
            assert result.selector is None
            assert isinstance(result.duration_ms, float)
            assert result.error is None
        finally:
            await browser.close()


async def test_type_success() -> None:
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        try:
            page = await browser.new_page()
            await page.goto("about:blank")
            await page.set_content('<input id="name" type="text">')
            ex = Executor(page)
            result = await ex.type("#name", "hello")
            assert result.success is True
            assert result.action == "type"
            assert result.selector == "#name"
            assert result.duration_ms > 0
            assert result.error is None
            value = await page.evaluate("document.getElementById('name').value")
            assert value == "hello"
        finally:
            await browser.close()


async def test_type_missing_selector() -> None:
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        try:
            page = await browser.new_page()
            page.set_default_timeout(2000)
            await page.goto("about:blank")
            ex = Executor(page)
            result = await ex.type("#does-not-exist", "hello")
            assert result.success is False
            assert result.action == "type"
            assert result.selector == "#does-not-exist"
            assert result.error is not None
        finally:
            await browser.close()


async def test_select_success() -> None:
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        try:
            page = await browser.new_page()
            await page.goto("about:blank")
            await page.set_content(
                '<select id="fruit"><option value="apple">Apple</option>'
                '<option value="banana">Banana</option></select>'
            )
            ex = Executor(page)
            result = await ex.select("#fruit", "banana")
            assert result.success is True
            assert result.action == "select"
            assert result.selector == "#fruit"
            assert result.duration_ms > 0
            assert result.error is None
            value = await page.evaluate("document.getElementById('fruit').value")
            assert value == "banana"
        finally:
            await browser.close()


async def test_select_invalid_option() -> None:
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        try:
            page = await browser.new_page()
            page.set_default_timeout(2000)
            await page.goto("about:blank")
            await page.set_content(
                '<select id="fruit"><option value="apple">Apple</option></select>'
            )
            ex = Executor(page)
            result = await ex.select("#fruit", "mango")
            assert result.success is False
            assert result.action == "select"
            assert result.selector == "#fruit"
            assert result.error is not None
        finally:
            await browser.close()


async def test_select_missing_selector() -> None:
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        try:
            page = await browser.new_page()
            page.set_default_timeout(2000)
            await page.goto("about:blank")
            ex = Executor(page)
            result = await ex.select("#does-not-exist", "value")
            assert result.success is False
            assert result.action == "select"
            assert result.selector == "#does-not-exist"
            assert result.error is not None
        finally:
            await browser.close()


async def test_navigate_failure() -> None:
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        try:
            page = await browser.new_page()
            ex = Executor(page)
            result = await ex.navigate("not-a-valid-url://??")
            assert result.success is False
            assert result.action == "navigate"
            assert result.selector is None
            assert result.error is not None
        finally:
            await browser.close()
