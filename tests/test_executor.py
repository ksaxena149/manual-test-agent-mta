from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from playwright.async_api import async_playwright

from mta.executor import DriftError, Executor


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
            page.set_default_timeout(2000)
            await page.goto("about:blank")
            ex = Executor(page, max_retries=0)
            with pytest.raises(DriftError) as exc_info:
                await ex.click("#does-not-exist")
            assert exc_info.value.action == "click"
            assert exc_info.value.selector == "#does-not-exist"
            assert exc_info.value.error
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
            ex = Executor(page, max_retries=0)
            with pytest.raises(DriftError) as exc_info:
                await ex.type("#does-not-exist", "hello")
            assert exc_info.value.action == "type"
            assert exc_info.value.selector == "#does-not-exist"
            assert exc_info.value.error
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
            ex = Executor(page, max_retries=0)
            with pytest.raises(DriftError) as exc_info:
                await ex.select("#fruit", "mango")
            assert exc_info.value.action == "select"
            assert exc_info.value.selector == "#fruit"
            assert exc_info.value.error
        finally:
            await browser.close()


async def test_select_missing_selector() -> None:
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        try:
            page = await browser.new_page()
            page.set_default_timeout(2000)
            await page.goto("about:blank")
            ex = Executor(page, max_retries=0)
            with pytest.raises(DriftError) as exc_info:
                await ex.select("#does-not-exist", "value")
            assert exc_info.value.action == "select"
            assert exc_info.value.selector == "#does-not-exist"
            assert exc_info.value.error
        finally:
            await browser.close()


async def test_navigate_failure() -> None:
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        try:
            page = await browser.new_page()
            ex = Executor(page, max_retries=0)
            with pytest.raises(DriftError) as exc_info:
                await ex.navigate("not-a-valid-url://??")
            assert exc_info.value.action == "navigate"
            assert exc_info.value.selector is None
            assert exc_info.value.error
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
            ex = Executor(page, max_retries=0)
            with pytest.raises(DriftError) as exc_info:
                await ex.upload("#does-not-exist", str(tmp_file))
            assert exc_info.value.action == "upload"
            assert exc_info.value.error
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
            ex = Executor(page, max_retries=0)
            with pytest.raises(DriftError) as exc_info:
                await ex.check("#does-not-exist")
            assert exc_info.value.action == "check"
            assert exc_info.value.error
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
            ex = Executor(page, max_retries=0)
            with pytest.raises(DriftError) as exc_info:
                await ex.uncheck("#does-not-exist")
            assert exc_info.value.action == "uncheck"
            assert exc_info.value.error
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
            ex = Executor(page, max_retries=0)
            with pytest.raises(DriftError) as exc_info:
                await ex.wait("#does-not-exist")
            assert exc_info.value.action == "wait"
            assert exc_info.value.selector == "#does-not-exist"
            assert exc_info.value.error
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
            ex = Executor(page, max_retries=0)
            with pytest.raises(DriftError) as exc_info:
                await ex.scroll("#does-not-exist")
            assert exc_info.value.action == "scroll"
            assert exc_info.value.error
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
            ex = Executor(page, max_retries=0)
            with pytest.raises(DriftError) as exc_info:
                await ex.assert_visible("#btn")
            assert exc_info.value.action == "assert_visible"
            assert exc_info.value.selector == "#btn"
            assert exc_info.value.error
        finally:
            await browser.close()


async def test_assert_visible_missing() -> None:
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        try:
            page = await browser.new_page()
            await page.goto("about:blank")
            ex = Executor(page, max_retries=0)
            with pytest.raises(DriftError) as exc_info:
                await ex.assert_visible("#does-not-exist")
            assert exc_info.value.action == "assert_visible"
            assert exc_info.value.error
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
            ex = Executor(page, max_retries=0)
            with pytest.raises(DriftError) as exc_info:
                await ex.assert_text("#msg", "Expected text")
            assert exc_info.value.action == "assert_text"
            assert exc_info.value.selector == "#msg"
            assert "Actual text" in exc_info.value.error
        finally:
            await browser.close()


async def test_assert_text_missing_selector() -> None:
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        try:
            page = await browser.new_page()
            page.set_default_timeout(2000)
            await page.goto("about:blank")
            ex = Executor(page, max_retries=0)
            with pytest.raises(DriftError) as exc_info:
                await ex.assert_text("#does-not-exist", "anything")
            assert exc_info.value.action == "assert_text"
            assert exc_info.value.error
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
            ex = Executor(page, max_retries=0)
            with pytest.raises(DriftError) as exc_info:
                await ex.assert_url("https://example.com")
            assert exc_info.value.action == "assert_url"
            assert exc_info.value.selector is None
            assert "about:blank" in exc_info.value.error
        finally:
            await browser.close()


# ── retry wrapper unit tests (no Playwright) ──────────────────────────────────


async def test_drift_error_raised_on_exhaustion() -> None:
    page = MagicMock()
    locator = AsyncMock()
    locator.click.side_effect = Exception("element not found")
    page.locator.return_value = locator

    ex = Executor(page, max_retries=2)
    with patch("mta.executor.asyncio.sleep", new_callable=AsyncMock):
        with pytest.raises(DriftError) as exc_info:
            await ex.click("#btn")

    err = exc_info.value
    assert err.action == "click"
    assert err.selector == "#btn"
    assert err.error == "element not found"
    assert err.attempts == 3  # initial + 2 retries


async def test_success_on_retry_reports_attempts() -> None:
    page = MagicMock()
    locator = AsyncMock()
    call_count = 0

    async def flaky_click() -> None:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise Exception("transient")

    locator.click = flaky_click
    page.locator.return_value = locator

    ex = Executor(page, max_retries=2)
    with patch("mta.executor.asyncio.sleep", new_callable=AsyncMock):
        result = await ex.click("#btn")

    assert result.success is True
    assert result.attempts == 2


async def test_success_first_try_attempts_is_one() -> None:
    page = MagicMock()
    locator = AsyncMock()
    locator.click = AsyncMock()  # succeeds immediately
    page.locator.return_value = locator

    ex = Executor(page, max_retries=2)
    result = await ex.click("#btn")

    assert result.success is True
    assert result.attempts == 1


async def test_custom_max_retries_zero_fails_immediately() -> None:
    page = MagicMock()
    locator = AsyncMock()
    locator.click.side_effect = Exception("boom")
    page.locator.return_value = locator

    ex = Executor(page, max_retries=0)
    with pytest.raises(DriftError) as exc_info:
        await ex.click("#btn")

    assert exc_info.value.attempts == 1
