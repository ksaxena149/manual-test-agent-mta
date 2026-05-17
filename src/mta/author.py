"""Author mode — end-to-end step resolution without a pre-existing cache.

Routing rules:
  snapshot-direct : arbiter has high-confidence winner AND action only needs a
                    selector (DIRECT_ACTIONS). No LLM call.
  snapshot-llm    : arbiter chose snapshot channel but confidence is low, or
                    the action needs args beyond a selector. LLM called with
                    accessibility-snapshot text; role="author".
  vision-llm      : heuristic picked vision channel (visual keyword or non-
                    structural action). LLM called with screenshot + DOM excerpt;
                    role="vision".

DriftError from the executor propagates up — AuthorMode does not catch it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from playwright.async_api import Page

from mta.arbiter import Arbiter, Step
from mta.executor import ActionResult, Executor
from mta.llm.client import LLMClient
from mta.snapshot import Snapshot
from mta.tools import ACTION_TOOLS, Action, parse_tool_call
from mta.vision import VisionInput

# Actions where a selector alone is sufficient — no extra LLM-derived args needed.
# For any other action type (type, select, upload, etc.) the LLM must supply the
# additional arguments even when the arbiter found a confident candidate.
DIRECT_ACTIONS: frozenset[str] = frozenset({"click", "check", "uncheck", "assert_visible"})


@dataclass
class Result:
    channel: str  # "snapshot-direct" | "snapshot-llm" | "vision-llm"
    action: Action
    action_result: ActionResult


async def _dispatch(executor: Executor, action: Action) -> ActionResult:
    a: dict[str, Any] = action.args
    match action.action_type:
        case "navigate":
            return await executor.navigate(a["url"])
        case "click":
            return await executor.click(a["selector"])
        case "type":
            return await executor.type(a["selector"], a["text"])
        case "select":
            return await executor.select(a["selector"], a["value"])
        case "scroll":
            return await executor.scroll(a["selector_or_direction"])
        case "wait":
            return await executor.wait(a["ms_or_selector"])
        case "check":
            return await executor.check(a["selector"])
        case "uncheck":
            return await executor.uncheck(a["selector"])
        case "upload":
            return await executor.upload(a["selector"], a["path"])
        case "assert_visible":
            return await executor.assert_visible(a["selector"])
        case "assert_text":
            return await executor.assert_text(a["selector"], a["expected"])
        case "assert_url":
            return await executor.assert_url(a["expected"])
        case _:
            raise ValueError(f"unknown action_type: {action.action_type!r}")


class AuthorMode:
    def __init__(self, llm_client: LLMClient, arbiter: Arbiter) -> None:
        self._llm = llm_client
        self._arbiter = arbiter

    async def resolve_and_run(self, page: Page, step: Step) -> Result:
        executor = Executor(page, max_retries=0)
        snapshot = await Snapshot.capture(page)
        heuristic_channel = self._arbiter.choose_channel(step)

        if heuristic_channel == "snapshot":
            resolved, candidate = self._arbiter.resolve_from_snapshot(
                snapshot, step.description
            )
            if resolved == "snapshot" and candidate is not None and step.action in DIRECT_ACTIONS:
                action = Action(
                    action_type=step.action,
                    args={"selector": candidate.element["selector"]},
                )
                action_result = await _dispatch(executor, action)
                return Result(channel="snapshot-direct", action=action, action_result=action_result)

            # Low-confidence or action needs extra args → ask the LLM
            msg: dict[str, Any] = {
                "role": "user",
                "content": (
                    f"Step: {step.description}\n\nAccessibility snapshot:\n{snapshot.to_prompt()}"
                ),
            }
            response = self._llm.complete([msg], ACTION_TOOLS, role="author")
            action = parse_tool_call(response)
            action_result = await _dispatch(executor, action)
            return Result(channel="snapshot-llm", action=action, action_result=action_result)

        # Vision channel
        vision_msg = await VisionInput.build(page, step.description)
        response = self._llm.complete([vision_msg], ACTION_TOOLS, role="vision")
        action = parse_tool_call(response)
        action_result = await _dispatch(executor, action)
        return Result(channel="vision-llm", action=action, action_result=action_result)
