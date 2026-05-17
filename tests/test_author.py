from unittest.mock import Mock

from playwright.async_api import async_playwright

from mta.arbiter import Arbiter, Step
from mta.author import AuthorMode
from mta.llm.anthropic_client import LLMResponse
from mta.llm.client import LLMClient


async def test_snapshot_direct_skips_llm() -> None:
    """High-confidence arbiter match → snapshot-direct, LLM never called."""
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        try:
            page = await browser.new_page()
            await page.set_content("<button>Submit</button>")

            llm = Mock(spec=LLMClient)
            mode = AuthorMode(llm_client=llm, arbiter=Arbiter())
            step = Step(action="click", description="click the submit button")

            result = await mode.resolve_and_run(page, step)

            assert result.channel == "snapshot-direct"
            llm.complete.assert_not_called()
            assert result.action_result.success is True
        finally:
            await browser.close()


async def test_vision_llm_sends_image_message() -> None:
    """Visual keyword in step → vision-llm; LLM receives multimodal message with image."""
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        try:
            page = await browser.new_page()
            await page.set_content('<div id="box" style="background:red">Mystery box</div>')

            llm = Mock(spec=LLMClient)
            llm.complete.return_value = LLMResponse(
                kind="tool_use",
                tool_name="assert_visible",
                tool_args={"selector": "#box"},
            )
            mode = AuthorMode(llm_client=llm, arbiter=Arbiter())
            # "appears" is a VISUAL_KEYWORD; action is not structural → vision channel
            step = Step(action="assert_visible", description="check the element appears highlighted")

            result = await mode.resolve_and_run(page, step)

            assert result.channel == "vision-llm"
            llm.complete.assert_called_once()
            call_args = llm.complete.call_args
            messages = call_args[0][0]  # first positional arg
            assert len(messages) == 1
            content = messages[0]["content"]
            types = {block["type"] for block in content}
            assert "image" in types
        finally:
            await browser.close()


async def test_snapshot_llm_when_low_confidence() -> None:
    """Low arbiter confidence → snapshot-llm; LLM called with role='author', no image."""
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        try:
            page = await browser.new_page()
            # Ambiguous page: no element name matches the description well
            await page.set_content("<button>Zz99</button>")

            llm = Mock(spec=LLMClient)
            llm.complete.return_value = LLMResponse(
                kind="tool_use",
                tool_name="click",
                tool_args={"selector": "button"},
            )
            mode = AuthorMode(llm_client=llm, arbiter=Arbiter())
            # "click" is structural → heuristic = snapshot, but low token overlap
            step = Step(action="click", description="click the submit button")

            result = await mode.resolve_and_run(page, step)

            assert result.channel == "snapshot-llm"
            llm.complete.assert_called_once()
            call_args = llm.complete.call_args
            assert call_args.kwargs.get("role") == "author"
            # message content must be a plain string (no image block)
            assert isinstance(call_args.args[0][0]["content"], str)
        finally:
            await browser.close()
