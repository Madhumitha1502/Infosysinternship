from agents.detection_agent import run_detection
from agents.analysis_agent import run_analysis
from agents.coordination_agent import run_coordination
from agents.decision_agent import run_decision
from agents.response_agent import run_response
from agents.alert_agent import run_alert


def main():

    print("\n" + "=" * 70)
    print("        AI CYBER ATTACK RESPONSE COORDINATOR")
    print("=" * 70)

    try:
        print("\n[1/6] DETECTION AGENT")
        run_detection()
        print("Detection Agent Completed Successfully.\n")

        print("[2/6] ANALYSIS AGENT")
        run_analysis()
        print("Analysis Agent Completed Successfully.\n")

        print("[3/6] COORDINATION AGENT")
        run_coordination()
        print("Coordination Agent Completed Successfully.\n")

        print("[4/6] DECISION AGENT")
        run_decision()
        print("Decision Agent Completed Successfully.\n")

        print("[5/6] RESPONSE AGENT")
        run_response()
        print("Response Agent Completed Successfully.\n")

        print("[6/6] ALERT AGENT")
        run_alert()
        print("Alert Agent Completed Successfully.\n")

        print("=" * 70)
        print("ALL AGENTS EXECUTED SUCCESSFULLY")
        print("CYBER ATTACK RESPONSE PIPELINE COMPLETED")
        print("=" * 70)

    except Exception as error:

        print("\n❌ Pipeline Execution Failed")
        print(f"Reason : {error}")



if __name__ == "__main__":
    main()