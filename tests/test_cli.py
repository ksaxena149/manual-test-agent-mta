"""CLI tests — top-level argparse and `mta run` end-to-end via subprocess.

Covers issue 025 acceptance criteria:
  - `mta run path/to/steps.md` runs to completion
  - Exit code reflects pass/fail
  - Default output is one line per step: `[index] [status] description`
  - Integration: pre-baked cache + local HTML page → exit 0
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import logging

from mta.cli import _verbosity_to_level, build_parser


# ---------------------------------------------------------------------------
# verbosity level mapping (unit)
# ---------------------------------------------------------------------------


def test_verbosity_zero_maps_to_warning() -> None:
    assert _verbosity_to_level(0) == logging.WARNING


def test_verbosity_one_maps_to_info() -> None:
    assert _verbosity_to_level(1) == logging.INFO


def test_verbosity_two_maps_to_debug() -> None:
    assert _verbosity_to_level(2) == logging.DEBUG


# ---------------------------------------------------------------------------
# argparse layer (unit)
# ---------------------------------------------------------------------------


def test_version_flag_exits_zero_and_prints_version() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "mta", "--version"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert result.stdout.strip() != ""


def test_version_string_matches_package() -> None:
    import mta

    result = subprocess.run(
        [sys.executable, "-m", "mta", "--version"],
        capture_output=True,
        text=True,
    )
    assert mta.__version__ in result.stdout or mta.__version__ in result.stderr


def test_run_subcommand_parses_v_flag() -> None:
    args = build_parser().parse_args(["run", "-v", "f.md"])
    assert args.verbose == 1


def test_run_subcommand_parses_vv_flag() -> None:
    args = build_parser().parse_args(["run", "-vv", "f.md"])
    assert args.verbose == 2


def test_run_subcommand_parses_file_argument() -> None:
    args = build_parser().parse_args(["run", "steps.md"])
    assert args.command == "run"
    assert args.file == Path("steps.md")


def test_run_subcommand_requires_file_argument() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "mta", "run"],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0


def test_run_subcommand_missing_file_exits_nonzero(tmp_path: Path) -> None:
    result = subprocess.run(
        [sys.executable, "-m", "mta", "run", str(tmp_path / "nope.md")],
        capture_output=True,
        text=True,
        cwd=tmp_path,
    )
    assert result.returncode != 0
    assert "not found" in result.stderr.lower() or "no such" in result.stderr.lower()


# ---------------------------------------------------------------------------
# end-to-end replay (integration)
# ---------------------------------------------------------------------------


def _write_fixture_project(tmp_path: Path) -> tuple[Path, Path]:
    """Create a minimal MTA project: config, step file, pre-baked cache, HTML page.

    Returns (cwd, test_file). Cache is keyed off test_file.stem so replay runs.
    """
    page_path = tmp_path / "page.html"
    page_path.write_text(
        "<html><body>"
        "<button id='submit'>Submit</button>"
        "<button id='next'>Next</button>"
        "</body></html>"
    )

    config_path = tmp_path / "mta.config.toml"
    config_path.write_text(
        "[model]\n"
        'default = "claude-sonnet-4-6"\n'
        "[browser]\n"
        "headless = true\n"
    )

    test_path = tmp_path / "test_demo.md"
    test_path.write_text(
        "1. go to page\n"
        "2. click submit\n"
        "3. click next\n"
    )

    page_url = f"file://{page_path}"
    cache_path = tmp_path / "test_demo.mta.json"
    cache_path.write_text(
        json.dumps(
            [
                {
                    "step_index": 0,
                    "description": "go to page",
                    "action_type": "navigate",
                    "selector": "",
                    "semantic_anchor": {},
                    "args": {"url": page_url},
                },
                {
                    "step_index": 1,
                    "description": "click submit",
                    "action_type": "click",
                    "selector": "#submit",
                    "semantic_anchor": {},
                    "args": {"selector": "#submit"},
                },
                {
                    "step_index": 2,
                    "description": "click next",
                    "action_type": "click",
                    "selector": "#next",
                    "semantic_anchor": {},
                    "args": {"selector": "#next"},
                },
            ]
        )
    )

    return tmp_path, test_path


def test_run_replay_with_baked_cache_exits_zero(tmp_path: Path) -> None:
    cwd, test_path = _write_fixture_project(tmp_path)

    result = subprocess.run(
        [sys.executable, "-m", "mta", "run", str(test_path)],
        capture_output=True,
        text=True,
        cwd=cwd,
        timeout=60,
    )

    assert result.returncode == 0, (
        f"stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    # One line per step in the cache.
    assert "[0]" in result.stdout
    assert "[1]" in result.stdout
    assert "[2]" in result.stdout
    assert "PASS" in result.stdout
    assert "go to page" in result.stdout
    assert "click submit" in result.stdout


def test_vv_run_emits_debug_to_stderr(tmp_path: Path) -> None:
    cwd, test_path = _write_fixture_project(tmp_path)

    result = subprocess.run(
        [sys.executable, "-m", "mta", "run", "-vv", str(test_path)],
        capture_output=True,
        text=True,
        cwd=cwd,
        timeout=60,
    )

    assert result.returncode == 0, (
        f"stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    assert "DEBUG" in result.stderr


def test_run_missing_config_errors(tmp_path: Path) -> None:
    test_path = tmp_path / "steps.md"
    test_path.write_text("1. click submit\n")

    result = subprocess.run(
        [sys.executable, "-m", "mta", "run", str(test_path)],
        capture_output=True,
        text=True,
        cwd=tmp_path,
    )

    assert result.returncode != 0
    assert "config" in result.stderr.lower() or "mta.config.toml" in result.stderr
