import pandas as pd
import os


def decide_action(row):

    if row["AttackType"] == "Brute Force Attack":
        return "Block IP Address"

    elif row["AttackType"] == "Malware Attack":
        return "Quarantine Device"

    elif row["AttackType"] == "DDoS Attack":
        return "Enable Firewall Protection"

    elif row["AttackType"] == "Unauthorized Device":
        return "Disconnect Unknown Device"

    else:
        return "No Action Required"


def run_decision():

    input_file = "data/analyzed_logs.xlsx"
    output_file = "data/decision_logs.xlsx"

    print("=" * 50)
    print("DECISION AGENT")
    print("=" * 50)

    if not os.path.exists(input_file):
        print("❌ Error: analyzed_logs.xlsx not found!")
        return None

    df = pd.read_excel(input_file)

    df["RecommendedAction"] = df.apply(decide_action, axis=1)

    df.to_excel(output_file, index=False)

    print("\nDecision Making Completed Successfully!\n")

    print(f"Total Records : {len(df)}")

    print(f"Output File : {output_file}")

    return output_file


if __name__ == "__main__":
    run_decision()