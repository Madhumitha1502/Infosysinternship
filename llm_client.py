"""
llm_client.py
=============
Thin, provider-agnostic LLM client used by every agent.

Supports:
  - OpenAI / any OpenAI-compatible endpoint (via `langchain_openai.ChatOpenAI`)
  - Ollama local models (via `langchain_community.chat_models.ChatOllama` /
    `langchain_ollama`)
  - "none" provider: no network calls are made at all. Agents fall back to
    deterministic heuristics. This lets the entire pipeline run end-to-end
    in CI/tests/demo environments with zero external dependencies or API keys.

A synchronous retry-with-backoff wrapper is provided so transient network
failures against the LLM provider don't crash the whole pipeline run.
"""

from __future__ import annotations

import time
from typing import Optional

from config import settings
from logging_setup import get_logger

logger = get_logger(__name__)


class LLMUnavailableError(RuntimeError):
    """Raised when the configured LLM provider cannot be reached."""


class LLMClient:
    """Provider-agnostic wrapper around a LangChain chat model."""

    def __init__(self) -> None:
        self.provider = settings.llm_provider
        self._model = None
        if self.provider == "openai":
            self._model = self._build_openai_model()
        elif self.provider == "ollama":
            self._model = self._build_ollama_model()
        elif self.provider == "none":
            logger.info("LLM provider set to 'none' — running in heuristic-only mode.")
        else:
            logger.warning("Unknown LLM provider '%s', defaulting to heuristic-only mode.", self.provider)
            self.provider = "none"

    # ------------------------------------------------------------------
    # Model builders
    # ------------------------------------------------------------------
    def _build_openai_model(self):
        try:
            from langchain_openai import ChatOpenAI

            if not settings.openai_api_key:
                logger.warning("OPENAI_API_KEY not set; falling back to heuristic-only mode.")
                self.provider = "none"
                return None

            return ChatOpenAI(
                model=settings.openai_model,
                api_key=settings.openai_api_key,
                base_url=settings.openai_base_url,
                temperature=settings.llm_temperature,
                max_tokens=settings.llm_max_tokens,
                timeout=settings.llm_timeout_seconds,
            )
        except ImportError:
            logger.warning("langchain_openai not installed; falling back to heuristic-only mode.")
            self.provider = "none"
            return None

    def _build_ollama_model(self):
        try:
            from langchain_ollama import ChatOllama

            return ChatOllama(
                model=settings.ollama_model,
                base_url=settings.ollama_base_url,
                temperature=settings.llm_temperature,
            )
        except ImportError:
            logger.warning("langchain_ollama not installed; falling back to heuristic-only mode.")
            self.provider = "none"
            return None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def is_available(self) -> bool:
        return self.provider != "none" and self._model is not None

    def generate(self, system_prompt: str, user_prompt: str) -> Optional[str]:
        """
        Generate a completion. Returns None if the LLM is unavailable so
        callers can gracefully fall back to heuristics — never raises for
        "no provider configured", only for provider errors after retries
        are exhausted (via LLMUnavailableError).
        """
        if not self.is_available():
            return None

        from langchain_core.messages import HumanMessage, SystemMessage

        messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]

        last_error: Optional[Exception] = None
        for attempt in range(1, settings.llm_max_retries + 1):
            try:
                response = self._model.invoke(messages)
                return response.content
            except Exception as exc:  # noqa: BLE001 - broad by design, provider-agnostic
                last_error = exc
                wait = settings.llm_retry_backoff_seconds * attempt
                logger.warning(
                    "LLM call failed (attempt %d/%d): %s. Retrying in %.1fs",
                    attempt, settings.llm_max_retries, exc, wait,
                )
                time.sleep(wait)

        logger.error("LLM provider exhausted retries: %s", last_error)
        raise LLMUnavailableError(str(last_error))


# Process-wide singleton
llm_client = LLMClient()
