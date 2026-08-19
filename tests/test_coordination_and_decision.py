from agents.analysis_agent import AnalysisAgent
from agents.coordination_agent import CoordinationAgent
from agents.decision_engine import DecisionEngine
from agents.detection_agent import DetectionAgent
from models import ResponseAction


def _build_incidents(sample_csv, fresh_memory):
    detection = DetectionAgent()
    detection.memory = fresh_memory
    detected = detection.run(sample_csv)

    analysis = AnalysisAgent()
    analysis.memory = fresh_memory
    analyzed = analysis.run(detected)

    coordination = CoordinationAgent()
    coordination.memory = fresh_memory
    return coordination.run(analyzed)


def test_incidents_are_ranked_by_risk_score_descending(sample_csv, fresh_memory):
    incidents = _build_incidents(sample_csv, fresh_memory)

    assert len(incidents) == 2
    risk_scores = [i.risk_score for i in incidents]
    assert risk_scores == sorted(risk_scores, reverse=True)
    assert incidents[0].priority_rank == 1
    assert incidents[1].priority_rank == 2


def test_all_incidents_get_unique_ids(sample_csv, fresh_memory):
    incidents = _build_incidents(sample_csv, fresh_memory)
    ids = {i.incident_id for i in incidents}
    assert len(ids) == len(incidents)


def test_decision_engine_chooses_valid_action(sample_csv, fresh_memory):
    incidents = _build_incidents(sample_csv, fresh_memory)

    decision_engine = DecisionEngine()
    decision_engine.memory = fresh_memory
    decisions = decision_engine.run(incidents)

    assert len(decisions) == len(incidents)
    for decision in decisions:
        assert decision.action in list(ResponseAction)
        assert isinstance(decision.requires_human_approval, bool)


def test_critical_bastion_brute_force_gets_block_ip(sample_csv, fresh_memory):
    incidents = _build_incidents(sample_csv, fresh_memory)

    decision_engine = DecisionEngine()
    decision_engine.memory = fresh_memory
    decisions = decision_engine.run(incidents)

    brute_force_incident = next(i for i in incidents if i.log_id == "3")
    decision = next(d for d in decisions if d.incident_id == brute_force_incident.incident_id)
    assert decision.action == ResponseAction.BLOCK_IP
