# ----------------------------------------
# Email Alert Tool
# ----------------------------------------

def send_email_alert(alert_message):

    print("\n----------------------------------------")
    print("EMAIL ALERT TOOL")
    print("----------------------------------------")

    print("Sending Email Alert...")
    print(f"Message : {alert_message}")

    status = "Email Alert Sent Successfully"

    print(status)

    return status


# ----------------------------------------
# Testing
# ----------------------------------------

if __name__ == "__main__":

    send_email_alert("Critical Malware Attack Detected")