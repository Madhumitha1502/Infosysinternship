from agents.detection_agent import run_detection
from agents.analysis_agent import run_analysis
from agents.decision_agent import run_decision
from agents.response_agent import run_response
from agents.alert_agent import run_alert
from agents.report_agent import run_report


class CoordinationAgent:

    def __init__(self):
        print("=" * 60)
        print(" AI AGENTS COORDINATION & DECISION ENGINE ")
        print("=" * 60)

    def orchestrate(self):

        print("\nStarting AI Workflow...\n")

        # Step 1
        print("Running Detection Agent...")
        detected_file = run_detection()

        # Step 2
        print("\nRunning Analysis Agent...")
        analyzed_file = run_analysis()

        # Step 3
        print("\nRunning Decision Agent...")
        decision_file = run_decision()

        # Step 4
        print("\nRunning Response Agent...")
        response_file = run_response()

        # Step 5
        print("\nRunning Alert Agent...")
        alert_file = run_alert()

        # Step 6
        print("\nRunning Report Agent...")
        report_file = run_report()

        print("\n====================================")
        print("AI Workflow Completed Successfully")
        print("====================================")

        print("\nFinal Report Generated:")
        print(report_file)