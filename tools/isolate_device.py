"""
tools/isolate_device.py
========================
Isolates a compromised endpoint/asset from the network (e.g. via EDR agent
network-containment API), preventing lateral movement while preserving the
host for forensics.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from langchain_core.tools import tool

from config import settings
from logging_setup import get_logger

logger = get_logger(__name__)


def isolate_device(asset: str, reason: str = "Compromise suspected") -> dict[str, Any]:
    """Isolate the given asset/endpoint from the network.

    Args:
        asset: Hostname or asset identifier to isolate.
        reason: Human-readable justification, stored in the audit trail.

    Returns:
        A structured result dict describing what happened.
    """
    timestamp = datetime.now(timezone.utc).isoformat()
    try:
        if settings.dry_run:
            logger.info("[DRY-RUN] Would isolate device %s | reason=%s", asset, reason)
            status = "simulated"
        else:
            # Real integration point: call EDR containment API (CrowdStrike,
            # Defender for Endpoint, SentinelOne, etc.) here.
            logger.info("Isolating device %s | reason=%s", asset, reason)
            status = "executed"

        return {
            "tool": "isolate_device",
            "asset": asset,
            "reason": reason,
            "status": status,
            "timestamp": timestamp,
            "success": True,
        }
    except Exception as exc:  # noqa: BLE001
        logger.exception("isolate_device failed for %s: %s", asset, exc)
        return {
            "tool": "isolate_device",
            "asset": asset,
            "reason": reason,
            "status": "error",
            "error": str(exc),
            "timestamp": timestamp,
            "success": False,
        }


@tool("isolate_device")
def isolate_device_tool(asset: str, reason: str = "Compromise suspected") -> dict[str, Any]:
    """Isolate a compromised endpoint/asset from the network."""
    return isolate_device(asset, reason)
