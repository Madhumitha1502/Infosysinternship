import pandas as pd
import random
import time
import os
from datetime import datetime

# ===========================================
# Create logs folder if it doesn't exist
# ===========================================

os.makedirs("logs", exist_ok=True)

# CSV file path
LOG_FILE = "logs/live_logs.csv"

# ===========================================
# Sample Data
# ===========================================

ip_addresses = [
    "192.168.1.10",
    "192.168.1.20",
    "192.168.1.30",
    "192.168.1.40",
    "192.168.1.50"
]

devices = [
    "Laptop",
    "Desktop",
    "Mobile",
    "Unknown"
]

network_traffic = [
    "Low",
    "Medium",
    "High",
    "Very High"
]

malware = [
    "Yes",
    "No"
]

# ===========================================
# Generate One Random Cyber Log
# ===========================================

def generate_log():

    failed = random.randint(0, 15)
    mal = random.choice(malware)
    traffic = random.choice(network_traffic)
    device = random.choice(devices)

    # Decide Attack Type
    if failed >= 10:
        attack = "Brute Force"

    elif mal == "Yes":
        attack = "Malware"

    elif traffic == "Very High":
        attack = "DDoS"

    elif device == "Unknown":
        attack = "Unauthorized Device"

    else:
        attack = "Normal"

    log = {
        "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "IPAddress": random.choice(ip_addresses),
        "FailedLoginAttempts": failed,
        "MalwareDetected": mal,
        "NetworkTraffic": traffic,
        "Device": device,
        "AttackType": attack
    }

    return log

# ===========================================
# Save Log into CSV
# ===========================================

def save_log(log):

    df = pd.DataFrame([log])

    if os.path.exists(LOG_FILE):
        df.to_csv(LOG_FILE, mode="a", header=False, index=False)
    else:
        df.to_csv(LOG_FILE, index=False)

# ===========================================
# Main Program
# ===========================================

if __name__ == "__main__":

    print("=" * 60)
    print(" LIVE CYBER LOG GENERATOR STARTED ")
    print("=" * 60)

    while True:

        log = generate_log()

        save_log(log)

        print(log)

        time.sleep(5)