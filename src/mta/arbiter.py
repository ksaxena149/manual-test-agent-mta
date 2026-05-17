"""Perception Arbiter — action-type heuristic and confidence-based channel selection.

Channel selection rules (data-driven, extend by editing these tables):

STRUCTURAL_ACTIONS: set of action verbs that always resolve via the
  accessibility-tree snapshot. DOM structure is sufficient to locate these.

VISUAL_KEYWORDS: words in a step description that signal visual/appearance
  assertions. When the action is not structural AND the description contains
  any of these words, the vision channel is used instead.

Default fallback: "snapshot" (structural bias — prefer cheap channel).

Confidence scoring thresholds (module-level defaults, injectable via Arbiter):

HIGH_CONFIDENCE_THRESHOLD: top candidate score must exceed this to stay on snapshot.
  Default 0.3 — a single clear token match plus a role hit typically scores ~0.35.

TIE_THRESHOLD: second candidate score must stay below this for the winner to be
  considered unambiguous. Default 0.15 — keeps vision for truly close races.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from mta.snapshot import Snapshot

Channel = Literal["snapshot", "vision"]

# Confidence thresholds for snapshot-vs-vision resolution. See module docstring.
HIGH_CONFIDENCE_THRESHOLD: float = 0.3
TIE_THRESHOLD: float = 0.15

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


@dataclass
class Candidate:
    element: dict[str, str]
    score: float


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


class Arbiter:
    """Picks the perception channel for a step using action-type heuristics."""

    def __init__(
        self,
        high_confidence_threshold: float = HIGH_CONFIDENCE_THRESHOLD,
        tie_threshold: float = TIE_THRESHOLD,
    ) -> None:
        self.high_confidence_threshold = high_confidence_threshold
        self.tie_threshold = tie_threshold

    def score_candidates(self, snapshot: Snapshot, description: str) -> list[Candidate]:
        desc_tokens = set(description.lower().split())
        candidates: list[Candidate] = []
        for el in snapshot.elements:
            name_tokens = set(el["name"].lower().split())
            overlap = _jaccard(desc_tokens, name_tokens)
            role_bonus = 0.1 if el["role"] in desc_tokens else 0.0
            candidates.append(Candidate(element=el, score=overlap + role_bonus))
        candidates.sort(key=lambda c: c.score, reverse=True)
        return candidates

    def resolve_from_snapshot(
        self, snapshot: Snapshot, description: str
    ) -> tuple[Channel, Candidate | None]:
        candidates = self.score_candidates(snapshot, description)
        if not candidates:
            return "vision", None
        top = candidates[0]
        if top.score <= self.high_confidence_threshold:
            return "vision", None
        second_score = candidates[1].score if len(candidates) > 1 else 0.0
        if second_score >= self.tie_threshold:
            return "vision", None
        return "snapshot", top

    def choose_channel(self, step: Step) -> Channel:
        if step.action in STRUCTURAL_ACTIONS:
            return "snapshot"
        words = set(step.description.lower().split())
        if words & VISUAL_KEYWORDS:
            return "vision"
        return "snapshot"
