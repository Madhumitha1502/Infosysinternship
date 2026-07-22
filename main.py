from agents.detection_agent import run_detection
from agents.analysis_agent import run_analysis
from agents.coordination_agent import run_coordination
from agents.decision_agent import run_decision
from agents.response_agent import run_response
from agents.alert_agent import run_alert
from agents.report_agent import run_report


def main():

    print("\n" + "=" * 70)
    print("        AI CYBER ATTACK RESPONSE COORDINATOR")
    print("=" * 70)

    print("\n[1/7] DETECTION AGENT")
    detection = run_detection()

    if detection is None:
        return

    print("\nDetection Agent Completed Successfully.")

    print("\n[2/7] ANALYSIS AGENT")
    analysis = run_analysis()

    if analysis is None:
        return

    print("\nAnalysis Agent Completed Successfully.")

    print("\n[3/7] COORDINATION AGENT")
    coordination = run_coordination()

    if coordination is None:
        return

    print("\nCoordination Agent Completed Successfully.")

    print("\n[4/7] DECISION AGENT")
    decision = run_decision()

    if decision is None:
        return

    print("\nDecision Agent Completed Successfully.")

    print("\n[5/7] RESPONSE AGENT")
    response = run_response()

    if response is None:
        return

    print("\nResponse Agent Completed Successfully.")

    print("\n[6/7] ALERT AGENT")
    alert = run_alert()

    if alert is None:
        return

    print("\nAlert Agent Completed Successfully.")

    print("\n[7/7] REPORT AGENT")
    report = run_report()

    if report is None:
        return

    print("\nReport Agent Completed Successfully.")

    print("\n" + "=" * 70)
    print(" ALL AGENTS EXECUTED SUCCESSFULLY")
    print(" AI CYBER ATTACK RESPONSE PIPELINE COMPLETED")
    print("=" * 70)


if __name__ == "__main__":
    main()