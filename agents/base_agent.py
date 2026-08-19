"""
agents/base_agent.py
=====================
Common functionality shared by every agent:

  - Structured logging under the agent's own name.
  - Access to the shared SQLite-backed memory.
  - Loading prompt templates from `prompts/`.
  - A `call_llm_json` helper that calls the LLM (if configured), parses its
    JSON response defensively, and falls back to `None` on any failure so
    each agent's heuristic fallback logic can take over — keeping the whole
    pipeline resilient to LLM outages, malformed output, or missing API keys.
  - A generic `retry` decorator/helper for transient operations.
"""

from __future__ import annotations

import functools
import json
import re
import time
from pathlib import Path
from typing import Any, Callable, Optional, TypeVar

from config import settings
from llm_client import LLMUnavailableError, llm_client
from logging_setup import get_logger
from memory.shared_memory import shared_memory

T = TypeVar("T")

_JSON_BLOCK_RE = re.compile(r"\{.*\}", re.DOTALL)


def retry(max_attempts: int = 3, backoff_seconds: float = 1.0):
    """Simple synchronous retry decorator with linear backoff."""

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            last_exc: Optional[Exception] = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as exc:  # noqa: BLE001
                    last_exc = exc
                    if attempt < max_attempts:
                        time.sleep(backoff_seconds * attempt)
            raise last_exc  # type: ignore[misc]

        return wrapper

    return decorator


class BaseAgent:
    """Base class providing shared plumbing for all pipeline agents."""

    #: subclasses override this with their own prompt filename (in prompts/)
    prompt_file: Optional[str] = None

    def __init__(self, name: str) -> None:
        self.name = name
        self.logger = get_logger(f"agents.{name}")
        self.memory = shared_memory
        self._prompt_template: Optional[str] = None

    # ------------------------------------------------------------------
    # Prompt handling
    # ------------------------------------------------------------------
    def load_prompt(self) -> str:
        """Load (and cache) this agent's prompt template from disk."""
        if self._prompt_template is not None:
            return self._prompt_template
        if not self.prompt_file:
            raise ValueError(f"{self.name} has no prompt_file configured")
        path: Path = settings.prompts_dir / self.prompt_file
        try:
            self._prompt_template = path.read_text(encoding="utf-8")
        except OSError as exc:
            self.logger.error("Failed to load prompt %s: %s", path, exc)
            raise
        return self._prompt_template

    # ------------------------------------------------------------------
    # LLM helper with JSON parsing + graceful fallback
    # ------------------------------------------------------------------
    def call_llm_json(self, system_prompt: str, user_prompt: str) -> Optional[dict[str, Any]]:
        """
        Call the LLM and attempt to parse a JSON object out of its response.

        Returns None (never raises) if:
          - No LLM provider is configured ("none" mode)
          - The LLM call ultimately fails after retries
          - The response cannot be parsed as JSON

        Callers are expected to fall back to heuristic logic when None is
        returned, which is the core resilience pattern of this system.
        """
        if not llm_client.is_available():
            return None
        try:
            raw = llm_client.generate(system_prompt, user_prompt)
        except LLMUnavailableError as exc:
            self.logger.warning("%s: LLM unavailable, falling back to heuristics (%s)", self.name, exc)
            return None

        if not raw:
            return None

        match = _JSON_BLOCK_RE.search(raw)
        candidate = match.group(0) if match else raw
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            self.logger.warning("%s: could not parse LLM output as JSON: %r", self.name, raw[:200])
            return None

    # ------------------------------------------------------------------
    # Event logging convenience
    # ------------------------------------------------------------------
    def log_event(self, event_type: str, payload: dict[str, Any]) -> None:
        self.memory.log_event(self.name, event_type, payload)
