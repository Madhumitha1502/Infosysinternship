import pandas as pd
import os


def generate_alert(row):

    if row["ResponseStatus"] == "Executed":

        return pd.Series([
            "Alert Sent",
            f"Security Alert: {row['AttackType']} detected. "
            f"Action Taken: {row['RecommendedAction']}."
        ])

    else:

        return pd.Series([
            "No Alert",
            "No alert required."
        ])


def run_alert():

    input_file = "data/response_logs.xlsx"
    output_file = "data/alert_logs.xlsx"

    print("=" * 50)
    print("ALERT AGENT")
    print("=" * 50)

    if not os.path.exists(input_file):
        print("❌ Error: response_logs.xlsx not found!")
        return None

    df = pd.read_excel(input_file)

    df[["AlertStatus", "AlertMessage"]] = df.apply(
        generate_alert,
        axis=1
    )

    df.to_excel(output_file, index=False)

    print("\nAlert Generation Completed Successfully!\n")

    print(f"Total Records : {len(df)}")

    print(f"Output File : {output_file}")

    return output_file


if __name__ == "__main__":
    run_alert()