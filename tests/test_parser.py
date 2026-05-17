from __future__ import annotations

from pathlib import Path

import pytest

from mta.parser import ParseError, Step, parse_steps


def _write(tmp_path: Path, name: str, body: str) -> Path:
    p = tmp_path / name
    p.write_text(body)
    return p


def test_clean_numbered_list(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        "steps.md",
        "1. go to login page\n2. fill in username\n3. click submit\n",
    )

    steps = parse_steps(path)

    assert steps == [
        Step(index=0, description="go to login page"),
        Step(index=1, description="fill in username"),
        Step(index=2, description="click submit"),
    ]


def test_skips_headings_and_blank_lines(tmp_path: Path) -> None:
    body = (
        "# Login flow\n"
        "\n"
        "1. open the login page\n"
        "\n"
        "## Step group\n"
        "2. enter creds\n"
        "\n"
        "3. submit\n"
    )
    path = _write(tmp_path, "steps.md", body)

    steps = parse_steps(path)

    assert [s.description for s in steps] == [
        "open the login page",
        "enter creds",
        "submit",
    ]
    assert [s.index for s in steps] == [0, 1, 2]


def test_malformed_line_raises_with_line_number(tmp_path: Path) -> None:
    body = "1. open page\nthis is not numbered\n2. click submit\n"
    path = _write(tmp_path, "steps.md", body)

    with pytest.raises(ParseError) as exc:
        parse_steps(path)

    msg = str(exc.value)
    assert "line 2" in msg
    assert str(path) in msg


def test_empty_file_returns_empty_list(tmp_path: Path) -> None:
    path = _write(tmp_path, "steps.md", "")

    assert parse_steps(path) == []


def test_whitespace_only_file_returns_empty_list(tmp_path: Path) -> None:
    path = _write(tmp_path, "steps.md", "\n\n   \n")

    assert parse_steps(path) == []


def test_txt_extension_supported(tmp_path: Path) -> None:
    path = _write(tmp_path, "steps.txt", "1. only step\n")

    assert parse_steps(path) == [Step(index=0, description="only step")]


def test_indices_are_zero_based_regardless_of_numbering(tmp_path: Path) -> None:
    # The list number in the file is decorative — the parser assigns its own
    # 0-based index from the order seen. A file numbered 5, 6, 7 still yields 0, 1, 2.
    path = _write(tmp_path, "steps.md", "5. first\n6. second\n7. third\n")

    steps = parse_steps(path)

    assert [s.index for s in steps] == [0, 1, 2]
    assert [s.description for s in steps] == ["first", "second", "third"]
