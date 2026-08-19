"""
agents/response_agent.py
==========================
Step 6 of the pipeline: executes the action chosen by the Decision Engine
using the concrete tools in `tools/`.

Actions that `requires_human_approval` are NOT executed automatically —
they are recorded with status "pending_approval" so a human analyst can
review and trigger them via the API (`POST /incidents/{id}/approve`).

A short LLM-generated (or heuristic-generated) runbook note is attached to
every result for inclusion in the incident report.
"""

from __future__ import annotations

from typing import Any, Callable

from agents.base_agent import BaseAgent
from models import CoordinatedIncident, Decision, ResponseAction, ResponseResult
from tools.block_ip import block_ip
from tools.isolate_device import isolate_device
from tools.rate_limit import rate_limit


def _disable_user(user: str, reason: str) -> dict[str, Any]:
    """Disable a compromised user account (IAM integration point)."""
    from datetime import datetime, timezone

    from config import settings
    from logging_setup import get_logger

    logger = get_logger("tools.disable_user")
    status = "simulated" if settings.dry_run else "executed"
    logger.info("[%s] Disabling user %s | reason=%s", status.upper(), user, reason)
    return {
        "tool": "disable_user",
        "user": user,
        "reason": reason,
        "status": status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "success": True,
    }


def _generate_firewall_rule(ip_address: str, reason: str) -> dict[str, Any]:
    """Generate (and optionally push) a firewall rule blocking the given IP/pattern."""
    from datetime import datetime, timezone

    from config import settings
    from logging_setup import get_logger

    logger = get_logger("tools.generate_firewall_rule")
    rule = f"deny ip from {ip_address} to any"
    status = "simulated" if settings.dry_run else "executed"
    logger.info("[%s] Generated firewall rule: %s | reason=%s", status.upper(), rule, reason)
    return {
        "tool": "generate_firewall_rule",
        "ip_address": ip_address,
        "rule": rule,
        "reason": reason,
        "status": status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "success": True,
    }


def _quarantine_device(asset: str, reason: str) -> dict[str, Any]:
    """Fully quarantine a device (stronger than isolation — blocks all I/O)."""
    from datetime import datetime, timezone

    from config import settings
    from logging_setup import get_logger

    logger = get_logger("tools.quarantine_device")
    status = "simulated" if settings.dry_run else "executed"
    logger.info("[%s] Quarantining device %s | reason=%s", status.upper(), asset, reason)
    return {
        "tool": "quarantine_device",
        "asset": asset,
        "reason": reason,
        "status": status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "success": True,
    }


def _monitor_only(incident_id: str, reason: str) -> dict[str, Any]:
    from datetime import datetime, timezone

    from logging_setup import get_logger

    logger = get_logger("tools.monitor_only")
    logger.info("Monitoring incident %s (no active response) | reason=%s", incident_id, reason)
    return {
        "tool": "monitor_only",
        "incident_id": incident_id,
        "reason": reason,
        "status": "monitoring",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "success": True,
    }


class ResponseAgent(BaseAgent):
    """Executes the response action chosen by the Decision Engine."""

    prompt_file = "response.txt"

    def __init__(self) -> None:
        super().__init__(name="response_agent")
        self._dispatch: dict[ResponseAction, Callable[[CoordinatedIncident, str], dict[str, Any]]] = {
            ResponseAction.BLOCK_IP: lambda inc, reason: block_ip(inc.source_ip, reason),
            ResponseAction.ISOLATE_DEVICE: lambda inc, reason: isolate_device(inc.asset or inc.destination_ip, reason),
            ResponseAction.DISABLE_USER: lambda inc, reason: _disable_user(inc.user or "unknown_user", reason),
            ResponseAction.RATE_LIMIT: lambda inc, reason: rate_limit(inc.source_ip, 60, reason),
            ResponseAction.GENERATE_FIREWALL_RULE: lambda inc, reason: _generate_firewall_rule(inc.source_ip, reason),
            ResponseAction.QUARANTINE_DEVICE: lambda inc, reason: _quarantine_device(inc.asset or inc.destination_ip, reason),
            ResponseAction.MONITOR_ONLY: lambda inc, reason: _monitor_only(inc.incident_id, reason),
        }

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def run(
        self,
        incidents: list[CoordinatedIncident] | None = None,
        decisions: list[Decision] | None = None,
    ) -> list[ResponseResult]:
        incidents = incidents or self._load_incidents_from_memory()
        decisions = decisions or self._load_decisions_from_memory()
        incidents_by_id = {inc.incident_id: inc for inc in incidents}

        results: list[ResponseResult] = []
        for decision in decisions:
            incident = incidents_by_id.get(decision.incident_id)
            if incident is None:
                self.logger.warning("No matching incident found for decision %s", decision.incident_id)
                continue
            results.append(self._execute_one(incident, decision))

        executed = sum(1 for r in results if r.status not in {"pending_approval"})
        self.logger.info("Response execution complete: %d/%d actions executed", executed, len(results))
        self.log_event("response_run_complete", {"count": len(results), "executed": executed})
        self.memory.set_state("response_results", [r.model_dump() for r in results])
        return results

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    def _load_incidents_from_memory(self) -> list[CoordinatedIncident]:
        raw = self.memory.get_state("coordinated_incidents", [])
        return [CoordinatedIncident(**item) for item in raw]

    def _load_decisions_from_memory(self) -> list[Decision]:
        raw = self.memory.get_state("decisions", [])
        return [Decision(**item) for item in raw]

    def _execute_one(self, incident: CoordinatedIncident, decision: Decision) -> ResponseResult:
        if decision.requires_human_approval:
            self.logger.info(
                "Incident %s requires human approval before executing '%s' — deferring.",
                incident.incident_id, decision.action.value,
            )
            return ResponseResult(
                incident_id=incident.incident_id,
                action=decision.action,
                status="pending_approval",
                success=True,
                details={"justification": decision.justification},
                runbook_note=(
                    f"Action '{decision.action.value}' recommended but deferred pending "
                    f"human approval. Justification: {decision.justification}"
                ),
            )

        handler = self._dispatch.get(decision.action)
        if handler is None:
            self.logger.error("No handler registered for action '%s'", decision.action.value)
            return ResponseResult(
                incident_id=incident.incident_id,
                action=decision.action,
                status="error",
                success=False,
                details={"error": "no handler registered"},
            )

        try:
            details = handler(incident, decision.justification)
        except Exception as exc:  # noqa: BLE001
            self.logger.exception("Response execution failed for %s: %s", incident.incident_id, exc)
            return ResponseResult(
                incident_id=incident.incident_id,
                action=decision.action,
                status="error",
                success=False,
                details={"error": str(exc)},
            )

        runbook_note = self._generate_runbook_note(decision.action.value, incident) or (
            f"Executed '{decision.action.value}' on incident {incident.incident_id}: "
            f"{decision.justification}"
        )

        return ResponseResult(
            incident_id=incident.incident_id,
            action=decision.action,
            status=details.get("status", "executed"),
            success=details.get("success", True),
            details=details,
            runbook_note=runbook_note,
        )

    def _generate_runbook_note(self, action: str, incident: CoordinatedIncident) -> str | None:
        template = self.load_prompt()
        user_prompt = template.replace("{action}", action).replace("{incident}", str(incident.model_dump()))
        system_prompt = "You are a precise SOC response runbook note generator. Respond with plain text only."
        if not self._llm_available():
            return None
        try:
            from llm_client import LLMUnavailableError, llm_client

            raw = llm_client.generate(system_prompt, user_prompt)
            return raw.strip() if raw else None
        except Exception:  # noqa: BLE001
            return None

    @staticmethod
    def _llm_available() -> bool:
        from llm_client import llm_client

        return llm_client.is_available()
