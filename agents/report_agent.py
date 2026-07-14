import pandas as pd
import os


def execute_response(row):

    action = row["RecommendedAction"]

    if action == "Block IP Address":
        return pd.Series([
            "Executed",
            "Attacker IP blocked successfully."
        ])

    elif action == "Quarantine Device":
        return pd.Series([
            "Executed",
            "Device isolated from the network."
        ])

    elif action == "Enable Firewall Protection":
        return pd.Series([
            "Executed",
            "Firewall rules updated successfully."
        ])

    elif action == "Disconnect Unknown Device":
        return pd.Series([
            "Executed",
            "Unknown device disconnected."
        ])

    else:
        return pd.Series([
            "No Action",
            "No response required."
        ])


def run_response():

    input_file = "data/decision_logs.xlsx"
    output_file = "data/response_logs.xlsx"

    print("=" * 50)
    print("RESPONSE AGENT")
    print("=" * 50)

    if not os.path.exists(input_file):
        print("❌ Error: decision_logs.xlsx not found!")
        return None

    df = pd.read_excel(input_file)

    df[["ResponseStatus", "ResponseMessage"]] = df.apply(
        execute_response,
        axis=1
    )

    df.to_excel(output_file, index=False)

    print("\nResponse Execution Completed Successfully!\n")

    print(f"Total Records : {len(df)}")

    print(f"Output File : {output_file}")

    return output_file


if __name__ == "__main__":
    run_response()