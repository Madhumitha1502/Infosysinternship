"""
agents/coordination_agent.py
==============================
Step 4 of the pipeline: takes analyzed events and turns them into a
prioritized, deduplicated incident queue.

Prioritization is purely deterministic/quantitative (no LLM call needed
here) — it computes a 0-100 risk score from:
  - severity (40% weight)
  - detection/analysis confidence (20% weight)
  - asset criticality (25% weight)
  - "business impact" proxy: whether the asset/user look production-critical
    based on naming heuristics and volumetric magnitude (15% weight)

The resulting `CoordinatedIncident` list is sorted descending by risk score
and given a `priority_rank`, ready for the Decision Engine.
"""

from __future__ import annotations

import uuid

from agents.base_agent import BaseAgent
from models import AnalyzedEvent, CoordinatedIncident, Severity

_SEVERITY_SCORE = {Severity.LOW: 25, Severity.MEDIUM: 50, Severity.HIGH: 75, Severity.CRITICAL: 100}
_CRITICALITY_SCORE = {"Low": 25, "Medium": 50, "High": 75, "Critical": 100}

_WEIGHT_SEVERITY = 0.40
_WEIGHT_CONFIDENCE = 0.20
_WEIGHT_CRITICALITY = 0.25
_WEIGHT_IMPACT = 0.15


class CoordinationAgent(BaseAgent):
    """Prioritizes analyzed events into a ranked incident queue."""

    def __init__(self) -> None:
        super().__init__(name="coordination_agent")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def run(self, analyzed_events: list[AnalyzedEvent] | None = None) -> list[CoordinatedIncident]:
        events = analyzed_events or self._load_analyzed_from_memory()

        incidents = [self._to_incident(event) for event in events]
        incidents.sort(key=lambda inc: inc.risk_score, reverse=True)
        for rank, incident in enumerate(incidents, start=1):
            incident.priority_rank = rank

        self.logger.info("Coordination complete: %d incidents prioritized", len(incidents))
        if incidents:
            self.logger.info(
                "Top incident: %s (%s) risk_score=%.1f",
                incidents[0].incident_id, incidents[0].attack_type.value, incidents[0].risk_score,
            )
        self.log_event("coordination_run_complete", {"count": len(incidents)})

        for incident in incidents:
            self.memory.upsert_incident(incident.incident_id, incident.model_dump())

        self.memory.set_state("coordinated_incidents", [i.model_dump() for i in incidents])
        return incidents

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    def _load_analyzed_from_memory(self) -> list[AnalyzedEvent]:
        raw = self.memory.get_state("analyzed_events", [])
        return [AnalyzedEvent(**item) for item in raw]

    def _business_impact_score(self, event: AnalyzedEvent) -> float:
        score = 30.0
        asset = (event.asset or "").lower()
        if any(keyword in asset for keyword in ("prod", "db", "bastion", "gateway", "server")):
            score += 40
        if (event.request_count or 0) > 5000 or (event.bytes_transferred or 0) > 20_000_000:
            score += 20
        if event.user and event.user.lower() in {"root", "administrator", "dbadmin"}:
            score += 10
        return min(100.0, score)

    def _to_incident(self, event: AnalyzedEvent) -> CoordinatedIncident:
        severity_score = _SEVERITY_SCORE[event.severity]
        confidence_score = event.confidence * 100
        criticality_score = _CRITICALITY_SCORE.get(event.asset_criticality or "Medium", 50)
        impact_score = self._business_impact_score(event)

        risk_score = (
            severity_score * _WEIGHT_SEVERITY
            + confidence_score * _WEIGHT_CONFIDENCE
            + criticality_score * _WEIGHT_CRITICALITY
            + impact_score * _WEIGHT_IMPACT
        )
        risk_score = round(min(100.0, risk_score), 2)

        incident_id = f"INC-{event.log_id}-{uuid.uuid4().hex[:6].upper()}"

        return CoordinatedIncident(
            **event.model_dump(),
            incident_id=incident_id,
            risk_score=risk_score,
        )
