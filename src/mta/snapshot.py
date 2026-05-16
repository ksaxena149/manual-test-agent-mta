from __future__ import annotations

import re
from dataclasses import dataclass, field

from playwright.async_api import Page

# Lines like: - button "Submit" [level=1]  or  - textbox "Username"
_LINE_RE = re.compile(
    r"^[ \t]*-\s+(?P<role>[a-zA-Z]+(?:[a-zA-Z0-9_-]*))"
    r'(?:\s+"(?P<name>[^"]*)")?'
    r"(?:\s+\[(?P<attrs>[^\]]*)\])?\s*:?\s*$"
)


def _parse_aria_snapshot(text: str) -> list[dict[str, str]]:
    elements: list[dict[str, str]] = []
    for line in text.splitlines():
        m = _LINE_RE.match(line)
        if not m:
            continue
        role = m.group("role").lower()
        if role == "text":
            continue
        name = m.group("name") or ""
        selector = _build_selector(role, name)
        elements.append({"role": role, "name": name, "selector": selector})
    return elements


def _build_selector(role: str, name: str) -> str:
    if name:
        escaped = name.replace('"', '\\"')
        return f'role={role}[name="{escaped}"]'
    return f"role={role}"


@dataclass
class Snapshot:
    elements: list[dict[str, str]] = field(default_factory=list)

    @classmethod
    async def capture(cls, page: Page) -> "Snapshot":
        raw = await page.aria_snapshot()
        elements = _parse_aria_snapshot(raw)
        return cls(elements=elements)

    def to_prompt(self) -> str:
        if not self.elements:
            return "(empty snapshot)"
        lines: list[str] = []
        for el in self.elements:
            name_part = f' "{el["name"]}"' if el["name"] else ""
            lines.append(f'{el["role"]}{name_part}')
        return "\n".join(lines)
