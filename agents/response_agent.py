import pandas as pd
import os


def run_report():

    input_file = "data/alert_logs.xlsx"
    output_file = "data/final_incident_report.xlsx"

    print("=" * 50)
    print("REPORT AGENT")
    print("=" * 50)

    if not os.path.exists(input_file):
        print("❌ Error: alert_logs.xlsx not found!")
        return None

    df = pd.read_excel(input_file)

    total_records = len(df)
    suspicious_records = (df["DetectionResult"] == "Suspicious").sum()
    normal_records = (df["DetectionResult"] == "Normal").sum()

    print("\nGenerating Incident Report...\n")

    print(f"Total Records       : {total_records}")
    print(f"Suspicious Records  : {suspicious_records}")
    print(f"Normal Records      : {normal_records}")

    df.to_excel(output_file, index=False)

    print("\nIncident Report Generated Successfully!")

    print(f"\nReport Saved As : {output_file}")

    return output_file


if __name__ == "__main__":
    run_report()