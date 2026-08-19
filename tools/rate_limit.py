"""
tools/rate_limit.py
====================
Applies rate limiting to a source IP or endpoint, used for lower-severity
volumetric abuse (e.g. moderate DDoS, API abuse) where an outright block
would be too disruptive.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from langchain_core.tools import tool

from config import settings
from logging_setup import get_logger

logger = get_logger(__name__)


def rate_limit(
    ip_address: str,
    requests_per_minute: int = 60,
    reason: str = "Excessive request volume",
) -> dict[str, Any]:
    """Apply a rate limit to the given IP address.

    Args:
        ip_address: The source IP to throttle.
        requests_per_minute: The new cap to apply.
        reason: Human-readable justification, stored in the audit trail.

    Returns:
        A structured result dict describing what happened.
    """
    timestamp = datetime.now(timezone.utc).isoformat()
    try:
        if settings.dry_run:
            logger.info(
                "[DRY-RUN] Would rate-limit %s to %d req/min | reason=%s",
                ip_address, requests_per_minute, reason,
            )
            status = "simulated"
        else:
            # Real integration point: call WAF / API gateway rate-limit rule API here.
            logger.info(
                "Rate-limiting %s to %d req/min | reason=%s",
                ip_address, requests_per_minute, reason,
            )
            status = "executed"

        return {
            "tool": "rate_limit",
            "ip_address": ip_address,
            "requests_per_minute": requests_per_minute,
            "reason": reason,
            "status": status,
            "timestamp": timestamp,
            "success": True,
        }
    except Exception as exc:  # noqa: BLE001
        logger.exception("rate_limit failed for %s: %s", ip_address, exc)
        return {
            "tool": "rate_limit",
            "ip_address": ip_address,
            "reason": reason,
            "status": "error",
            "error": str(exc),
            "timestamp": timestamp,
            "success": False,
        }


@tool("rate_limit")
def rate_limit_tool(
    ip_address: str, requests_per_minute: int = 60, reason: str = "Excessive request volume"
) -> dict[str, Any]:
    """Apply rate limiting to a noisy or abusive source IP."""
    return rate_limit(ip_address, requests_per_minute, reason)
