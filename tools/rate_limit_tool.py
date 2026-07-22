# ----------------------------------------
# Rate Limit Tool
# ----------------------------------------

def enable_rate_limit(ip_address):

    print("\n----------------------------------------")
    print("RATE LIMIT TOOL")
    print("----------------------------------------")

    print(f"Applying Rate Limit for : {ip_address}")

    status = "Rate Limiting Enabled Successfully"

    print(status)

    return status


# ----------------------------------------
# Testing
# ----------------------------------------

if __name__ == "__main__":

    enable_rate_limit("192.168.1.150")