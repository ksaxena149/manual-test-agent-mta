"""Tests for CacheWriter (issue 019)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from mta.cache import CacheEntry, CacheWriter


# --- Tracer bullet: single append creates file with correct structure ---


def test_append_creates_file_with_entry(tmp_path: Path) -> None:
    test_file = tmp_path / "login.md"
    writer = CacheWriter(test_file)

    entry = CacheEntry(
        step_index=0,
        description="Click the login button",
        action_type="click",
        selector="button[type=submit]",
        semantic_anchor={},
    )
    writer.append(entry)

    cache_path = tmp_path / "login.mta.json"
    assert cache_path.exists()
    data = json.loads(cache_path.read_text())
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["step_index"] == 0
    assert data[0]["description"] == "Click the login button"
    assert data[0]["action_type"] == "click"
    assert data[0]["selector"] == "button[type=submit]"
    assert data[0]["semantic_anchor"] == {}


# --- Multiple appends accumulate in order ---


def test_multiple_appends_accumulate_in_order(tmp_path: Path) -> None:
    test_file = tmp_path / "checkout.md"
    writer = CacheWriter(test_file)

    entries = [
        CacheEntry(step_index=i, description=f"step {i}", action_type="click",
                   selector=f"#btn{i}", semantic_anchor={})
        for i in range(3)
    ]
    for e in entries:
        writer.append(e)

    data = json.loads((tmp_path / "checkout.mta.json").read_text())
    assert len(data) == 3
    assert [d["step_index"] for d in data] == [0, 1, 2]
    assert [d["selector"] for d in data] == ["#btn0", "#btn1", "#btn2"]


# --- Cache path derivation ---


def test_cache_path_derived_from_test_path(tmp_path: Path) -> None:
    test_file = tmp_path / "tests" / "login.md"
    test_file.parent.mkdir()
    writer = CacheWriter(test_file)
    entry = CacheEntry(0, "navigate home", "navigate", "https://x.com", {})
    writer.append(entry)

    expected = tmp_path / "tests" / "login.mta.json"
    assert expected.exists()
    # No other .json files alongside
    json_files = list((tmp_path / "tests").glob("*.json"))
    assert len(json_files) == 1


def test_cache_path_for_py_test_file(tmp_path: Path) -> None:
    test_file = tmp_path / "test_login.py"
    writer = CacheWriter(test_file)
    entry = CacheEntry(0, "click login", "click", "#login", {})
    writer.append(entry)

    expected = tmp_path / "test_login.mta.json"
    assert expected.exists()


# --- Atomic write: new writer loads existing entries, no .tmp files left ---


def test_new_writer_loads_existing_entries(tmp_path: Path) -> None:
    """Second CacheWriter on same test_path inherits prior entries."""
    test_file = tmp_path / "flow.md"
    w1 = CacheWriter(test_file)
    w1.append(CacheEntry(0, "step 0", "click", "#a", {}))

    w2 = CacheWriter(test_file)
    w2.append(CacheEntry(1, "step 1", "click", "#b", {}))

    data = json.loads((tmp_path / "flow.mta.json").read_text())
    assert len(data) == 2
    assert data[0]["selector"] == "#a"
    assert data[1]["selector"] == "#b"


def test_no_temp_files_left_after_append(tmp_path: Path) -> None:
    test_file = tmp_path / "smoke.md"
    writer = CacheWriter(test_file)
    writer.append(CacheEntry(0, "x", "click", "#x", {}))
    writer.append(CacheEntry(1, "y", "navigate", "http://y", {}))

    tmp_files = list(tmp_path.glob("*.tmp"))
    assert tmp_files == [], f"leftover temp files: {tmp_files}"
