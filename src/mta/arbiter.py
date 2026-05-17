"""Perception Arbiter — action-type heuristic for channel selection.

Channel selection rules (data-driven, extend by editing these tables):

STRUCTURAL_ACTIONS: set of action verbs that always resolve via the
  accessibility-tree snapshot. DOM structure is sufficient to locate these.

VISUAL_KEYWORDS: words in a step description that signal visual/appearance
  assertions. When the action is not structural AND the description contains
  any of these words, the vision channel is used instead.

Default fallback: "snapshot" (structural bias — prefer cheap channel).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Channel = Literal["snapshot", "vision"]

# Action verbs that interact with DOM structure and are reliably resolved
# via the accessibility tree. Extend this set to add new structural actions.
STRUCTURAL_ACTIONS: frozenset[str] = frozenset(
    {
        "click",
        "type",
        "fill",
        "select",
        "check",
        "uncheck",
        "navigate",
        "scroll",
        "wait",
        "upload",
    }
)

# Words that indicate visual / appearance-based assertions. When present in
# the step description and the action is not structural, escalate to vision.
VISUAL_KEYWORDS: frozenset[str] = frozenset(
    {
        "looks",
        "look",
        "appears",
        "appear",
        "color",
        "colour",
        "highlighted",
        "highlight",
        "visible",
        "hidden",
        "style",
        "icon",
        "image",
        "screenshot",
    }
)


@dataclass
class Step:
    action: str
    description: str


class Arbiter:
    """Picks the perception channel for a step using action-type heuristics."""

    def choose_channel(self, step: Step) -> Channel:
        if step.action in STRUCTURAL_ACTIONS:
            return "snapshot"
        words = set(step.description.lower().split())
        if words & VISUAL_KEYWORDS:
            return "vision"
        return "snapshot"
