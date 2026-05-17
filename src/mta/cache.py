"""Cache writer for MTA author mode.

CacheEntry schema: { step_index, description, action_type, selector, semantic_anchor }
Cache file path rule: test_path.with_suffix('.mta.json') — same directory, same stem.
Writes are atomic: full rewrite to a temp file, then os.replace.
"""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class CacheEntry:
    step_index: int
    description: str
    action_type: str
    selector: str
    semantic_anchor: dict[str, Any] = field(default_factory=dict)


class CacheWriter:
    """Append cache entries to a per-test JSON file atomically."""

    def __init__(self, test_path: Path) -> None:
        self._cache_path = test_path.with_suffix(".mta.json")
        self._entries: list[dict[str, Any]] = self._load()

    def _load(self) -> list[dict[str, Any]]:
        if self._cache_path.exists():
            return json.loads(self._cache_path.read_text())  # type: ignore[no-any-return]
        return []

    def append(self, entry: CacheEntry) -> None:
        self._entries.append(asdict(entry))
        self._write()

    def _write(self) -> None:
        dir_ = self._cache_path.parent
        fd, tmp = tempfile.mkstemp(dir=dir_, suffix=".tmp")
        try:
            with os.fdopen(fd, "w") as fh:
                json.dump(self._entries, fh, indent=2)
            os.replace(tmp, self._cache_path)
        except Exception:
            os.unlink(tmp)
            raise
