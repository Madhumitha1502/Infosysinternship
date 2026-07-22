import pandas as pd
import os
from datetime import datetime


# ----------------------------------------
# Assign Priority Based on Risk Score
# ----------------------------------------
def assign_priority(risk_score):

    if risk_score >= 90:
        return "P1"

    elif risk_score >= 70:
        return "P2"

    elif risk_score >= 40:
        return "P3"

    else:
        return "P4"


# ----------------------------------------
# Assign Next Agent
# ----------------------------------------
def assign_agent(attack):

    if attack in [
        "Brute Force",
        "Malware",
        "DDoS",
        "Unauthorized Device"
    ]:
        return "Decision Agent"

    return "No Action"


# ----------------------------------------
# Workflow Status
# ----------------------------------------
def workflow_status(agent):

    if agent == "Decision Agent":
        return "Pending"

    return "Completed"


# ----------------------------------------
# Coordination Engine
# ----------------------------------------
def run_coordination():

    input_file = "data/analyzed_logs.csv"
    output_file = "data/coordinated_tasks.csv"

    print("=" * 60)
    print("AI CYBER ATTACK RESPONSE COORDINATOR")
    print("COORDINATION AGENT")
    print("=" * 60)

    if not os.path.exists(input_file):
        print("❌ Analysis output not found!")
        return None

    df = pd.read_csv(input_file)

    if df.empty:
        print("No incidents found.")
        return None

    # New Columns
    df["Priority"] = df["RiskScore"].apply(assign_priority)

    df["AssignedAgent"] = df["AttackCategory"].apply(assign_agent)

    df["WorkflowStatus"] = df["AssignedAgent"].apply(workflow_status)

    df["CoordinatorTimestamp"] = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    # Priority Order
    priority_order = {
        "P1": 1,
        "P2": 2,
        "P3": 3,
        "P4": 4
    }

    df["PriorityOrder"] = df["Priority"].map(priority_order)

    df = df.sort_values(by="PriorityOrder")

    df.drop(columns=["PriorityOrder"], inplace=True)

    # Save Output
    df.to_csv(output_file, index=False)

    print("\n✅ Coordination Completed Successfully!\n")

    print(f"Total Incidents : {len(df)}")

    print("\nPriority Distribution")
    print(df["Priority"].value_counts())

    print("\nAssigned Agent Distribution")
    print(df["AssignedAgent"].value_counts())

    print(f"\nOutput File : {output_file}")

    return output_file


# ----------------------------------------
# Main
# ----------------------------------------
if __name__ == "__main__":
    run_coordination()