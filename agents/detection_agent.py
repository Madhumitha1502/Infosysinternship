"""
agents/detection_agent.py
==========================
Step 2 of the pipeline: scans raw network log entries and flags suspicious
activity, classifying it into one of the fixed attack categories.

Detection strategy:
  1. Fast heuristic/signature matching (regex + keyword rules) runs first
     on every log entry — this is cheap, deterministic, and catches the
     vast majority of obvious attack signatures without any LLM call.
  2. If an LLM provider is configured, the LLM is used to *confirm and
     refine* the heuristic call (attack type + reasoning), giving richer
     output while never being a single point of failure: if the LLM is
     unavailable or returns malformed output, the heuristic verdict is
     used as-is.
"""

from __future__ import annotations

import re
from typing import Any

import pandas as pd

from agents.base_agent import BaseAgent
from config import settings
from models import DetectedEvent, NetworkLogEntry, ThreatType

# Ordered signature rules: (ThreatType, compiled regex applied to payload_snippet)
_SIGNATURES: list[tuple[ThreatType, re.Pattern]] = [
    (ThreatType.SQL_INJECTION, re.compile(r"(union\s+select|or\s+1=1|--\s|drop\s+table|' or ')", re.I)),
    (ThreatType.RANSOMWARE, re.compile(r"(ransom|decrypt|encrypted|readme_decrypt)", re.I)),
    (ThreatType.MALWARE, re.compile(r"(malware|trojan|\.exe|dropped binary|suspicious binary)", re.I)),
    (ThreatType.PHISHING, re.compile(r"(phishing|credential harvest|fake login|spoofed)", re.I)),
    (ThreatType.PRIVILEGE_ESCALATION, re.compile(r"(sudo su|privilege escalat|unauthorized root|added to admin)", re.I)),
    (ThreatType.BRUTE_FORCE, re.compile(r"(brute force|failed login|failed ssh|credential stuffing)", re.I)),
    (ThreatType.PORT_SCANNING, re.compile(r"(port scan|sequential port|nmap)", re.I)),
    (ThreatType.DDOS, re.compile(r"(syn flood|http flood|ddos|botnet|req/min)", re.I)),
]

_HIGH_REQUEST_COUNT_THRESHOLD = 1000
_HIGH_BYTES_THRESHOLD = 10_000_000


class DetectionAgent(BaseAgent):
    """Flags suspicious network activity from raw logs."""

    prompt_file = "detection.txt"

    def __init__(self) -> None:
        super().__init__(name="detection_agent")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def load_logs(self, csv_path: str | None = None) -> pd.DataFrame:
        """Load raw network logs from CSV (Step 1 of the pipeline)."""
        path = csv_path or str(settings.network_logs_csv)
        try:
            df = pd.read_csv(path)
            self.logger.info("Loaded %d log entries from %s", len(df), path)
            return df
        except FileNotFoundError:
            self.logger.error("Network log file not found: %s", path)
            raise
        except pd.errors.ParserError as exc:
            self.logger.error("Failed to parse CSV %s: %s", path, exc)
            raise

    def run(self, csv_path: str | None = None) -> list[DetectedEvent]:
        """Run detection over all logs and return the list of detected events
        (both suspicious and benign, each tagged accordingly)."""
        df = self.load_logs(csv_path)
        detected: list[DetectedEvent] = []

        for _, row in df.iterrows():
            entry = self._row_to_entry(row)
            event = self._detect_one(entry)
            detected.append(event)

        suspicious_count = sum(1 for e in detected if e.is_suspicious)
        self.logger.info(
            "Detection complete: %d/%d entries flagged suspicious", suspicious_count, len(detected)
        )
        self.log_event(
            "detection_run_complete",
            {"total": len(detected), "suspicious": suspicious_count},
        )
        self.memory.set_state("detected_events", [e.model_dump() for e in detected])
        return detected

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    @staticmethod
    def _row_to_entry(row: "pd.Series[Any]") -> NetworkLogEntry:
        data = row.to_dict()
        # Normalize NaN -> None for optional fields
        for key, value in list(data.items()):
            if pd.isna(value):
                data[key] = None
        data["log_id"] = str(data.get("log_id"))
        return NetworkLogEntry(**data)

    def _heuristic_detect(self, entry: NetworkLogEntry) -> tuple[bool, ThreatType, str]:
        text = (entry.payload_snippet or "").strip()

        for attack_type, pattern in _SIGNATURES:
            if pattern.search(text):
                return True, attack_type, f"Matched signature for {attack_type.value}: '{text[:80]}'"

        # Volumetric heuristics independent of payload text
        if (entry.request_count or 0) >= _HIGH_REQUEST_COUNT_THRESHOLD:
            return True, ThreatType.DDOS, f"High request volume: {entry.request_count} requests"
        if (entry.bytes_transferred or 0) >= _HIGH_BYTES_THRESHOLD:
            return True, ThreatType.DDOS, f"Abnormally high bytes transferred: {entry.bytes_transferred}"
        if entry.status and str(entry.status).lower() == "flagged":
            return True, ThreatType.UNKNOWN, "Marked as flagged by upstream sensor, no signature match"

        return False, ThreatType.BENIGN, "No suspicious signature or volumetric anomaly detected"

    def _detect_one(self, entry: NetworkLogEntry) -> DetectedEvent:
        is_suspicious, attack_type, reasoning = self._heuristic_detect(entry)
        method = "heuristic"

        if is_suspicious:
            llm_result = self._llm_detect(entry)
            if llm_result is not None:
                try:
                    llm_attack_type = ThreatType(llm_result.get("attack_type", attack_type.value))
                    is_suspicious = bool(llm_result.get("is_suspicious", is_suspicious))
                    attack_type = llm_attack_type
                    reasoning = llm_result.get("reasoning", reasoning)
                    method = "llm"
                except ValueError:
                    self.logger.debug("LLM returned unrecognized attack_type, keeping heuristic result")

        return DetectedEvent(
            **entry.model_dump(),
            is_suspicious=is_suspicious,
            attack_type=attack_type,
            detection_method=method,
            detection_reasoning=reasoning,
        )

    def _llm_detect(self, entry: NetworkLogEntry) -> dict[str, Any] | None:
        template = self.load_prompt()
        user_prompt = template.replace("{log_entry}", str(entry.model_dump()))
        system_prompt = "You are a precise, JSON-only SOC detection assistant."
        return self.call_llm_json(system_prompt, user_prompt)
