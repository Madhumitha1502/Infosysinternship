"""
tools/block_ip.py
==================
Blocks a malicious source IP address at the network perimeter (firewall /
security group / WAF, depending on deployment).

In `dry_run` mode (the default), no real firewall API is called — the
action is logged and returned as a structured result so the rest of the
pipeline (and audit trail) behaves identically to a live run.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from langchain_core.tools import tool

from config import settings
from logging_setup import get_logger

logger = get_logger(__name__)


def block_ip(ip_address: str, reason: str = "Malicious activity detected") -> dict[str, Any]:
    """Block the given IP address at the perimeter firewall.

    Args:
        ip_address: The source IP to block.
        reason: Human-readable justification, stored in the audit trail.

    Returns:
        A structured result dict describing what happened.
    """
    timestamp = datetime.now(timezone.utc).isoformat()
    try:
        if settings.dry_run:
            logger.info("[DRY-RUN] Would block IP %s | reason=%s", ip_address, reason)
            status = "simulated"
        else:
            # Real integration point: call firewall/WAF/cloud security-group API here.
            # e.g. requests.post(f"{settings.firewall_api_url}/block", json={...})
            logger.info("Blocking IP %s at firewall | reason=%s", ip_address, reason)
            status = "executed"

        return {
            "tool": "block_ip",
            "ip_address": ip_address,
            "reason": reason,
            "status": status,
            "timestamp": timestamp,
            "success": True,
        }
    except Exception as exc:  # noqa: BLE001
        logger.exception("block_ip failed for %s: %s", ip_address, exc)
        return {
            "tool": "block_ip",
            "ip_address": ip_address,
            "reason": reason,
            "status": "error",
            "error": str(exc),
            "timestamp": timestamp,
            "success": False,
        }


@tool("block_ip")
def block_ip_tool(ip_address: str, reason: str = "Malicious activity detected") -> dict[str, Any]:
    """Block a malicious source IP address at the perimeter firewall."""
    return block_ip(ip_address, reason)
