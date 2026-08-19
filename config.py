"""
config.py
=========
Centralized configuration management for the AI Cyber Attack Response system.

All runtime configuration is loaded from environment variables (via a `.env`
file in development, or real environment variables in production/Docker).
Using `pydantic-settings` gives us validated, typed configuration with sane
defaults so the system can run out-of-the-box in "offline/heuristic" mode
even without an LLM API key configured.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Load .env as early as possible so BaseSettings can see the values.
load_dotenv(override=False)

BASE_DIR = Path(__file__).resolve().parent


class Settings(BaseSettings):
    """Application-wide configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ------------------------------------------------------------------
    # General
    # ------------------------------------------------------------------
    app_name: str = "AI Cyber Attack Response Coordinator"
    environment: Literal["development", "staging", "production"] = "development"
    log_level: str = "INFO"

    # ------------------------------------------------------------------
    # LLM Provider configuration
    # ------------------------------------------------------------------
    # provider: "openai" | "ollama" | "none" (heuristic-only, no LLM calls)
    llm_provider: Literal["openai", "ollama", "none"] = Field(default="none")

    openai_api_key: str = Field(default="")
    openai_base_url: str = Field(default="https://api.openai.com/v1")
    openai_model: str = Field(default="gpt-4o-mini")

    ollama_base_url: str = Field(default="http://localhost:11434")
    ollama_model: str = Field(default="llama3.1")

    llm_temperature: float = Field(default=0.2)
    llm_max_tokens: int = Field(default=800)
    llm_timeout_seconds: int = Field(default=30)
    llm_max_retries: int = Field(default=3)
    llm_retry_backoff_seconds: float = Field(default=1.5)

    # ------------------------------------------------------------------
    # Paths
    # ------------------------------------------------------------------
    base_dir: Path = BASE_DIR
    data_dir: Path = BASE_DIR / "data"
    reports_dir: Path = BASE_DIR / "reports"
    logs_dir: Path = BASE_DIR / "logs"
    prompts_dir: Path = BASE_DIR / "prompts"

    network_logs_csv: Path = BASE_DIR / "data" / "network_logs.csv"
    detected_logs_csv: Path = BASE_DIR / "data" / "detected_logs.csv"
    analyzed_logs_csv: Path = BASE_DIR / "data" / "analyzed_logs.csv"
    coordinated_tasks_csv: Path = BASE_DIR / "data" / "coordinated_tasks.csv"
    decision_output_csv: Path = BASE_DIR / "data" / "decision_output.csv"
    response_output_csv: Path = BASE_DIR / "data" / "response_output.csv"
    alert_output_csv: Path = BASE_DIR / "data" / "alert_output.csv"
    final_report_csv: Path = BASE_DIR / "data" / "final_report.csv"

    incident_report_md: Path = BASE_DIR / "reports" / "incident_report.md"
    incident_report_json: Path = BASE_DIR / "reports" / "incident_report.json"

    sqlite_path: Path = BASE_DIR / "memory" / "shared_memory.db"

    # ------------------------------------------------------------------
    # Alerting
    # ------------------------------------------------------------------
    smtp_host: str = Field(default="localhost")
    smtp_port: int = Field(default=25)
    smtp_username: str = Field(default="")
    smtp_password: str = Field(default="")
    smtp_use_tls: bool = Field(default=True)
    alert_email_from: str = Field(default="soc-alerts@example.com")
    alert_email_to: str = Field(default="soc-team@example.com")
    slack_webhook_url: str = Field(default="")

    # Dry-run mode: response/alert tools log actions instead of performing
    # real network/email side effects. Defaults to True for safety.
    dry_run: bool = Field(default=True)

    # ------------------------------------------------------------------
    # Risk / scoring thresholds
    # ------------------------------------------------------------------
    critical_risk_threshold: int = Field(default=85)
    high_risk_threshold: int = Field(default=65)
    medium_risk_threshold: int = Field(default=40)

    def ensure_directories(self) -> None:
        """Create all required directories if they do not already exist."""
        for directory in (self.data_dir, self.reports_dir, self.logs_dir):
            directory.mkdir(parents=True, exist_ok=True)
        self.sqlite_path.parent.mkdir(parents=True, exist_ok=True)


settings = Settings()
settings.ensure_directories()
