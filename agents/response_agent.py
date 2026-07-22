import pandas as pd
import os
from datetime import datetime


# ----------------------------------------
# Execute Response
# ----------------------------------------
def execute_response(decision):

    if decision == "Block Source IP":
        return "IP Successfully Blocked"

    elif decision == "Isolate Device":
        return "Device Successfully Isolated"

    elif decision == "Enable Rate Limiting":
        return "Rate Limiting Enabled"

    elif decision == "Disable Device Access":
        return "Device Access Disabled"

    elif decision == "Continue Monitoring":
        return "Monitoring Started"

    else:
        return "No Action Executed"


# ----------------------------------------
# Response Status
# ----------------------------------------
def response_status(decision):

    if decision == "Continue Monitoring":
        return "Monitoring"

    return "Executed"


# ----------------------------------------
# Response Agent
# ----------------------------------------
def run_response():

    input_file = "data/decision_output.csv"
    output_file = "data/response_output.csv"

    print("=" * 60)
    print("AI CYBER ATTACK RESPONSE COORDINATOR")
    print("RESPONSE AGENT")
    print("=" * 60)

    # Check file
    if not os.path.exists(input_file):
        print("❌ Decision output not found!")
        return None

    # Read decision output
    df = pd.read_csv(input_file)

    if df.empty:
        print("No incidents available.")
        return None

    # Execute Response
    df["ResponseAction"] = df["FinalDecision"].apply(
        execute_response
    )

    # Response Status
    df["ResponseStatus"] = df["FinalDecision"].apply(
        response_status
    )

    # Response Time
    df["ResponseTime"] = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    # Save Output
    df.to_csv(output_file, index=False)

    # Summary
    print("\n✅ Response Executed Successfully!\n")

    print(f"Total Incidents : {len(df)}")

    print("\nResponse Status")
    print(df["ResponseStatus"].value_counts())

    print(f"\nOutput File : {output_file}")

    return output_file


# ----------------------------------------
# Main
# ----------------------------------------
if __name__ == "__main__":
    run_response()