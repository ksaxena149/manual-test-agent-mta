import pytest
from mta.browser import _resolve_headless, launch_browser
from mta.config import BrowserConfig, Config, ModelRoles


def _config(headless: bool | None = None) -> Config:
    return Config(
        default_model="claude-sonnet-4-5",
        model_roles=ModelRoles(),
        browser=BrowserConfig(headless=headless),
    )


# --- headless auto-detection ---


def test_headless_when_display_unset() -> None:
    assert _resolve_headless(_config(), env={}) is True


def test_headless_when_ci_set() -> None:
    assert _resolve_headless(_config(), env={"DISPLAY": ":0", "CI": "true"}) is True


def test_headed_when_display_set_and_no_ci() -> None:
    assert _resolve_headless(_config(), env={"DISPLAY": ":0"}) is False


def test_config_headless_true_overrides() -> None:
    assert _resolve_headless(_config(headless=True), env={"DISPLAY": ":0"}) is True


def test_config_headless_false_overrides() -> None:
    assert _resolve_headless(_config(headless=False), env={"CI": "true"}) is False


# --- integration: context manager lifecycle ---


async def test_launch_browser_navigates_about_blank() -> None:
    async with launch_browser(_config(headless=True)) as (browser, context, page):
        await page.goto("about:blank")
        assert page.url == "about:blank"
