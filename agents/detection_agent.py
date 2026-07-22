import pandas as pd
import os


def detect_activity(row):
    """
    Detect suspicious cyber activities based on predefined rules.
    """

    # Rule 1 - Brute Force Detection
    if row["FailedLoginAttempts"] >= 10:
        return "Suspicious"

    # Rule 2 - Malware Detection
    elif row["MalwareDetected"] == "Yes":
        return "Suspicious"

    # Rule 3 - DDoS Detection
    elif row["NetworkTraffic"] == "Very High":
        return "Suspicious"

    # Rule 4 - Unauthorized Device
    elif row["Device"] == "Unknown":
        return "Suspicious"

    else:
        return "Normal"


def run_detection():

    input_file = "logs/live_logs.csv"
    output_file = "data/detected_logs.csv"

    print("=" * 50)
    print("DETECTION AGENT")
    print("=" * 50)

    # Check if input file exists
    if not os.path.exists(input_file):
        print("❌ Error: Input file not found!")
        return None

    # Create data folder if it doesn't exist
    os.makedirs("data", exist_ok=True)

    # Read CSV file
    df = pd.read_csv(input_file)

    # Apply detection rules
    df["DetectionResult"] = df.apply(detect_activity, axis=1)

    # Count results
    suspicious = (df["DetectionResult"] == "Suspicious").sum()
    normal = (df["DetectionResult"] == "Normal").sum()

    # Save output
    df.to_csv(output_file, index=False)

    # Print summary
    print("\n✅ Detection Completed Successfully!\n")
    print(f"Total Records      : {len(df)}")
    print(f"Suspicious Records : {suspicious}")
    print(f"Normal Records     : {normal}")

    print(f"\nOutput File : {output_file}")

    return output_file


if __name__ == "__main__":
    run_detection()