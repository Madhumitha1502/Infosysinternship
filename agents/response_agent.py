import pandas as pd
import os
from datetime import datetime
import sys

# Add project root to Python path
sys.path.append(
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..")
    )
)

# ----------------------------------------
# Enterprise Tools
# ----------------------------------------
from tools.block_ip_tool import block_ip
from tools.isolate_device_tool import isolate_device
from tools.rate_limit_tool import enable_rate_limit
from tools.email_alert_tool import send_email_alert


# ----------------------------------------
# Execute Response
# ----------------------------------------
def execute_response(row):

    try:

        decision = row.get("FinalDecision", "")
        attack = row.get("AttackCategory", "")

        if decision == "Block Source IP":

            result = block_ip("192.168.1.100")

        elif decision == "Isolate Device":

            result = isolate_device("DESKTOP-001")

        elif decision == "Enable Rate Limiting":

            result = enable_rate_limit("192.168.1.100")

        elif decision == "Disable Device Access":

            result = isolate_device("UNKNOWN-DEVICE")

        elif decision == "Continue Monitoring":

            result = "Monitoring Started"

        else:

            result = "No Action Executed"

        # Send Email Alert
        if decision != "Continue Monitoring":

            send_email_alert(
                f"{attack} detected. Action Taken: {decision}"
            )

        return result

    except Exception as error:

        return f"Execution Failed : {error}"


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

    # Check Input File
    if not os.path.exists(input_file):

        print("❌ Decision output not found!")
        return None

    # Read Decision Output
    df = pd.read_csv(input_file)

    if df.empty:

        print("No incidents available.")
        return None

    # Execute Enterprise Tools
    df["ResponseAction"] = df.apply(
        execute_response,
        axis=1
    )

    # Response Status
    df["ResponseStatus"] = df["FinalDecision"].apply(
        response_status
    )

    # Response Timestamp
    df["ResponseTime"] = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    # Save Output
    df.to_csv(output_file, index=False)

    # Display Summary
    print("\n✅ Response Execution Completed Successfully!\n")

    print(f"Total Incidents : {len(df)}")

    print("\nResponse Status Distribution")
    print(df["ResponseStatus"].value_counts())

    print(f"\nOutput File : {output_file}")

    return output_file



# Main

if __name__ == "__main__":

    run_response()