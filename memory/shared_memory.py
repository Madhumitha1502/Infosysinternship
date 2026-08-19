"""
memory/shared_memory.py
========================
Shared, persistent memory layer used by every agent in the pipeline.

Why SQLite:
- Zero-ops embedded database, ships with Python stdlib (`sqlite3`).
- Gives us durability across process restarts (unlike an in-memory dict),
  which matters for an incident-response system where you may want to
  resume/audit a run after a crash.

The `SharedMemory` class exposes a simple key/value + structured "events"
API that agents use to:
  1. Pass intermediate results to downstream agents (`set_state` / `get_state`)
  2. Append immutable audit-log style events (`log_event` / `get_events`)
  3. Track per-incident context across the whole pipeline (`upsert_incident`)

All methods are synchronous (SQLite + short transactions are fast enough for
this workload) but are safe to call from async code via `asyncio.to_thread`
if needed.
"""

from __future__ import annotations

import json
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Optional

from config import settings
from logging_setup import get_logger

logger = get_logger(__name__)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS kv_state (
    key         TEXT PRIMARY KEY,
    value       TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS events (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    agent       TEXT NOT NULL,
    event_type  TEXT NOT NULL,
    payload     TEXT NOT NULL,
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS incidents (
    incident_id     TEXT PRIMARY KEY,
    source_ip       TEXT,
    threat_type     TEXT,
    severity        TEXT,
    risk_score      REAL,
    status          TEXT,
    data            TEXT NOT NULL,
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL
);
"""


class SharedMemory:
    """Thread-safe SQLite-backed shared memory for cross-agent state."""

    def __init__(self, db_path: Optional[Path] = None) -> None:
        self.db_path = db_path or settings.sqlite_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._init_schema()
        logger.info("SharedMemory initialized at %s", self.db_path)

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------
    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path, timeout=30, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_schema(self) -> None:
        with self._lock, self._connect() as conn:
            conn.executescript(_SCHEMA)

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    # ------------------------------------------------------------------
    # Key/Value state (used to hand off data between pipeline stages)
    # ------------------------------------------------------------------
    def set_state(self, key: str, value: Any) -> None:
        try:
            serialized = json.dumps(value, default=str)
            with self._lock, self._connect() as conn:
                conn.execute(
                    """
                    INSERT INTO kv_state (key, value, updated_at)
                    VALUES (?, ?, ?)
                    ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at
                    """,
                    (key, serialized, self._now()),
                )
            logger.debug("State set: %s", key)
        except (sqlite3.Error, TypeError) as exc:
            logger.exception("Failed to set state for key=%s: %s", key, exc)
            raise

    def get_state(self, key: str, default: Any = None) -> Any:
        try:
            with self._lock, self._connect() as conn:
                row = conn.execute(
                    "SELECT value FROM kv_state WHERE key = ?", (key,)
                ).fetchone()
            if row is None:
                return default
            return json.loads(row["value"])
        except sqlite3.Error as exc:
            logger.exception("Failed to get state for key=%s: %s", key, exc)
            return default

    # ------------------------------------------------------------------
    # Event log (audit trail of what every agent did)
    # ------------------------------------------------------------------
    def log_event(self, agent: str, event_type: str, payload: dict[str, Any]) -> None:
        try:
            with self._lock, self._connect() as conn:
                conn.execute(
                    """
                    INSERT INTO events (agent, event_type, payload, created_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (agent, event_type, json.dumps(payload, default=str), self._now()),
                )
            logger.debug("Event logged: agent=%s type=%s", agent, event_type)
        except sqlite3.Error as exc:
            logger.exception("Failed to log event for agent=%s: %s", agent, exc)

    def get_events(self, agent: Optional[str] = None) -> list[dict[str, Any]]:
        try:
            with self._lock, self._connect() as conn:
                if agent:
                    rows = conn.execute(
                        "SELECT * FROM events WHERE agent = ? ORDER BY id", (agent,)
                    ).fetchall()
                else:
                    rows = conn.execute("SELECT * FROM events ORDER BY id").fetchall()
            return [dict(row) for row in rows]
        except sqlite3.Error as exc:
            logger.exception("Failed to fetch events: %s", exc)
            return []

    # ------------------------------------------------------------------
    # Incident tracking
    # ------------------------------------------------------------------
    def upsert_incident(self, incident_id: str, data: dict[str, Any]) -> None:
        try:
            with self._lock, self._connect() as conn:
                now = self._now()
                conn.execute(
                    """
                    INSERT INTO incidents
                        (incident_id, source_ip, threat_type, severity, risk_score, status, data, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(incident_id) DO UPDATE SET
                        source_ip=excluded.source_ip,
                        threat_type=excluded.threat_type,
                        severity=excluded.severity,
                        risk_score=excluded.risk_score,
                        status=excluded.status,
                        data=excluded.data,
                        updated_at=excluded.updated_at
                    """,
                    (
                        incident_id,
                        data.get("source_ip"),
                        data.get("attack_type"),
                        data.get("severity"),
                        data.get("risk_score"),
                        data.get("response_status", data.get("status", "queued")),
                        json.dumps(data, default=str),
                        now,
                        now,
                    ),
                )
        except sqlite3.Error as exc:
            logger.exception("Failed to upsert incident %s: %s", incident_id, exc)

    def get_incident(self, incident_id: str) -> Optional[dict[str, Any]]:
        with self._lock, self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM incidents WHERE incident_id = ?", (incident_id,)
            ).fetchone()
        if row is None:
            return None
        result = dict(row)
        result["data"] = json.loads(result["data"])
        return result

    def all_incidents(self) -> list[dict[str, Any]]:
        with self._lock, self._connect() as conn:
            rows = conn.execute("SELECT * FROM incidents ORDER BY updated_at DESC").fetchall()
        results = []
        for row in rows:
            item = dict(row)
            item["data"] = json.loads(item["data"])
            results.append(item)
        return results

    def clear(self) -> None:
        """Wipe all tables. Primarily used by tests / fresh pipeline runs."""
        with self._lock, self._connect() as conn:
            conn.execute("DELETE FROM kv_state")
            conn.execute("DELETE FROM events")
            conn.execute("DELETE FROM incidents")
        logger.info("SharedMemory cleared")


# Process-wide singleton so all agents share the same memory instance.
shared_memory = SharedMemory()
