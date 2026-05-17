"""Markdown / txt step-file parser.

Format: numbered list (``1. ...``), one step per line. Blank lines and lines
starting with ``#`` are skipped (treated as headings / comments). Any other
non-numbered line is a hard parse error reported with the file path and the
1-based line number.

The list number in the source is decorative — ``parse_steps`` assigns its own
0-based index in source order, matching ``CacheEntry.step_index`` used by the
orchestrator.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

_NUMBERED_LINE = re.compile(r"^\s*\d+\.\s+(.+?)\s*$")


@dataclass(frozen=True)
class Step:
    index: int
    description: str


class ParseError(ValueError):
    """Raised when a step file contains a non-numbered, non-comment, non-blank line."""


def parse_steps(path: Path) -> list[Step]:
    text = Path(path).read_text()
    steps: list[Step] = []
    for lineno, raw in enumerate(text.splitlines(), start=1):
        stripped = raw.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            continue
        match = _NUMBERED_LINE.match(raw)
        if match is None:
            raise ParseError(
                f"{path}:line {lineno}: expected numbered step (e.g. '1. ...'), "
                f"got: {raw!r}"
            )
        steps.append(Step(index=len(steps), description=match.group(1)))
    return steps
