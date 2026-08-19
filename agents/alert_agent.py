"""
agents/alert_agent.py
=======================
Step 7 of the pipeline: notifies humans/systems about incidents via:
  - Email (through tools/email_alert.py)
  - Slack (via incoming webhook, if configured)
  - Structured JSON alert objects (always produced, written to
    data/alert_output.csv and available to the API/report agent)

Alerts are generated for every incident that received an active response
(or is pending approval) — pure "monitor_only" / benign items are skipped
to avoid alert fatigue, unless severity is High/Critical.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

import requests

from agents.base_agent import BaseAgent
from config import settings
from models import AlertRecord, CoordinatedIncident, Decision, ResponseResult, Severity
from tools.email_alert import send_email_alert

_ALWAYS_ALERT_SEVERITIES = {Severity.HIGH, Severity.CRITICAL}


class AlertAgent(BaseAgent):
    """Generates and dispatches email, Slack, and JSON alerts for incidents."""

    def __init__(self) -> None:
        super().__init__(name="alert_agent")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def run(
        self,
        incidents: list[CoordinatedIncident] | None = None,
        decisions: list[Decision] | None = None,
        response_results: list[ResponseResult] | None = None,
    ) -> list[AlertRecord]:
        incidents = incidents or self._load_incidents_from_memory()
        decisions = decisions or self._load_decisions_from_memory()
        response_results = response_results or self._load_responses_from_memory()

        decisions_by_id = {d.incident_id: d for d in decisions}
        responses_by_id = {r.incident_id: r for r in response_results}

        records: list[AlertRecord] = []
        for incident in incidents:
            decision = decisions_by_id.get(incident.incident_id)
            response = responses_by_id.get(incident.incident_id)

            if not self._should_alert(incident, decision):
                continue

            records.extend(self._alert_for_incident(incident, decision, response))

        self.logger.info("Alerting complete: %d alert records generated", len(records))
        self.log_event("alert_run_complete", {"count": len(records)})
        self.memory.set_state("alert_records", [r.model_dump() for r in records])
        return records

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    def _load_incidents_from_memory(self) -> list[CoordinatedIncident]:
        raw = self.memory.get_state("coordinated_incidents", [])
        return [CoordinatedIncident(**item) for item in raw]

    def _load_decisions_from_memory(self) -> list[Decision]:
        raw = self.memory.get_state("decisions", [])
        return [Decision(**item) for item in raw]

    def _load_responses_from_memory(self) -> list[ResponseResult]:
        raw = self.memory.get_state("response_results", [])
        return [ResponseResult(**item) for item in raw]

    def _should_alert(self, incident: CoordinatedIncident, decision: Decision | None) -> bool:
        if incident.severity in _ALWAYS_ALERT_SEVERITIES:
            return True
        if decision and decision.action.value != "monitor_only":
            return True
        return False

    def _alert_for_incident(
        self,
        incident: CoordinatedIncident,
        decision: Decision | None,
        response: ResponseResult | None,
    ) -> list[AlertRecord]:
        subject = f"[{incident.severity.value.upper()}] {incident.attack_type.value} detected on {incident.asset or incident.destination_ip}"
        body = self._build_body(incident, decision, response)

        records: list[AlertRecord] = []

        # JSON alert (always produced)
        json_alert = self._build_json_alert(incident, decision, response)
        records.append(
            AlertRecord(
                incident_id=incident.incident_id,
                channel="json",
                status="generated",
                success=True,
                message=json.dumps(json_alert),
            )
        )

        # Email alert
        email_result = send_email_alert(subject, body)
        records.append(
            AlertRecord(
                incident_id=incident.incident_id,
                channel="email",
                status=email_result.get("status", "unknown"),
                success=email_result.get("success", False),
                message=subject,
            )
        )

        # Slack alert (only if webhook configured)
        slack_result = self._send_slack_alert(subject, body)
        if slack_result is not None:
            records.append(
                AlertRecord(
                    incident_id=incident.incident_id,
                    channel="slack",
                    status=slack_result.get("status", "unknown"),
                    success=slack_result.get("success", False),
                    message=subject,
                )
            )

        return records

    def _build_body(
        self,
        incident: CoordinatedIncident,
        decision: Decision | None,
        response: ResponseResult | None,
    ) -> str:
        lines = [
            f"Incident ID: {incident.incident_id}",
            f"Threat Type: {incident.attack_type.value}",
            f"Severity: {incident.severity.value}",
            f"Risk Score: {incident.risk_score}",
            f"Source IP: {incident.source_ip}",
            f"Asset: {incident.asset or incident.destination_ip} (criticality: {incident.asset_criticality})",
            f"MITRE ATT&CK: {incident.mitre_attack_technique}",
            f"Impact: {incident.impact}",
        ]
        if decision:
            lines.append(f"Decided Action: {decision.action.value} (approval required: {decision.requires_human_approval})")
            lines.append(f"Justification: {decision.justification}")
        if response:
            lines.append(f"Response Status: {response.status}")
            if response.runbook_note:
                lines.append(f"Runbook Note: {response.runbook_note}")
        return "\n".join(lines)

    def _build_json_alert(
        self,
        incident: CoordinatedIncident,
        decision: Decision | None,
        response: ResponseResult | None,
    ) -> dict[str, Any]:
        return {
            "incident_id": incident.incident_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "threat_type": incident.attack_type.value,
            "severity": incident.severity.value,
            "risk_score": incident.risk_score,
            "source_ip": incident.source_ip,
            "asset": incident.asset,
            "mitre_attack_technique": incident.mitre_attack_technique,
            "decision": decision.model_dump() if decision else None,
            "response": response.model_dump() if response else None,
        }

    def _send_slack_alert(self, subject: str, body: str) -> dict[str, Any] | None:
        if not settings.slack_webhook_url:
            return None

        timestamp = datetime.now(timezone.utc).isoformat()
        payload = {"text": f"*{subject}*\n```{body}```"}

        try:
            if settings.dry_run:
                self.logger.info("[DRY-RUN] Would post Slack alert: %s", subject)
                return {"status": "simulated", "success": True, "timestamp": timestamp}

            resp = requests.post(settings.slack_webhook_url, json=payload, timeout=10)
            resp.raise_for_status()
            self.logger.info("Slack alert sent: %s", subject)
            return {"status": "executed", "success": True, "timestamp": timestamp}
        except requests.RequestException as exc:
            self.logger.exception("Slack alert failed: %s", exc)
            return {"status": "error", "success": False, "timestamp": timestamp, "error": str(exc)}
