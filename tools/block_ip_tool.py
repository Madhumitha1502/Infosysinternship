# ----------------------------------------
# Block IP Tool
# ----------------------------------------

def block_ip(ip_address):

    print("\n----------------------------------------")
    print("BLOCK IP TOOL")
    print("----------------------------------------")

    print(f"Blocking IP Address : {ip_address}")

    # Simulated firewall action
    status = "IP Address Blocked Successfully"

    print(status)

    return status


# ----------------------------------------
# Testing
# ----------------------------------------

if __name__ == "__main__":

    block_ip("192.168.1.100")