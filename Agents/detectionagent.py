import pandas as pd
import os

# File Paths

input_file = "data/cyber_logs_50_records.xlsx"
output_file = "data/detected_logs.xlsx"


# Check if Input File Exists

if not os.path.exists(input_file):
    print("❌ Error: Input file not found!")
    exit()


# Read Excel File

df = pd.read_excel(input_file)

print("=======================================")
print(" AI Cyber Attack Response Coordinator ")
print(" Detection Agent Started ")
print("=======================================\n")


# Detection Function

def detect_activity(row):

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



# Apply Detection Rules

df["DetectionResult"] = df.apply(detect_activity, axis=1)


# Count Results

suspicious = (df["DetectionResult"] == "Suspicious").sum()
normal = (df["DetectionResult"] == "Normal").sum()


# Save Output

df.to_excel(output_file, index=False)


# Console Output

print("Detection Completed Successfully!\n")

print(f"Total Records       : {len(df)}")
print(f"Suspicious Records  : {suspicious}")
print(f"Normal Records      : {normal}")

print("\nDetected Logs Saved As:")
print(output_file)

print("\nFirst Five Records:\n")
print(df.head())