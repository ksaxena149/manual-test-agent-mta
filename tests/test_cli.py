"""CLI tests — top-level argparse and `mta run` end-to-end via subprocess.

Covers issue 025 acceptance criteria:
  - `mta run path/to/steps.md` runs to completion
  - Exit code reflects pass/fail
  - Default output is one line per step: `[index] [mode] [status] description`
  - Integration: pre-baked cache + local HTML page → exit 0

Covers issue 027 acceptance criteria:
  - Mode tag (llm/cache/heal) appears in each step line
  - Mode column is fixed-width (5 chars)
  - Summary footer prints counts per mode
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import logging

from mta.author import Result
from mta.cli import _print_summary, _verbosity_to_level, build_parser
from mta.executor import ActionResult
from mta.orchestrator import RunResult
from mta.parser import Step as ParsedStep
from mta.tools import Action


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _make_result(mode: str = "llm", success: bool = True) -> Result:
    return Result(
        channel="cache",
        action=Action(action_type="click", args={"selector": "#btn"}),
        action_result=ActionResult(
            success=success,
            action="click",
            selector="#btn",
            duration_ms=10.0,
            error=None,
        ),
        mode=mode,
    )


def _make_run_result(
    results: list[Result], mode: str = "replay"
) -> RunResult:
    return RunResult(
        mode=mode,  # type: ignore[arg-type]
        test_path=Path("test.md"),
        step_results=results,
        cache_entries=[],
    )


# ---------------------------------------------------------------------------
# _print_summary unit tests (issue 027)
# ---------------------------------------------------------------------------


def test_print_summary_step_line_contains_mode_tag(capsys: object) -> None:
    parsed = [ParsedStep(index=0, description="click the button")]
    run_result = _make_run_result([_make_result(mode="cache")])
    _print_summary(parsed, run_result)
    out = capsys.readouterr().out  # type: ignore[attr-defined]
    assert "cache" in out
    assert "[0]" in out
    assert "PASS" in out


def test_print_summary_footer_counts_modes(capsys: object) -> None:
    parsed = [ParsedStep(index=i, description=f"step {i}") for i in range(3)]
    results = [
        _make_result(mode="cache"),
        _make_result(mode="cache"),
        _make_result(mode="llm"),
    ]
    run_result = _make_run_result(results)
    _print_summary(parsed, run_result)
    out = capsys.readouterr().out  # type: ignore[attr-defined]
    assert "2 cache" in out
    assert "1 llm" in out
    assert "0 heal" in out


def test_print_summary_no_ansi_when_not_tty(capsys: object) -> None:
    # capsys captures to non-TTY — no ANSI escape codes should appear
    parsed = [ParsedStep(index=0, description="step a")]
    run_result = _make_run_result([_make_result(mode="llm")])
    _print_summary(parsed, run_result)
    out = capsys.readouterr().out  # type: ignore[attr-defined]
    assert "\x1b[" not in out


def test_print_summary_mode_column_is_fixed_width(capsys: object) -> None:
    # "llm" (3 chars) must be padded to 5 so columns align with "cache" (5 chars)
    parsed = [
        ParsedStep(index=0, description="step a"),
        ParsedStep(index=1, description="step b"),
    ]
    results = [_make_result(mode="llm"), _make_result(mode="cache")]
    run_result = _make_run_result(results)
    _print_summary(parsed, run_result)
    out = capsys.readouterr().out  # type: ignore[attr-defined]
    lines = out.splitlines()
    step_lines = [l for l in lines if l.startswith("[")]
    assert "[llm  ]" in step_lines[0]
    assert "[cache]" in step_lines[1]


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


def test_run_replay_output_includes_mode_tag(tmp_path: Path) -> None:
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
    assert "[cache]" in result.stdout


def test_run_replay_summary_footer_matches_per_step_modes(tmp_path: Path) -> None:
    # Fixture has 3 cache entries → footer must report 3 cache, 0 heal, 0 llm.
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
    assert "3 cache" in result.stdout
    assert "0 heal" in result.stdout
    assert "0 llm" in result.stdout


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
