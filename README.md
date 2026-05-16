# Manual Test Agent (MTA)

Manual Test Agent is a hybrid browser testing agent for web applications. It combines deterministic replay with targeted LLM reasoning so that stable steps run cheaply from cache, while ambiguous or drifted steps can fall back to model-guided recovery.

## Why this exists

Most AI browser testing tools lean on vision and LLM reasoning for every step. That works, but it is often too slow, too expensive, and too fragile for repeated test execution.

MTA takes a different approach:

- First run: use an LLM to resolve the test steps and record the successful actions.
- Later runs: replay those actions deterministically with zero LLM calls.
- On drift: re-engage the LLM only for the broken step, heal the cache, and continue.

The goal is to keep the flexibility of AI-assisted browser automation without paying the full AI cost on every run.

## Core ideas

- Hybrid perception: prefer Playwright snapshots and DOM structure, escalate to screenshots only when needed.
- Deterministic replay: store successful actions in a per-test cache for cheap, repeatable reruns.
- Targeted healing: recover only the failed step instead of re-authoring the whole test.
- Terminal-first workflow: start with a practical CLI before expanding into a richer UI.

## Planned feature set

- Python-based test authoring
- Markdown step-file execution
- Playwright browser automation
- Support for Anthropic and OpenRouter-backed models
- Configurable model roles for authoring, healing, and vision
- Per-test JSON cache files stored alongside tests
- Verbose terminal reporting for cache hits, model usage, healing, and failures

## High-level architecture

MTA is organized around a few clear modules:

1. Orchestrator: routes between author, replay, and heal modes
2. Perception arbiter: chooses snapshot-first vs vision-assisted resolution
3. LLM client: wraps model providers behind a shared interface
4. Action executor: exposes a fixed browser action vocabulary
5. Cache and recorder: stores resolved steps for deterministic replay
6. Heal engine: repairs drifted steps and updates cache entries
7. CLI and pytest integration: lets tests run from markdown or Python DSL

## Project status

This repository is currently being prepared as the public home for the project. The implementation is planned around a terminal-first MVP focused on:

- authoring a test
- recording cache entries
- replaying without LLM calls
- healing a failed cached step

## Background

This project is inspired by the browser-agent ideas behind Magnitude, but it is intentionally being reworked with a Python-first stack and a hybrid cache-plus-heal execution model.

The broader goal is to build a browser testing system that is practical for repeated use, easy to explain architecturally, and suitable for an academic major-project presentation.
