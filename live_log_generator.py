import pandas as pd
import random
import time
import os
from datetime import datetime

# File path
LOG_FILE = "logs/live_logs.csv"

# Sample Data
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


def generate_log():
    """
    Generate a single random cyber log.
    """

    log = {
        "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "IPAddress": random.choice(ip_addresses),
        "FailedLoginAttempts": random.randint(0, 15),
        "MalwareDetected": random.choice(malware),
        "NetworkTraffic": random.choice(network_traffic),
        "Device": random.choice(devices)
    }

    return log


def save_log(log):
    """
    Save generated log into CSV file.
    """

    df = pd.DataFrame([log])

    if os.path.exists(LOG_FILE):
        df.to_csv(LOG_FILE, mode="a", header=False, index=False)
    else:
        df.to_csv(LOG_FILE, index=False)


def start_generator():
    """
    Continuously generate logs every 2 seconds.
    """

    print("=" * 50)
    print("LIVE CYBER LOG GENERATOR STARTED")
    print("=" * 50)

    while True:

        new_log = generate_log()

        save_log(new_log)

        print("New Log Generated:")
        print(new_log)
        print("-" * 50)

        time.sleep(2)


if __name__ == "__main__":
    start_generator()