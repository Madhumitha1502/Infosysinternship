import pandas as pd
import os
from datetime import datetime


# ----------------------------------------
# Alert Level
# ----------------------------------------
def get_alert_level(priority):

    if priority == "P1":
        return "High"

    elif priority == "P2":
        return "Medium"

    else:
        return "Low"


# ----------------------------------------
# Generate Alert Message
# ----------------------------------------
def generate_alert_message(row):

    attack = row["AttackCategory"]
    priority = row["Priority"]
    decision = row["FinalDecision"]

    return (
        f"{attack} detected | "
        f"Priority: {priority} | "
        f"Action: {decision}"
    )


# ----------------------------------------
# Alert Status
# ----------------------------------------
def alert_status():

    return "Sent"


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

    # Check file
    if not os.path.exists(input_file):
        print("❌ Response output not found!")
        return None

    # Read response output
    df = pd.read_csv(input_file)

    if df.empty:
        print("No incidents available.")
        return None

    # Alert Level
    df["AlertLevel"] = df["Priority"].apply(get_alert_level)

    # Alert Message
    df["AlertMessage"] = df.apply(
        generate_alert_message,
        axis=1
    )

    # Alert Status
    df["AlertStatus"] = alert_status()

    # Alert Time
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