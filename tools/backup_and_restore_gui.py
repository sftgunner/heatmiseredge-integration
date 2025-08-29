import tkinter as tk
from tkinter import messagebox, scrolledtext, filedialog
from pymodbus.client import ModbusTcpClient
import os
import time

REGISTER_COUNT = 218
RESTORE_START = 21

class ModbusApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Modbus Backup & Restore Tool")
        self.root.geometry("550x420")

        # IP address input
        tk.Label(root, text="Device IP:").grid(row=0, column=0, padx=10, pady=5, sticky="e")
        self.ip_entry = tk.Entry(root, width=30)
        self.ip_entry.grid(row=0, column=1, padx=10, pady=5)

        # Slave ID input
        tk.Label(root, text="Slave ID:").grid(row=1, column=0, padx=10, pady=5, sticky="e")
        self.slave_entry = tk.Entry(root, width=10)
        self.slave_entry.grid(row=1, column=1, padx=10, pady=5, sticky="w")

        # Buttons
        self.backup_btn = tk.Button(root, text="Backup Registers", command=self.backup_registers)
        self.backup_btn.grid(row=2, column=0, columnspan=2, pady=10)

        self.restore_btn = tk.Button(root, text="Restore Registers", command=self.restore_registers)
        self.restore_btn.grid(row=3, column=0, columnspan=2, pady=5)

        # Output area
        self.output = scrolledtext.ScrolledText(root, width=65, height=15)
        self.output.grid(row=4, column=0, columnspan=2, padx=10, pady=10)

    def log(self, message):
        self.output.insert(tk.END, message + "\n")
        self.output.see(tk.END)

    def read_registers(self, client, slave_id):
        all_values = [None] * REGISTER_COUNT
        for i in range(0, 210, 10):
            result = client.read_holding_registers(i, count=10, slave=slave_id)
            if result.isError():
                self.log(f"Error reading {i}–{i+9}: {result}")
                continue
            all_values[i:i+10] = result.registers

        result = client.read_holding_registers(210, count=8, slave=slave_id)
        if not result.isError():
            all_values[210:218] = result.registers
        else:
            self.log("Error reading 210–217")

        return all_values

    def write_registers(self, client, slave_id, values):
        for i in range(RESTORE_START, 210, 10):
            chunk = values[i:i+10]
            if None in chunk:
                self.log(f"Skipping write to {i}–{i+9} (missing data)")
                continue
            client.write_registers(i, chunk, slave=slave_id)

        last_chunk = values[210:218]
        if None not in last_chunk:
            client.write_registers(210, last_chunk, slave=slave_id)
        else:
            self.log("Skipping write to 210–217 (missing data)")

    def backup_registers(self):
        device_ip = self.ip_entry.get().strip()
        try:
            slave_id = int(self.slave_entry.get())
        except ValueError:
            messagebox.showerror("Invalid Input", "Slave ID must be an integer.")
            return

        if not device_ip:
            messagebox.showerror("Missing Input", "Device IP cannot be empty.")
            return

        # Build default filename
        ip_sanitized = device_ip.replace(".", "_")
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        default_filename = f"heatmiser_backup_{ip_sanitized}_{slave_id}_{timestamp}.txt"

        # Ask user where to save
        file_path = filedialog.asksaveasfilename(
            initialfile=default_filename,
            defaultextension=".txt",
            filetypes=[("Text Files", "*.txt")]
        )
        if not file_path:
            self.log("Backup cancelled.")
            return

        self.log(f"Connecting to {device_ip}...")
        client = ModbusTcpClient(device_ip)
        if not client.connect():
            self.log("Connection failed.")
            return

        self.log("Reading registers 0–217...")
        values = self.read_registers(client, slave_id)
        client.close()

        with open(file_path, "w") as f:
            f.write(",".join(map(str, values)))

        self.log(f"Backup saved to {file_path}.")


    def restore_registers(self):
        device_ip = self.ip_entry.get()
        try:
            slave_id = int(self.slave_entry.get())
        except ValueError:
            messagebox.showerror("Invalid Input", "Slave ID must be an integer.")
            return

        file_path = filedialog.askopenfilename(filetypes=[("Text Files", "*.txt")])
        if not file_path:
            self.log("Restore cancelled.")
            return

        if not os.path.exists(file_path):
            self.log(f"File not found: {file_path}")
            return

        with open(file_path, "r") as f:
            values_str = f.read().strip().split(",")
            values = [int(v) if v != "None" else None for v in values_str]

        if len(values) != REGISTER_COUNT:
            self.log(f"File must contain {REGISTER_COUNT} values.")
            return

        self.log(f"Connecting to {device_ip}...")
        client = ModbusTcpClient(device_ip)
        if not client.connect():
            self.log("Connection failed.")
            return

        self.log("Restoring writable registers 21–217...")
        self.write_registers(client, slave_id, values)
        client.close()
        self.log("Restore complete.")

if __name__ == "__main__":
    root = tk.Tk()
    app = ModbusApp(root)
    root.mainloop()
