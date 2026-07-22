import pandas as pd
import os
from datetime import datetime


# ----------------------------------------
# Report Agent
# ----------------------------------------
def run_report():

    input_file = "data/alert_output.csv"
    output_file = "data/final_report.csv"

    print("=" * 60)
    print("AI CYBER ATTACK RESPONSE COORDINATOR")
    print("REPORT AGENT")
    print("=" * 60)

    # Check Input File
    if not os.path.exists(input_file):
        print("❌ Alert output not found!")
        return None

    df = pd.read_csv(input_file)

    if df.empty:
        print("No incidents available.")
        return None

    # ----------------------------------------
    # Summary
    # ----------------------------------------

    total_incidents = len(df)

    attack_summary = (
        df["AttackCategory"]
        .value_counts()
        .to_dict()
    )

    severity_summary = (
        df["Severity"]
        .value_counts()
        .to_dict()
    )

    tool_summary = (
        df["SelectedTool"]
        .value_counts()
        .to_dict()
    )

    response_summary = (
        df["ResponseStatus"]
        .value_counts()
        .to_dict()
    )

    alert_summary = (
        df["AlertLevel"]
        .value_counts()
        .to_dict()
    )

    report = {
        "Report Generated On": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Total Incidents": total_incidents,
        "Attack Summary": str(attack_summary),
        "Severity Summary": str(severity_summary),
        "Tool Usage Summary": str(tool_summary),
        "Response Summary": str(response_summary),
        "Alert Summary": str(alert_summary)
    }

    report_df = pd.DataFrame([report])

    report_df.to_csv(output_file, index=False)

    # ----------------------------------------
    # Console Output
    # ----------------------------------------

    print("\n✅ Final Report Generated Successfully!\n")

    print(f"Total Incidents : {total_incidents}")

    print("\nAttack Categories")
    print(df["AttackCategory"].value_counts())

    print("\nSeverity Distribution")
    print(df["Severity"].value_counts())

    print("\nTool Usage")
    print(df["SelectedTool"].value_counts())

    print("\nAlert Levels")
    print(df["AlertLevel"].value_counts())

    print(f"\nOutput File : {output_file}")

    return output_file


# ----------------------------------------
# Main
# ----------------------------------------

if __name__ == "__main__":
    run_report()