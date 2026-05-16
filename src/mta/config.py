import tomllib
from dataclasses import dataclass, field
from pathlib import Path


class ConfigError(Exception):
    pass


@dataclass
class ModelRoles:
    author: str | None = None
    vision: str | None = None
    heal: str | None = None


@dataclass
class BrowserConfig:
    headless: bool | None = None


@dataclass
class Config:
    default_model: str
    model_roles: ModelRoles = field(default_factory=ModelRoles)
    max_retries: int = 2
    heal_mode: str = "auto"
    browser: BrowserConfig = field(default_factory=BrowserConfig)


def load_config(project_root: Path | None = None) -> Config:
    root = project_root or Path.cwd()
    path = root / "mta.config.toml"

    if not path.exists():
        raise ConfigError(f"Config file not found: {path}")

    with open(path, "rb") as f:
        raw = tomllib.load(f)

    model_section = raw.get("model", {})
    if not isinstance(model_section, dict) or "default" not in model_section:
        raise ConfigError("Missing required key: model.default")

    default_model = model_section["default"]
    if not isinstance(default_model, str):
        raise ConfigError("Invalid type for model.default: expected str")

    max_retries = raw.get("max_retries", 2)
    if not isinstance(max_retries, int):
        kind = type(max_retries).__name__
        raise ConfigError(
            f"Invalid type for max_retries: expected int, got {kind}"
        )

    heal_mode = raw.get("heal_mode", "auto")
    if heal_mode not in ("auto", "interactive"):
        raise ConfigError(
            f"Invalid value for heal_mode: {heal_mode!r}"
            " (must be 'auto' or 'interactive')"
        )

    roles_section = model_section.get("roles", {})

    def _str_or_none(key: str) -> str | None:
        val = roles_section.get(key)
        return val if isinstance(val, str) else None

    model_roles = ModelRoles(
        author=_str_or_none("author"),
        vision=_str_or_none("vision"),
        heal=_str_or_none("heal"),
    )

    browser_section = raw.get("browser", {})
    raw_headless = (
        browser_section.get("headless") if isinstance(browser_section, dict) else None
    )
    if raw_headless is not None and not isinstance(raw_headless, bool):
        kind = type(raw_headless).__name__
        raise ConfigError(
            f"Invalid type for browser.headless: expected bool, got {kind}"
        )
    browser = BrowserConfig(
        headless=raw_headless if isinstance(raw_headless, bool) else None
    )

    return Config(
        default_model=default_model,
        model_roles=model_roles,
        max_retries=max_retries,
        heal_mode=heal_mode,
        browser=browser,
    )
