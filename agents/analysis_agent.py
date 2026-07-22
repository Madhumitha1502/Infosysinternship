import pandas as pd
import os


# -----------------------------
# Severity Calculation
# -----------------------------
def calculate_severity(row):

    score = 0

    if row["FailedLoginAttempts"] >= 10:
        score += 2

    if row["MalwareDetected"] == "Yes":
        score += 2

    if row["NetworkTraffic"] == "Very High":
        score += 2

    if row["Device"] == "Unknown":
        score += 2

    if score >= 6:
        return "Critical"

    elif score >= 4:
        return "High"

    elif score >= 2:
        return "Medium"

    else:
        return "Low"


# -----------------------------
# Attack Identification
# -----------------------------
def identify_attack(row):

    if row["FailedLoginAttempts"] >= 10:
        return "Brute Force"

    elif row["MalwareDetected"] == "Yes":
        return "Malware"

    elif row["NetworkTraffic"] == "Very High":
        return "DDoS"

    elif row["Device"] == "Unknown":
        return "Unauthorized Device"

    else:
        return "Normal"


# -----------------------------
# Risk Score
# -----------------------------
def calculate_risk_score(severity):

    risk = {
        "Critical": 95,
        "High": 80,
        "Medium": 60,
        "Low": 30
    }

    return risk.get(severity, 0)


# -----------------------------
# Recommended Action
# -----------------------------
def recommend_action(attack):

    actions = {
        "Brute Force": "Block Source IP",
        "Malware": "Isolate Device",
        "DDoS": "Enable Rate Limiting",
        "Unauthorized Device": "Verify Device",
        "Normal": "Continue Monitoring"
    }

    return actions.get(attack, "Continue Monitoring")


# -----------------------------
# Main Analysis Function
# -----------------------------
def run_analysis():

    input_file = "data/detected_logs.csv"
    output_file = "data/analyzed_logs.csv"

    print("=" * 60)
    print("AI CYBER ATTACK RESPONSE COORDINATOR")
    print("ANALYSIS AGENT")
    print("=" * 60)

    if not os.path.exists(input_file):
        print("❌ Detection output not found!")
        return None

    df = pd.read_csv(input_file)

    # Analyse only suspicious incidents
    suspicious_df = df[df["DetectionResult"] == "Suspicious"].copy()

    if suspicious_df.empty:
        print("No suspicious incidents found.")
        return None

    # Perform Analysis
    suspicious_df["Severity"] = suspicious_df.apply(
        calculate_severity,
        axis=1
    )

    suspicious_df["AttackCategory"] = suspicious_df.apply(
        identify_attack,
        axis=1
    )

    suspicious_df["RiskScore"] = suspicious_df["Severity"].apply(
        calculate_risk_score
    )

    suspicious_df["RecommendedAction"] = suspicious_df[
        "AttackCategory"
    ].apply(recommend_action)

    # Save Output
    suspicious_df.to_csv(output_file, index=False)

    # Display Summary
    print("\nAnalysis Completed Successfully!\n")

    print(f"Total Suspicious Incidents : {len(suspicious_df)}")

    print("\nSeverity Distribution")
    print(suspicious_df["Severity"].value_counts())

    print("\nAttack Categories")
    print(suspicious_df["AttackCategory"].value_counts())

    print(f"\nOutput File : {output_file}")

    return output_file


# -----------------------------
# Program Entry Point
# -----------------------------
if __name__ == "__main__":
    run_analysis()