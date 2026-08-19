"""
agents/decision_engine.py
===========================
Step 5 of the pipeline: the Decision Engine.

Given a prioritized incident (risk score, severity, threat type, asset
criticality), it chooses the single best automated response action from a
fixed action space, and flags whether the action needs human approval
before execution (disruptive actions on non-Critical incidents default to
requiring approval, to avoid unnecessary business impact from full
automation).

A deterministic decision table is the source of truth; the LLM (if
available) can override the table's choice, but only when it stays within
the valid action space — this bounds the "blast radius" of LLM
hallucination in an incident-response automation context.
"""

from __future__ import annotations

from typing import Any

from agents.base_agent import BaseAgent
from models import CoordinatedIncident, Decision, ResponseAction, Severity, ThreatType

# Deterministic mapping: attack type -> default response action.
_ACTION_TABLE: dict[ThreatType, ResponseAction] = {
    ThreatType.SQL_INJECTION: ResponseAction.GENERATE_FIREWALL_RULE,
    ThreatType.BRUTE_FORCE: ResponseAction.BLOCK_IP,
    ThreatType.DDOS: ResponseAction.RATE_LIMIT,
    ThreatType.PORT_SCANNING: ResponseAction.BLOCK_IP,
    ThreatType.MALWARE: ResponseAction.ISOLATE_DEVICE,
    ThreatType.RANSOMWARE: ResponseAction.QUARANTINE_DEVICE,
    ThreatType.PHISHING: ResponseAction.DISABLE_USER,
    ThreatType.PRIVILEGE_ESCALATION: ResponseAction.DISABLE_USER,
    ThreatType.UNKNOWN: ResponseAction.MONITOR_ONLY,
    ThreatType.BENIGN: ResponseAction.MONITOR_ONLY,
}

_DISRUPTIVE_ACTIONS = {
    ResponseAction.ISOLATE_DEVICE,
    ResponseAction.DISABLE_USER,
    ResponseAction.QUARANTINE_DEVICE,
}


class DecisionEngine(BaseAgent):
    """Chooses the best automated response action for each incident."""

    prompt_file = "decision.txt"

    def __init__(self) -> None:
        super().__init__(name="decision_engine")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def run(self, incidents: list[CoordinatedIncident] | None = None) -> list[Decision]:
        incidents = incidents or self._load_incidents_from_memory()

        decisions = [self._decide_one(incident) for incident in incidents]

        self.logger.info("Decision engine complete: %d decisions made", len(decisions))
        approvals_needed = sum(1 for d in decisions if d.requires_human_approval)
        self.log_event(
            "decision_run_complete",
            {"count": len(decisions), "requires_human_approval": approvals_needed},
        )
        self.memory.set_state("decisions", [d.model_dump() for d in decisions])
        return decisions

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    def _load_incidents_from_memory(self) -> list[CoordinatedIncident]:
        raw = self.memory.get_state("coordinated_incidents", [])
        return [CoordinatedIncident(**item) for item in raw]

    def _heuristic_decide(self, incident: CoordinatedIncident) -> tuple[ResponseAction, str]:
        action = _ACTION_TABLE.get(incident.attack_type, ResponseAction.MONITOR_ONLY)

        # Downgrade very-low-risk incidents to monitor-only regardless of type.
        if incident.risk_score < 30:
            return ResponseAction.MONITOR_ONLY, "Risk score below actionable threshold; monitoring only."

        justification = (
            f"Default policy action for {incident.attack_type.value} "
            f"at risk score {incident.risk_score:.1f} (severity: {incident.severity.value})."
        )
        return action, justification

    def _requires_approval(self, action: ResponseAction, severity: Severity) -> bool:
        return action in _DISRUPTIVE_ACTIONS and severity != Severity.CRITICAL

    def _decide_one(self, incident: CoordinatedIncident) -> Decision:
        action, justification = self._heuristic_decide(incident)
        method = "heuristic"

        llm_result = self._llm_decide(incident)
        if llm_result is not None:
            try:
                candidate_action = ResponseAction(llm_result.get("action", action.value))
                action = candidate_action
                justification = llm_result.get("justification", justification)
                method = "llm"
            except ValueError:
                self.logger.debug("LLM proposed an out-of-domain action; keeping heuristic decision")

        requires_approval = self._requires_approval(action, incident.severity)
        # Respect an explicit LLM approval flag only if it *raises* caution
        # (never let the LLM silently waive a safety-critical approval gate).
        if llm_result is not None and bool(llm_result.get("requires_human_approval", False)):
            requires_approval = True

        return Decision(
            incident_id=incident.incident_id,
            action=action,
            justification=justification,
            requires_human_approval=requires_approval,
            decision_method=method,
        )

    def _llm_decide(self, incident: CoordinatedIncident) -> dict[str, Any] | None:
        template = self.load_prompt()
        user_prompt = template.replace("{incident}", str(incident.model_dump()))
        system_prompt = "You are a precise, JSON-only automated incident response decision engine."
        return self.call_llm_json(system_prompt, user_prompt)
