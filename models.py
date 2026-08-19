"""
models.py
=========
Shared Pydantic models used across agents, the FastAPI layer, and CSV/JSON
serialization. Centralizing these avoids subtle field-name drift between
pipeline stages.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class ThreatType(str, Enum):
    SQL_INJECTION = "SQL Injection"
    BRUTE_FORCE = "Brute Force"
    DDOS = "DDoS"
    PORT_SCANNING = "Port Scanning"
    MALWARE = "Malware"
    RANSOMWARE = "Ransomware"
    PHISHING = "Phishing"
    PRIVILEGE_ESCALATION = "Privilege Escalation"
    BENIGN = "Benign"
    UNKNOWN = "Unknown"


class Severity(str, Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"


class ResponseAction(str, Enum):
    BLOCK_IP = "block_ip"
    ISOLATE_DEVICE = "isolate_device"
    DISABLE_USER = "disable_user"
    RATE_LIMIT = "rate_limit"
    GENERATE_FIREWALL_RULE = "generate_firewall_rule"
    QUARANTINE_DEVICE = "quarantine_device"
    MONITOR_ONLY = "monitor_only"


class NetworkLogEntry(BaseModel):
    log_id: str
    timestamp: str
    source_ip: str
    destination_ip: str
    destination_port: Optional[int] = None
    protocol: Optional[str] = None
    user: Optional[str] = None
    asset: Optional[str] = None
    asset_criticality: Optional[str] = "Medium"
    bytes_transferred: Optional[int] = None
    request_count: Optional[int] = None
    payload_snippet: Optional[str] = None
    status: Optional[str] = None


class DetectedEvent(NetworkLogEntry):
    is_suspicious: bool
    attack_type: ThreatType
    detection_method: str  # "heuristic" | "llm"
    detection_reasoning: str = ""


class AnalyzedEvent(DetectedEvent):
    severity: Severity
    confidence: float = Field(ge=0.0, le=1.0)
    impact: str
    mitre_attack_technique: str
    analysis_method: str  # "heuristic" | "llm"


class CoordinatedIncident(AnalyzedEvent):
    incident_id: str
    risk_score: float
    priority_rank: Optional[int] = None


class Decision(BaseModel):
    incident_id: str
    action: ResponseAction
    justification: str
    requires_human_approval: bool
    decision_method: str  # "heuristic" | "llm"


class ResponseResult(BaseModel):
    incident_id: str
    action: ResponseAction
    status: str
    success: bool
    details: dict = Field(default_factory=dict)
    runbook_note: str = ""


class AlertRecord(BaseModel):
    incident_id: str
    channel: str  # "email" | "slack" | "json"
    status: str
    success: bool
    message: str = ""
