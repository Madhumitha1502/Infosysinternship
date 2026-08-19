from agents.analysis_agent import AnalysisAgent
from agents.coordination_agent import CoordinationAgent
from agents.decision_engine import DecisionEngine
from agents.detection_agent import DetectionAgent
from agents.response_agent import ResponseAgent
from tools.block_ip import block_ip
from tools.isolate_device import isolate_device
from tools.rate_limit import rate_limit


def test_block_ip_tool_dry_run_returns_simulated_status():
    result = block_ip("203.0.113.1", "unit test")
    assert result["success"] is True
    assert result["status"] == "simulated"
    assert result["ip_address"] == "203.0.113.1"


def test_isolate_device_tool_dry_run_returns_simulated_status():
    result = isolate_device("workstation-01", "unit test")
    assert result["success"] is True
    assert result["status"] == "simulated"


def test_rate_limit_tool_dry_run_returns_simulated_status():
    result = rate_limit("203.0.113.2", 30, "unit test")
    assert result["success"] is True
    assert result["requests_per_minute"] == 30


def test_response_agent_executes_full_pipeline(sample_csv, fresh_memory):
    detection = DetectionAgent()
    detection.memory = fresh_memory
    detected = detection.run(sample_csv)

    analysis = AnalysisAgent()
    analysis.memory = fresh_memory
    analyzed = analysis.run(detected)

    coordination = CoordinationAgent()
    coordination.memory = fresh_memory
    incidents = coordination.run(analyzed)

    decision_engine = DecisionEngine()
    decision_engine.memory = fresh_memory
    decisions = decision_engine.run(incidents)

    response_agent = ResponseAgent()
    response_agent.memory = fresh_memory
    results = response_agent.run(incidents, decisions)

    assert len(results) == len(decisions)
    for result in results:
        assert result.status in {"simulated", "executed", "pending_approval", "monitoring", "error"}
