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

    input_file = "data/cyber_logs_50_records.xlsx"
    output_file = "data/detected_logs.xlsx"

    print("=" * 50)
    print("DETECTION AGENT")
    print("=" * 50)

    # Check if dataset exists
    if not os.path.exists(input_file):
        print("❌ Error: Input file not found!")
        return None

    # Read dataset
    df = pd.read_excel(input_file)

    # Apply detection rules
    df["DetectionResult"] = df.apply(detect_activity, axis=1)

    # Count results
    suspicious = (df["DetectionResult"] == "Suspicious").sum()
    normal = (df["DetectionResult"] == "Normal").sum()

    # Save output
    df.to_excel(output_file, index=False)

    # Display summary
    print("\nDetection Completed Successfully!\n")
    print(f"Total Records      : {len(df)}")
    print(f"Suspicious Records : {suspicious}")
    print(f"Normal Records     : {normal}")

    print(f"\nOutput File : {output_file}")

    # Return output for next agent
    return output_file


# Run only if this file is executed directly
if __name__ == "__main__":
    run_detection()