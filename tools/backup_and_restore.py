import argparse
from pymodbus.client import ModbusTcpClient
import os
from colorama import init, Fore, Style

# Initialize colorama
init()

REGISTER_COUNT = 218           # Registers 0 to 217
BACKUP_FILENAME = "modbus_backup.txt"
RESTORE_START = 20             # Only restore registers 20 to 217

def check_device_online(ip, slave_id):
    """Check if a Modbus device is online and responding."""
    client = ModbusTcpClient(ip)
    if not client.connect():
        print(f"{Fore.RED}{Style.BRIGHT}Failed to connect to device at {ip}{Style.RESET_ALL}")
        return False
    
    # Try to read first register to verify communication
    result = client.read_holding_registers(0, count=1, slave=slave_id)
    client.close()
    
    if result.isError():
        print(f"{Fore.RED}{Style.BRIGHT}Device at {ip} (slave ID: {slave_id}) is not responding properly{Style.RESET_ALL}")
        return False
    
    print(f"{Fore.GREEN}{Style.BRIGHT}Device at {ip} (slave ID: {slave_id}) is online and responding{Style.RESET_ALL}")
    return True

REGISTER_COUNT = 218           # Registers 0 to 217
BACKUP_FILENAME = "modbus_backup.txt"
RESTORE_START = 20             # Only restore registers 20 to 217

def read_registers(client, slave_id):
    all_values = [None] * REGISTER_COUNT
    for i in range(0, 210, 10):  # Read in chunks of 10
        result = client.read_holding_registers(i, count=10, slave=slave_id)
        if result.isError():
            print(f"Error reading registers {i}–{i+9}: {result}")
            continue
        all_values[i:i+10] = result.registers

    # Read remaining 8 registers (210–217)
    result = client.read_holding_registers(210, count=8, slave=slave_id)
    if not result.isError():
        all_values[210:218] = result.registers
    else:
        print(f"Error reading registers 210–217: {result}")

    return all_values

def write_registers(client, slave_id, values):
    for i in range(RESTORE_START, 210, 10):
        chunk = values[i:i+10]
        if None in chunk:
            print(f"Skipping write to {i}–{i+9} due to missing data.")
            continue
        client.write_registers(i, chunk, slave=slave_id)

    last_chunk = values[210:218]
    if None not in last_chunk:
        client.write_registers(210, last_chunk, slave=slave_id)
    else:
        print("Skipping write to 210–217 due to missing data.")

def backup_registers():
    device_ip = input("Enter Modbus device IP address: ")
    slave_id = int(input("Enter Modbus slave ID: "))

    client = ModbusTcpClient(device_ip)
    if not client.connect():
        print("Failed to connect to device.")
        return

    print("Reading registers for backup...")
    values = read_registers(client, slave_id)
    client.close()

    with open(BACKUP_FILENAME, "w") as f:
        f.write(",".join(map(str, values)))

    print(f"Backup completed and saved to {BACKUP_FILENAME}.")

def restore_registers():
    device_ip = input("Enter Modbus device IP address: ")
    slave_id = int(input("Enter Modbus slave ID: "))

    if not os.path.exists(BACKUP_FILENAME):
        print(f"No backup file found at {BACKUP_FILENAME}.")
        return

    with open(BACKUP_FILENAME, "r") as f:
        values_str = f.read().strip().split(",")
        values = [int(v) if v != "None" else None for v in values_str]

    if len(values) != REGISTER_COUNT:
        print(f"Backup file must contain exactly {REGISTER_COUNT} values.")
        return

    client = ModbusTcpClient(device_ip)
    if not client.connect():
        print("Failed to connect to device.")
        return

    print(f"Restoring writable registers {RESTORE_START} to 217...")
    write_registers(client, slave_id, values)
    client.close()

    print("Restoration completed.")

def main():
    parser = argparse.ArgumentParser(description='Modbus Backup & Restore Tool')
    parser.add_argument('--ip', help='Modbus device IP address')
    parser.add_argument('--slave-id', type=int, help='Modbus slave ID')
    parser.add_argument('--check', action='store_true', help='Check if device is online')
    args = parser.parse_args()

    if args.check and args.ip and args.slave_id:
        check_device_online(args.ip, args.slave_id)
        return

    while True:
        print("\nModbus Backup & Restore Tool")
        print("1. Check device status")
        print("2. Backup registers")
        print("3. Restore registers from backup")
        print("4. Exit")

        choice = input("Enter your choice: ")

        if choice == "1":
            device_ip = args.ip or input("Enter Modbus device IP address: ")
            slave_id = args.slave_id or int(input("Enter Modbus slave ID: "))
            check_device_online(device_ip, slave_id)
        elif choice == "2":
            device_ip = args.ip or input("Enter Modbus device IP address: ")
            slave_id = args.slave_id or int(input("Enter Modbus slave ID: "))
            backup_registers(device_ip, slave_id)
        elif choice == "3":
            device_ip = args.ip or input("Enter Modbus device IP address: ")
            slave_id = args.slave_id or int(input("Enter Modbus slave ID: "))
            restore_registers(device_ip, slave_id)
        elif choice == "4":
            print("Goodbye!")
            break
        else:
            print("Invalid choice. Try again.")

if __name__ == "__main__":
    main()
