from agents.detection_agent import DetectionAgent
from models import ThreatType


def test_detects_sql_injection(sample_csv, fresh_memory):
    agent = DetectionAgent()
    agent.memory = fresh_memory

    events = agent.run(sample_csv)

    sqli_events = [e for e in events if e.attack_type == ThreatType.SQL_INJECTION]
    assert len(sqli_events) == 1
    assert sqli_events[0].is_suspicious is True
    assert sqli_events[0].detection_method == "heuristic"


def test_flags_benign_traffic_as_not_suspicious(sample_csv, fresh_memory):
    agent = DetectionAgent()
    agent.memory = fresh_memory

    events = agent.run(sample_csv)

    benign = next(e for e in events if e.log_id == "2")
    assert benign.is_suspicious is False
    assert benign.attack_type == ThreatType.BENIGN


def test_detects_brute_force_from_volumetric_signature(sample_csv, fresh_memory):
    agent = DetectionAgent()
    agent.memory = fresh_memory

    events = agent.run(sample_csv)

    brute_force = next(e for e in events if e.log_id == "3")
    assert brute_force.is_suspicious is True
    assert brute_force.attack_type == ThreatType.BRUTE_FORCE


def test_returns_full_row_count(sample_csv, fresh_memory):
    agent = DetectionAgent()
    agent.memory = fresh_memory

    events = agent.run(sample_csv)
    assert len(events) == 3
