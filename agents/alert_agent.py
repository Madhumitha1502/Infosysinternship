import pandas as pd
import os
from datetime import datetime


# ----------------------------------------
# Generate Alert Level
# ----------------------------------------
def generate_alert_level(severity):

    if severity == "Critical":
        return "High"

    elif severity == "High":
        return "Medium"

    elif severity == "Medium":
        return "Low"

    else:
        return "Info"


# ----------------------------------------
# Generate Alert Message
# ----------------------------------------
def generate_alert_message(row):

    attack = row.get("AttackCategory", "")
    decision = row.get("FinalDecision", "")
    severity = row.get("Severity", "")

    return (
        f"{severity} Alert: "
        f"{attack} detected. "
        f"Response Action: {decision}."
    )


# ----------------------------------------
# Alert Agent
# ----------------------------------------
def run_alert():

    input_file = "data/response_output.csv"
    output_file = "data/alert_output.csv"

    print("=" * 60)
    print("AI CYBER ATTACK RESPONSE COORDINATOR")
    print("ALERT AGENT")
    print("=" * 60)

    # Check Input File
    if not os.path.exists(input_file):

        print("❌ Response output not found!")
        return None

    # Read Response Output
    df = pd.read_csv(input_file)

    if df.empty:

        print("No incidents available.")
        return None

    # Alert Level
    df["AlertLevel"] = df["Severity"].apply(
        generate_alert_level
    )

    # Alert Message
    df["AlertMessage"] = df.apply(
        generate_alert_message,
        axis=1
    )

    # Alert Timestamp
    df["AlertTime"] = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    # Save Output
    df.to_csv(output_file, index=False)

    # Summary
    print("\n✅ Alerts Generated Successfully!\n")

    print(f"Total Alerts : {len(df)}")

    print("\nAlert Level Distribution")
    print(df["AlertLevel"].value_counts())

    print(f"\nOutput File : {output_file}")

    return output_file


# ----------------------------------------
# Main
# ----------------------------------------
if __name__ == "__main__":

    run_alert()