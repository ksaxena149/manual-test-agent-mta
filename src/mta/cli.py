"""CLI entrypoint for MTA.

Subcommands:
  mta --version          show version
  mta run <file>         parse a numbered step file and run it through the
                         orchestrator. Author mode if no cache; replay mode if
                         cache file exists. Prints one line per step in the
                         form `[index] [status] description` and exits 0 on
                         full success, non-zero on any step failure.

Parser steps carry no action verb — the LLM decides the action in author mode,
and replay reads it from the cache. We translate parser.Step → arbiter.Step
with `action=""` so AuthorMode's DIRECT_ACTIONS short-circuit is skipped and
the LLM path runs.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path

from mta import __version__
from mta.arbiter import Arbiter
from mta.arbiter import Step as ArbiterStep
from mta.author import AuthorMode
from mta.browser import launch_browser
from mta.config import Config, ConfigError, load_config
from mta.executor import DriftError
from mta.llm.client import LLMClient
from mta.orchestrator import Orchestrator, RunResult
from mta.parser import ParseError, Step as ParsedStep, parse_steps
from mta.replay import ReplayMode


def _verbosity_to_level(verbosity: int) -> int:
    if verbosity == 0:
        return logging.WARNING
    if verbosity == 1:
        return logging.INFO
    return logging.DEBUG


def _configure_logging(verbosity: int) -> None:
    level = _verbosity_to_level(verbosity)
    logger = logging.getLogger("mta")
    logger.setLevel(level)
    handler = logging.StreamHandler(sys.stderr)
    handler.setLevel(level)
    handler.setFormatter(logging.Formatter("%(levelname)s %(name)s %(message)s"))
    logger.addHandler(handler)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="mta", description="Manual Test Agent")
    parser.add_argument("--version", action="version", version=f"mta {__version__}")
    sub = parser.add_subparsers(dest="command")
    run_p = sub.add_parser("run", help="Run a markdown/txt step file")
    run_p.add_argument("file", type=Path, help="Path to numbered step file")
    run_p.add_argument(
        "-v",
        dest="verbose",
        action="count",
        default=0,
        help="Increase verbosity (-v INFO, -vv DEBUG)",
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "run":
        sys.exit(_run(args.file, getattr(args, "verbose", 0)))
    parser.print_help()


def _run(test_path: Path, verbosity: int = 0) -> int:
    _configure_logging(verbosity)
    if not test_path.exists():
        print(f"error: file not found: {test_path}", file=sys.stderr)
        return 2

    try:
        config = load_config()
    except ConfigError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    try:
        parsed = parse_steps(test_path)
    except ParseError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    steps = [ArbiterStep(action="", description=s.description) for s in parsed]
    return asyncio.run(_async_run(config, test_path, parsed, steps))


async def _async_run(
    config: Config,
    test_path: Path,
    parsed: list[ParsedStep],
    steps: list[ArbiterStep],
) -> int:
    async with launch_browser(config) as (_browser, _ctx, page):
        llm = LLMClient(config)
        author = AuthorMode(llm, Arbiter())
        replay = ReplayMode(llm, max_retries=config.max_retries)
        orch = Orchestrator(author_mode=author, page=page, replay_mode=replay)
        try:
            result = await orch.run(test_path, steps)
        except DriftError as exc:
            print(f"error: drift during replay: {exc}", file=sys.stderr)
            return 1
    return _print_summary(parsed, result)


def _print_summary(parsed: list[ParsedStep], result: RunResult) -> int:
    descriptions: dict[int, str] = {s.index: s.description for s in parsed}
    # In replay mode the cache may carry steps the parser file doesn't enumerate
    # (e.g. an implicit navigate). Prefer the cache entry's recorded description
    # so the printed line still corresponds to the action that ran.
    for entry in result.cache_entries:
        descriptions.setdefault(entry.step_index, entry.description)

    failed = False
    for i, sr in enumerate(result.step_results):
        ok = sr.action_result.success
        status = "PASS" if ok else "FAIL"
        desc = descriptions.get(i, sr.action.action_type)
        print(f"[{i}] {status} {desc}")
        if not ok:
            failed = True
    return 1 if failed else 0
