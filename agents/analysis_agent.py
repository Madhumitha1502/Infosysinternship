"""
agents/analysis_agent.py
==========================
Step 3 of the pipeline: takes suspicious events from the Detection Agent and
performs deeper classification — severity, confidence, business impact, and
MITRE ATT&CK technique mapping.

Like the Detection Agent, this uses a heuristic baseline (a lookup table
keyed by attack type, adjusted by asset criticality and volumetric signals)
with an optional LLM refinement pass.
"""

from __future__ import annotations

from typing import Any

from agents.base_agent import BaseAgent
from models import AnalyzedEvent, DetectedEvent, Severity, ThreatType

# Baseline severity / MITRE mapping per attack type.
_THREAT_PROFILE: dict[ThreatType, dict[str, Any]] = {
    ThreatType.SQL_INJECTION: dict(severity=Severity.HIGH, confidence=0.85, mitre="T1190 - Exploit Public-Facing Application"),
    ThreatType.BRUTE_FORCE: dict(severity=Severity.MEDIUM, confidence=0.8, mitre="T1110 - Brute Force"),
    ThreatType.DDOS: dict(severity=Severity.HIGH, confidence=0.9, mitre="T1498 - Network Denial of Service"),
    ThreatType.PORT_SCANNING: dict(severity=Severity.LOW, confidence=0.7, mitre="T1046 - Network Service Discovery"),
    ThreatType.MALWARE: dict(severity=Severity.CRITICAL, confidence=0.85, mitre="T1204 - User Execution"),
    ThreatType.RANSOMWARE: dict(severity=Severity.CRITICAL, confidence=0.95, mitre="T1486 - Data Encrypted for Impact"),
    ThreatType.PHISHING: dict(severity=Severity.MEDIUM, confidence=0.75, mitre="T1566 - Phishing"),
    ThreatType.PRIVILEGE_ESCALATION: dict(severity=Severity.HIGH, confidence=0.8, mitre="T1068 - Exploitation for Privilege Escalation"),
    ThreatType.UNKNOWN: dict(severity=Severity.MEDIUM, confidence=0.5, mitre="TA0001 - Initial Access (unconfirmed)"),
    ThreatType.BENIGN: dict(severity=Severity.LOW, confidence=0.95, mitre="N/A"),
}

_CRITICALITY_BUMP = {"Critical": 1, "High": 0, "Medium": 0, "Low": -1}
_SEVERITY_ORDER = [Severity.LOW, Severity.MEDIUM, Severity.HIGH, Severity.CRITICAL]


class AnalysisAgent(BaseAgent):
    """Classifies detected events by severity, confidence, impact, and MITRE technique."""

    prompt_file = "analysis.txt"

    def __init__(self) -> None:
        super().__init__(name="analysis_agent")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def run(self, detected_events: list[DetectedEvent] | None = None) -> list[AnalyzedEvent]:
        events = detected_events or self._load_detected_from_memory()
        suspicious = [e for e in events if e.is_suspicious]

        analyzed: list[AnalyzedEvent] = []
        for event in suspicious:
            analyzed.append(self._analyze_one(event))

        self.logger.info("Analysis complete: %d events classified", len(analyzed))
        self.log_event("analysis_run_complete", {"count": len(analyzed)})
        self.memory.set_state("analyzed_events", [e.model_dump() for e in analyzed])
        return analyzed

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    def _load_detected_from_memory(self) -> list[DetectedEvent]:
        raw = self.memory.get_state("detected_events", [])
        return [DetectedEvent(**item) for item in raw]

    def _bump_severity(self, severity: Severity, bump: int) -> Severity:
        idx = _SEVERITY_ORDER.index(severity)
        new_idx = max(0, min(len(_SEVERITY_ORDER) - 1, idx + bump))
        return _SEVERITY_ORDER[new_idx]

    def _heuristic_analyze(self, event: DetectedEvent) -> dict[str, Any]:
        profile = _THREAT_PROFILE.get(event.attack_type, _THREAT_PROFILE[ThreatType.UNKNOWN])
        bump = _CRITICALITY_BUMP.get(event.asset_criticality or "Medium", 0)
        severity = self._bump_severity(profile["severity"], bump)

        impact = (
            f"A {event.attack_type.value} event was detected targeting "
            f"'{event.asset or event.destination_ip}' "
            f"(criticality: {event.asset_criticality or 'Medium'}). "
            f"Estimated severity: {severity.value}."
        )

        return {
            "severity": severity,
            "confidence": profile["confidence"],
            "impact": impact,
            "mitre_attack_technique": profile["mitre"],
        }

    def _analyze_one(self, event: DetectedEvent) -> AnalyzedEvent:
        result = self._heuristic_analyze(event)
        method = "heuristic"

        llm_result = self._llm_analyze(event)
        if llm_result is not None:
            try:
                severity = Severity(llm_result.get("severity", result["severity"].value))
                confidence = float(llm_result.get("confidence", result["confidence"]))
                confidence = max(0.0, min(1.0, confidence))
                impact = llm_result.get("impact", result["impact"])
                mitre = llm_result.get("mitre_attack_technique", result["mitre_attack_technique"])
                result = {
                    "severity": severity,
                    "confidence": confidence,
                    "impact": impact,
                    "mitre_attack_technique": mitre,
                }
                method = "llm"
            except (ValueError, TypeError):
                self.logger.debug("LLM returned malformed analysis fields, keeping heuristic result")

        return AnalyzedEvent(
            **event.model_dump(),
            severity=result["severity"],
            confidence=result["confidence"],
            impact=result["impact"],
            mitre_attack_technique=result["mitre_attack_technique"],
            analysis_method=method,
        )

    def _llm_analyze(self, event: DetectedEvent) -> dict[str, Any] | None:
        template = self.load_prompt()
        user_prompt = template.replace("{event}", str(event.model_dump()))
        system_prompt = "You are a precise, JSON-only SOC threat analysis assistant."
        return self.call_llm_json(system_prompt, user_prompt)
