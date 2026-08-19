"""
tests/conftest.py
===================
Shared pytest fixtures. Forces the LLM provider to "none" (heuristic-only)
for all tests so the suite runs deterministically without network access or
API keys, and points shared memory at a temporary SQLite file per test.
"""

from __future__ import annotations

import os

os.environ.setdefault("LLM_PROVIDER", "none")
os.environ.setdefault("DRY_RUN", "true")
os.environ.setdefault("LOG_LEVEL", "WARNING")

import pytest

from memory.shared_memory import SharedMemory


@pytest.fixture()
def fresh_memory(tmp_path, monkeypatch):
    """Provide an isolated SharedMemory instance backed by a temp SQLite file."""
    db_path = tmp_path / "test_shared_memory.db"
    memory = SharedMemory(db_path=db_path)

    # Patch the module-level singleton used by agents so they pick up the
    # isolated instance for the duration of the test.
    import memory.shared_memory as shared_memory_module

    monkeypatch.setattr(shared_memory_module, "shared_memory", memory)
    return memory


@pytest.fixture()
def sample_csv(tmp_path):
    """A small, deterministic network-logs CSV for fast unit tests."""
    content = (
        "log_id,timestamp,source_ip,destination_ip,destination_port,protocol,"
        "user,asset,asset_criticality,bytes_transferred,request_count,payload_snippet,status\n"
        "1,2026-01-01T00:00:00Z,203.0.113.1,10.0.0.1,443,TCP,,web-01,High,1000,10,"
        "\"' OR 1=1 --\",flagged\n"
        "2,2026-01-01T00:01:00Z,203.0.113.2,10.0.0.2,80,TCP,,web-02,Medium,500,5,"
        "\"normal GET /\",normal\n"
        "3,2026-01-01T00:02:00Z,203.0.113.3,10.0.0.3,22,TCP,root,bastion-01,Critical,700,300,"
        "\"300 failed ssh login attempts\",flagged\n"
    )
    path = tmp_path / "logs.csv"
    path.write_text(content, encoding="utf-8")
    return str(path)
