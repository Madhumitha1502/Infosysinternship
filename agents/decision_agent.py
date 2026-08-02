import pandas as pd
import os
from datetime import datetime



# Select Final Decision

def select_decision(attack, priority):

    try:

        if attack == "Malware":
            return "Isolate Device"

        elif attack == "Brute Force":
            return "Block Source IP"

        elif attack == "DDoS":
            return "Enable Rate Limiting"

        elif attack == "Unauthorized Device":
            return "Disable Device Access"

        else:
            return "Continue Monitoring"

    except Exception:
        return "Continue Monitoring"


# ----------------------------------------
# Select Enterprise Tool
# ----------------------------------------
def select_tool(decision):

    tool_mapping = {

        "Block Source IP": "Block IP Tool",

        "Isolate Device": "Isolate Device Tool",

        "Enable Rate Limiting": "Rate Limit Tool",

        "Disable Device Access": "Isolate Device Tool",

        "Continue Monitoring": "Monitoring Service"

    }

    return tool_mapping.get(decision, "Unknown Tool")


# ----------------------------------------
# Assign Execution Status
# ----------------------------------------
def assign_status(priority):

    if priority in ["P1", "P2"]:
        return "Approved"

    elif priority == "P3":
        return "Monitoring"

    else:
        return "Low Priority"


# ----------------------------------------
# Decision Engine
# ----------------------------------------
def run_decision():

    input_file = "data/coordinated_tasks.csv"
    output_file = "data/decision_output.csv"

    print("=" * 60)
    print("AI CYBER ATTACK RESPONSE COORDINATOR")
    print("DECISION AGENT")
    print("=" * 60)

    # Check Input File
    if not os.path.exists(input_file):

        print("❌ Coordination output not found!")
        return None

    # Read Data
    df = pd.read_csv(input_file)

    if df.empty:

        print("No incidents available.")
        return None

    # Final Decision
    df["FinalDecision"] = df.apply(

        lambda row: select_decision(

            row.get("AttackCategory", ""),

            row.get("Priority", "")

        ),

        axis=1

    )

    # Enterprise Tool Selection
    df["SelectedTool"] = df["FinalDecision"].apply(

        select_tool

    )

    # Execution Status
    df["ExecutionStatus"] = df["Priority"].apply(

        assign_status

    )

    # Decision Timestamp
    df["DecisionTime"] = datetime.now().strftime(

        "%Y-%m-%d %H:%M:%S"

    )

    # Save Output
    df.to_csv(output_file, index=False)

    # Summary
    print("\n✅ Decision Completed Successfully!\n")

    print(f"Total Incidents : {len(df)}")

    print("\nExecution Status Distribution")
    print(df["ExecutionStatus"].value_counts())

    print("\nSelected Tool Distribution")
    print(df["SelectedTool"].value_counts())

    print("\nFinal Decision Distribution")
    print(df["FinalDecision"].value_counts())

    print(f"\nOutput File : {output_file}")

    return output_file


# ----------------------------------------
# Main
# ----------------------------------------
if __name__ == "__main__":

    run_decision()