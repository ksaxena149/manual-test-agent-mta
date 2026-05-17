"""Tests for CacheReader (issue 021)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from mta.cache import CacheEntry, CacheError, CacheReader


# --- Tracer bullet: valid file loads ordered entries ---


def test_load_valid_file_returns_ordered_entries(tmp_path: Path) -> None:
    cache_path = tmp_path / "login.mta.json"
    data = [
        {"step_index": 0, "description": "navigate", "action_type": "navigate",
         "selector": "https://x.com", "semantic_anchor": {}},
        {"step_index": 1, "description": "click login", "action_type": "click",
         "selector": "#login", "semantic_anchor": {"parent_text": "header"}},
    ]
    cache_path.write_text(json.dumps(data))

    entries = CacheReader.load(tmp_path / "login.md")

    assert len(entries) == 2
    assert entries[0].step_index == 0
    assert entries[0].action_type == "navigate"
    assert entries[1].step_index == 1
    assert entries[1].selector == "#login"
    assert entries[1].semantic_anchor == {"parent_text": "header"}


# --- Missing cache file returns empty list ---


def test_load_missing_file_returns_empty(tmp_path: Path) -> None:
    entries = CacheReader.load(tmp_path / "nonexistent.md")
    assert entries == []


# --- Empty JSON array returns empty list ---


def test_load_empty_json_array_returns_empty(tmp_path: Path) -> None:
    (tmp_path / "empty.mta.json").write_text("[]")
    entries = CacheReader.load(tmp_path / "empty.md")
    assert entries == []


# --- Malformed entry raises CacheError naming file and index ---


def test_load_malformed_entry_raises_cache_error(tmp_path: Path) -> None:
    cache_path = tmp_path / "bad.mta.json"
    data = [
        {"step_index": 0, "description": "ok", "action_type": "click",
         "selector": "#x", "semantic_anchor": {}},
        {"step_index": 1, "description": "missing required fields"},  # malformed
    ]
    cache_path.write_text(json.dumps(data))

    with pytest.raises(CacheError) as exc_info:
        CacheReader.load(tmp_path / "bad.md")

    msg = str(exc_info.value)
    assert "bad.mta.json" in msg
    assert "1" in msg  # entry index
