from pathlib import Path

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


async def test_upload_success(tmp_path: Path) -> None:
    tmp_file = tmp_path / "test.txt"
    tmp_file.write_text("hello")

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        try:
            page = await browser.new_page()
            await page.goto("about:blank")
            await page.set_content('<input type="file" id="file">')
            ex = Executor(page)
            result = await ex.upload("#file", str(tmp_file))
            assert result.success is True
            assert result.action == "upload"
            assert result.selector == "#file"
            assert result.error is None
        finally:
            await browser.close()


async def test_upload_missing_selector(tmp_path: Path) -> None:
    tmp_file = tmp_path / "test.txt"
    tmp_file.write_text("hello")

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        try:
            page = await browser.new_page()
            page.set_default_timeout(2000)
            await page.goto("about:blank")
            ex = Executor(page)
            result = await ex.upload("#does-not-exist", str(tmp_file))
            assert result.success is False
            assert result.action == "upload"
            assert result.error is not None
        finally:
            await browser.close()


async def test_check_success() -> None:
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        try:
            page = await browser.new_page()
            await page.goto("about:blank")
            await page.set_content('<input type="checkbox" id="cb">')
            ex = Executor(page)
            result = await ex.check("#cb")
            assert result.success is True
            assert result.action == "check"
            assert result.selector == "#cb"
            assert result.error is None
            checked = await page.evaluate("document.getElementById('cb').checked")
            assert checked is True
        finally:
            await browser.close()


async def test_check_missing_selector() -> None:
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        try:
            page = await browser.new_page()
            page.set_default_timeout(2000)
            await page.goto("about:blank")
            ex = Executor(page)
            result = await ex.check("#does-not-exist")
            assert result.success is False
            assert result.action == "check"
            assert result.error is not None
        finally:
            await browser.close()


async def test_uncheck_success() -> None:
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        try:
            page = await browser.new_page()
            await page.goto("about:blank")
            await page.set_content('<input type="checkbox" id="cb" checked>')
            ex = Executor(page)
            result = await ex.uncheck("#cb")
            assert result.success is True
            assert result.action == "uncheck"
            assert result.selector == "#cb"
            assert result.error is None
            checked = await page.evaluate("document.getElementById('cb').checked")
            assert checked is False
        finally:
            await browser.close()


async def test_uncheck_missing_selector() -> None:
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        try:
            page = await browser.new_page()
            page.set_default_timeout(2000)
            await page.goto("about:blank")
            ex = Executor(page)
            result = await ex.uncheck("#does-not-exist")
            assert result.success is False
            assert result.action == "uncheck"
            assert result.error is not None
        finally:
            await browser.close()


async def test_wait_ms_int() -> None:
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        try:
            page = await browser.new_page()
            await page.goto("about:blank")
            ex = Executor(page)
            result = await ex.wait(50)
            assert result.success is True
            assert result.action == "wait"
            assert result.selector is None
            assert result.duration_ms >= 50
            assert result.error is None
        finally:
            await browser.close()


async def test_wait_ms_string() -> None:
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        try:
            page = await browser.new_page()
            await page.goto("about:blank")
            ex = Executor(page)
            result = await ex.wait("50")
            assert result.success is True
            assert result.action == "wait"
            assert result.selector is None
            assert result.error is None
        finally:
            await browser.close()


async def test_wait_selector_visible() -> None:
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        try:
            page = await browser.new_page()
            await page.goto("about:blank")
            await page.set_content('<button id="btn">OK</button>')
            ex = Executor(page)
            result = await ex.wait("#btn")
            assert result.success is True
            assert result.action == "wait"
            assert result.selector == "#btn"
            assert result.error is None
        finally:
            await browser.close()


async def test_wait_selector_missing() -> None:
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        try:
            page = await browser.new_page()
            page.set_default_timeout(2000)
            await page.goto("about:blank")
            ex = Executor(page)
            result = await ex.wait("#does-not-exist")
            assert result.success is False
            assert result.action == "wait"
            assert result.selector == "#does-not-exist"
            assert result.error is not None
        finally:
            await browser.close()


async def test_scroll_selector() -> None:
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        try:
            page = await browser.new_page()
            await page.goto("about:blank")
            await page.set_content(
                '<div id="target" style="margin-top:2000px">Target</div>'
            )
            ex = Executor(page)
            result = await ex.scroll("#target")
            assert result.success is True
            assert result.action == "scroll"
            assert result.selector == "#target"
            assert result.error is None
        finally:
            await browser.close()


async def test_scroll_missing_selector() -> None:
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        try:
            page = await browser.new_page()
            page.set_default_timeout(2000)
            await page.goto("about:blank")
            ex = Executor(page)
            result = await ex.scroll("#does-not-exist")
            assert result.success is False
            assert result.action == "scroll"
            assert result.error is not None
        finally:
            await browser.close()


async def test_scroll_direction_down() -> None:
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        try:
            page = await browser.new_page()
            await page.goto("about:blank")
            await page.set_content(
                '<div style="height:5000px">tall page</div>'
            )
            ex = Executor(page)
            result = await ex.scroll("down")
            assert result.success is True
            assert result.action == "scroll"
            assert result.selector == "down"
            assert result.duration_ms > 0
            assert result.error is None
        finally:
            await browser.close()


async def test_assert_visible_success() -> None:
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        try:
            page = await browser.new_page()
            await page.goto("about:blank")
            await page.set_content('<button id="btn">OK</button>')
            ex = Executor(page)
            result = await ex.assert_visible("#btn")
            assert result.success is True
            assert result.action == "assert_visible"
            assert result.selector == "#btn"
            assert result.error is None
        finally:
            await browser.close()


async def test_assert_visible_hidden() -> None:
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        try:
            page = await browser.new_page()
            await page.goto("about:blank")
            await page.set_content('<button id="btn" style="display:none">OK</button>')
            ex = Executor(page)
            result = await ex.assert_visible("#btn")
            assert result.success is False
            assert result.action == "assert_visible"
            assert result.selector == "#btn"
            assert result.error is not None
        finally:
            await browser.close()


async def test_assert_visible_missing() -> None:
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        try:
            page = await browser.new_page()
            await page.goto("about:blank")
            ex = Executor(page)
            result = await ex.assert_visible("#does-not-exist")
            assert result.success is False
            assert result.action == "assert_visible"
            assert result.error is not None
        finally:
            await browser.close()


async def test_assert_text_success() -> None:
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        try:
            page = await browser.new_page()
            await page.goto("about:blank")
            await page.set_content('<p id="msg">  Hello world  </p>')
            ex = Executor(page)
            result = await ex.assert_text("#msg", "Hello world")
            assert result.success is True
            assert result.action == "assert_text"
            assert result.selector == "#msg"
            assert result.error is None
        finally:
            await browser.close()


async def test_assert_text_mismatch() -> None:
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        try:
            page = await browser.new_page()
            await page.goto("about:blank")
            await page.set_content('<p id="msg">Actual text</p>')
            ex = Executor(page)
            result = await ex.assert_text("#msg", "Expected text")
            assert result.success is False
            assert result.action == "assert_text"
            assert result.selector == "#msg"
            assert result.error is not None
            assert "Actual text" in result.error
        finally:
            await browser.close()


async def test_assert_text_missing_selector() -> None:
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        try:
            page = await browser.new_page()
            page.set_default_timeout(2000)
            await page.goto("about:blank")
            ex = Executor(page)
            result = await ex.assert_text("#does-not-exist", "anything")
            assert result.success is False
            assert result.action == "assert_text"
            assert result.error is not None
        finally:
            await browser.close()


async def test_assert_url_success() -> None:
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        try:
            page = await browser.new_page()
            await page.goto("about:blank")
            ex = Executor(page)
            result = await ex.assert_url("about:blank")
            assert result.success is True
            assert result.action == "assert_url"
            assert result.selector is None
            assert result.error is None
        finally:
            await browser.close()


async def test_assert_url_substring_match() -> None:
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        try:
            page = await browser.new_page()
            await page.goto("about:blank")
            ex = Executor(page)
            result = await ex.assert_url("blank")
            assert result.success is True
            assert result.action == "assert_url"
            assert result.error is None
        finally:
            await browser.close()


async def test_assert_url_failure() -> None:
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        try:
            page = await browser.new_page()
            await page.goto("about:blank")
            ex = Executor(page)
            result = await ex.assert_url("https://example.com")
            assert result.success is False
            assert result.action == "assert_url"
            assert result.selector is None
            assert result.error is not None
            assert "about:blank" in result.error
        finally:
            await browser.close()
