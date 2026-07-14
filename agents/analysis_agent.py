import pandas as pd
import os


def analyze_attack(row):

    if row["FailedLoginAttempts"] >= 10:
        return pd.Series([
            "Brute Force Attack",
            "High",
            "More than 10 failed login attempts."
        ])

    elif row["MalwareDetected"] == "Yes":
        return pd.Series([
            "Malware Attack",
            "Critical",
            "Malware detected in the system."
        ])

    elif row["NetworkTraffic"] == "Very High":
        return pd.Series([
            "DDoS Attack",
            "Critical",
            "Abnormally high network traffic."
        ])

    elif row["Device"] == "Unknown":
        return pd.Series([
            "Unauthorized Device",
            "Medium",
            "Unknown device attempted access."
        ])

    else:
        return pd.Series([
            "Normal Activity",
            "Low",
            "No suspicious activity detected."
        ])


def run_analysis():

    input_file = "data/detected_logs.xlsx"
    output_file = "data/analyzed_logs.xlsx"

    print("=" * 50)
    print("ANALYSIS AGENT")
    print("=" * 50)

    if not os.path.exists(input_file):
        print("❌ Error: detected_logs.xlsx not found!")
        return None

    df = pd.read_excel(input_file)

    df[["AttackType", "Severity", "Reason"]] = df.apply(
        analyze_attack,
        axis=1
    )

    df.to_excel(output_file, index=False)

    print("\nAnalysis Completed Successfully!\n")

    print(f"Total Records : {len(df)}")

    print(f"Output File : {output_file}")

    return output_file


if __name__ == "__main__":
    run_analysis()