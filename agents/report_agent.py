"""
agents/report_agent.py
========================
Step 8 (final) of the pipeline: aggregates the full run into:
  - final_report.csv  (one row per incident, all pipeline fields flattened)
  - incident_report.json (structured, machine-readable full report)
  - incident_report.md   (human-readable Markdown report)
  - An executive summary (LLM-generated if available, else a templated
    heuristic summary), included in both the Markdown and JSON reports.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from agents.base_agent import BaseAgent
from config import settings
from models import AlertRecord, CoordinatedIncident, Decision, ResponseResult, Severity


class ReportAgent(BaseAgent):
    """Aggregates the full pipeline run into CSV / JSON / Markdown reports."""

    prompt_file = "report.txt"

    def __init__(self) -> None:
        super().__init__(name="report_agent")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def run(
        self,
        incidents: list[CoordinatedIncident] | None = None,
        decisions: list[Decision] | None = None,
        response_results: list[ResponseResult] | None = None,
        alert_records: list[AlertRecord] | None = None,
    ) -> dict[str, Any]:
        incidents = incidents or self._load_incidents_from_memory()
        decisions = decisions or self._load_decisions_from_memory()
        response_results = response_results or self._load_responses_from_memory()
        alert_records = alert_records or self._load_alerts_from_memory()

        decisions_by_id = {d.incident_id: d for d in decisions}
        responses_by_id = {r.incident_id: r for r in response_results}
        alerts_by_incident: dict[str, list[AlertRecord]] = {}
        for alert in alert_records:
            alerts_by_incident.setdefault(alert.incident_id, []).append(alert)

        rows = self._build_rows(incidents, decisions_by_id, responses_by_id, alerts_by_incident)
        severity_breakdown = self._severity_breakdown(incidents)
        executive_summary = self._executive_summary(rows, severity_breakdown)

        final_report_path = self._write_csv(rows)
        json_report_path = self._write_json(rows, severity_breakdown, executive_summary)
        md_report_path = self._write_markdown(rows, severity_breakdown, executive_summary)

        self.logger.info(
            "Report generation complete: %s, %s, %s", final_report_path, json_report_path, md_report_path
        )
        self.log_event(
            "report_run_complete",
            {"incidents": len(rows), "outputs": [str(final_report_path), str(json_report_path), str(md_report_path)]},
        )

        return {
            "final_report_csv": str(final_report_path),
            "incident_report_json": str(json_report_path),
            "incident_report_md": str(md_report_path),
            "executive_summary": executive_summary,
            "severity_breakdown": severity_breakdown,
            "incident_count": len(rows),
        }

    # ------------------------------------------------------------------
    # Internals — data loading
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

    def _load_alerts_from_memory(self) -> list[AlertRecord]:
        raw = self.memory.get_state("alert_records", [])
        return [AlertRecord(**item) for item in raw]

    # ------------------------------------------------------------------
    # Internals — row building
    # ------------------------------------------------------------------
    def _build_rows(
        self,
        incidents: list[CoordinatedIncident],
        decisions_by_id: dict[str, Decision],
        responses_by_id: dict[str, ResponseResult],
        alerts_by_incident: dict[str, list[AlertRecord]],
    ) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for incident in incidents:
            decision = decisions_by_id.get(incident.incident_id)
            response = responses_by_id.get(incident.incident_id)
            alerts = alerts_by_incident.get(incident.incident_id, [])

            rows.append(
                {
                    "incident_id": incident.incident_id,
                    "priority_rank": incident.priority_rank,
                    "timestamp": incident.timestamp,
                    "source_ip": incident.source_ip,
                    "asset": incident.asset,
                    "asset_criticality": incident.asset_criticality,
                    "threat_type": incident.attack_type.value,
                    "severity": incident.severity.value,
                    "confidence": incident.confidence,
                    "risk_score": incident.risk_score,
                    "mitre_attack_technique": incident.mitre_attack_technique,
                    "impact": incident.impact,
                    "decided_action": decision.action.value if decision else None,
                    "requires_human_approval": decision.requires_human_approval if decision else None,
                    "decision_justification": decision.justification if decision else None,
                    "response_status": response.status if response else None,
                    "response_success": response.success if response else None,
                    "runbook_note": response.runbook_note if response else None,
                    "alert_channels": ", ".join(sorted({a.channel for a in alerts})) if alerts else None,
                }
            )
        return rows

    def _severity_breakdown(self, incidents: list[CoordinatedIncident]) -> dict[str, int]:
        breakdown = {s.value: 0 for s in Severity}
        for incident in incidents:
            breakdown[incident.severity.value] += 1
        return breakdown

    # ------------------------------------------------------------------
    # Internals — executive summary
    # ------------------------------------------------------------------
    def _executive_summary(self, rows: list[dict[str, Any]], severity_breakdown: dict[str, int]) -> str:
        llm_summary = self._llm_summary(rows)
        if llm_summary:
            return llm_summary
        return self._heuristic_summary(rows, severity_breakdown)

    def _heuristic_summary(self, rows: list[dict[str, Any]], severity_breakdown: dict[str, int]) -> str:
        total = len(rows)
        auto_actions = sum(1 for r in rows if r["decided_action"] not in (None, "monitor_only"))
        pending_approval = sum(1 for r in rows if r.get("requires_human_approval"))

        return (
            f"During this run, {total} incidents were identified and triaged. "
            f"Severity breakdown — Critical: {severity_breakdown.get('Critical', 0)}, "
            f"High: {severity_breakdown.get('High', 0)}, "
            f"Medium: {severity_breakdown.get('Medium', 0)}, "
            f"Low: {severity_breakdown.get('Low', 0)}. "
            f"{auto_actions} automated response action(s) were taken by the system. "
            f"{pending_approval} incident(s) require human approval before "
            f"disruptive containment actions are executed. Overall risk posture "
            f"for this run is "
            f"{'elevated' if severity_breakdown.get('Critical', 0) or severity_breakdown.get('High', 0) else 'moderate'}."
        )

    def _llm_summary(self, rows: list[dict[str, Any]]) -> str | None:
        template = self.load_prompt()
        user_prompt = template.replace("{incidents}", json.dumps(rows, default=str)[:6000])
        system_prompt = "You are a precise, concise executive cybersecurity report writer."
        if not self._llm_available():
            return None
        try:
            from llm_client import llm_client

            raw = llm_client.generate(system_prompt, user_prompt)
            return raw.strip() if raw else None
        except Exception:  # noqa: BLE001
            return None

    @staticmethod
    def _llm_available() -> bool:
        from llm_client import llm_client

        return llm_client.is_available()

    # ------------------------------------------------------------------
    # Internals — file writers
    # ------------------------------------------------------------------
    def _write_csv(self, rows: list[dict[str, Any]]) -> Path:
        path = settings.final_report_csv
        df = pd.DataFrame(rows)
        df.to_csv(path, index=False)
        return path

    def _write_json(
        self, rows: list[dict[str, Any]], severity_breakdown: dict[str, int], executive_summary: str
    ) -> Path:
        path = settings.incident_report_json
        payload = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "incident_count": len(rows),
            "severity_breakdown": severity_breakdown,
            "executive_summary": executive_summary,
            "incidents": rows,
        }
        path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
        return path

    def _write_markdown(
        self, rows: list[dict[str, Any]], severity_breakdown: dict[str, int], executive_summary: str
    ) -> Path:
        path = settings.incident_report_md
        lines = [
            "# Cyber Incident Response Report",
            "",
            f"_Generated: {datetime.now(timezone.utc).isoformat()}_",
            "",
            "## Executive Summary",
            "",
            executive_summary,
            "",
            "## Severity Breakdown",
            "",
            "| Severity | Count |",
            "|---|---|",
        ]
        for severity, count in severity_breakdown.items():
            lines.append(f"| {severity} | {count} |")

        lines += ["", "## Incident Detail", ""]
        lines.append(
            "| Rank | Incident ID | Threat Type | Severity | Risk Score | Asset | Action | Status |"
        )
        lines.append("|---|---|---|---|---|---|---|---|")
        for row in rows:
            lines.append(
                f"| {row['priority_rank']} | {row['incident_id']} | {row['threat_type']} | "
                f"{row['severity']} | {row['risk_score']} | {row['asset']} | "
                f"{row['decided_action']} | {row['response_status']} |"
            )

        path.write_text("\n".join(lines), encoding="utf-8")
        return path
