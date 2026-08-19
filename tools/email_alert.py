"""
tools/email_alert.py
=====================
Sends an email alert to the configured SOC distribution list via SMTP.

In `dry_run` mode (the default), no real SMTP connection is made — the
message is logged and returned as a structured result.
"""

from __future__ import annotations

import smtplib
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

from langchain_core.tools import tool

from config import settings
from logging_setup import get_logger

logger = get_logger(__name__)


def send_email_alert(subject: str, body: str, to_address: str | None = None) -> dict[str, Any]:
    """Send an incident alert email.

    Args:
        subject: Email subject line.
        body: Plain-text email body.
        to_address: Recipient override; defaults to `settings.alert_email_to`.

    Returns:
        A structured result dict describing what happened.
    """
    timestamp = datetime.now(timezone.utc).isoformat()
    recipient = to_address or settings.alert_email_to

    try:
        if settings.dry_run:
            logger.info("[DRY-RUN] Would email '%s' to %s", subject, recipient)
            status = "simulated"
        else:
            message = MIMEMultipart()
            message["From"] = settings.alert_email_from
            message["To"] = recipient
            message["Subject"] = subject
            message.attach(MIMEText(body, "plain"))

            with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as server:
                if settings.smtp_use_tls:
                    server.starttls()
                if settings.smtp_username:
                    server.login(settings.smtp_username, settings.smtp_password)
                server.sendmail(settings.alert_email_from, [recipient], message.as_string())

            logger.info("Email alert sent to %s | subject=%s", recipient, subject)
            status = "executed"

        return {
            "tool": "send_email_alert",
            "to": recipient,
            "subject": subject,
            "status": status,
            "timestamp": timestamp,
            "success": True,
        }
    except Exception as exc:  # noqa: BLE001
        logger.exception("send_email_alert failed: %s", exc)
        return {
            "tool": "send_email_alert",
            "to": recipient,
            "subject": subject,
            "status": "error",
            "error": str(exc),
            "timestamp": timestamp,
            "success": False,
        }


@tool("send_email_alert")
def send_email_alert_tool(subject: str, body: str, to_address: str = "") -> dict[str, Any]:
    """Send an email alert to the SOC distribution list."""
    return send_email_alert(subject, body, to_address or None)
