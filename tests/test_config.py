import textwrap
from pathlib import Path

import pytest

from mta.config import BrowserConfig, Config, ConfigError, ModelRoles, load_config


def write_toml(tmp_path: Path, content: str) -> Path:
    cfg = tmp_path / "mta.config.toml"
    cfg.write_text(textwrap.dedent(content))
    return tmp_path


# --- tracer bullet ---

def test_valid_full_config(tmp_path: Path) -> None:
    write_toml(tmp_path, """
        max_retries = 3
        heal_mode = "interactive"

        [model]
        default = "claude-sonnet-4-6"

        [model.roles]
        author = "claude-sonnet-4-6"
        vision = "claude-sonnet-4-6"
        heal = "claude-haiku-4-5-20251001"

        [browser]
        headless = true
    """)
    cfg = load_config(tmp_path)

    assert isinstance(cfg, Config)
    assert cfg.default_model == "claude-sonnet-4-6"
    assert cfg.model_roles == ModelRoles(
        author="claude-sonnet-4-6",
        vision="claude-sonnet-4-6",
        heal="claude-haiku-4-5-20251001",
    )
    assert cfg.max_retries == 3
    assert cfg.heal_mode == "interactive"
    assert cfg.browser == BrowserConfig(headless=True)


# --- minimal config uses defaults ---

def test_valid_minimal_config(tmp_path: Path) -> None:
    write_toml(tmp_path, """
        [model]
        default = "claude-haiku-4-5-20251001"
    """)
    cfg = load_config(tmp_path)

    assert cfg.default_model == "claude-haiku-4-5-20251001"
    assert cfg.model_roles == ModelRoles()
    assert cfg.max_retries == 2
    assert cfg.heal_mode == "auto"
    assert cfg.browser == BrowserConfig()


# --- missing file ---

def test_missing_config_file_raises(tmp_path: Path) -> None:
    with pytest.raises(ConfigError) as exc_info:
        load_config(tmp_path)
    assert "mta.config.toml" in str(exc_info.value)


# --- missing required key ---

def test_missing_default_model_raises(tmp_path: Path) -> None:
    write_toml(tmp_path, """
        max_retries = 2
    """)
    with pytest.raises(ConfigError) as exc_info:
        load_config(tmp_path)
    assert "model.default" in str(exc_info.value)


# --- wrong type ---

def test_wrong_type_for_max_retries_raises(tmp_path: Path) -> None:
    write_toml(tmp_path, """
        max_retries = "two"

        [model]
        default = "claude-sonnet-4-6"
    """)
    with pytest.raises(ConfigError) as exc_info:
        load_config(tmp_path)
    assert "max_retries" in str(exc_info.value)


# --- invalid heal_mode ---

def test_invalid_heal_mode_raises(tmp_path: Path) -> None:
    write_toml(tmp_path, """
        heal_mode = "magic"

        [model]
        default = "claude-sonnet-4-6"
    """)
    with pytest.raises(ConfigError) as exc_info:
        load_config(tmp_path)
    assert "heal_mode" in str(exc_info.value)
