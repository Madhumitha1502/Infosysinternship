from agents.analysis_agent import AnalysisAgent
from agents.detection_agent import DetectionAgent
from models import Severity


def test_analysis_assigns_severity_and_mitre(sample_csv, fresh_memory):
    detection = DetectionAgent()
    detection.memory = fresh_memory
    detected = detection.run(sample_csv)

    analysis = AnalysisAgent()
    analysis.memory = fresh_memory
    analyzed = analysis.run(detected)

    # Only suspicious events should be carried into analysis.
    assert len(analyzed) == 2
    for event in analyzed:
        assert event.severity in list(Severity)
        assert event.mitre_attack_technique
        assert 0.0 <= event.confidence <= 1.0


def test_critical_asset_bumps_severity(sample_csv, fresh_memory):
    detection = DetectionAgent()
    detection.memory = fresh_memory
    detected = detection.run(sample_csv)

    analysis = AnalysisAgent()
    analysis.memory = fresh_memory
    analyzed = analysis.run(detected)

    brute_force_event = next(e for e in analyzed if e.log_id == "3")
    # asset_criticality=Critical should bump severity up from the Medium baseline.
    assert brute_force_event.severity in (Severity.HIGH, Severity.CRITICAL)
