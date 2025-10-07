# Heatmiser Edge Modbus Integration for Home Assistant

## Overview

This custom Home Assistant integration enables control and monitoring of Heatmiser Edge thermostats and timers via Modbus TCP. It supports temperature management, schedule editing, diagnostics, and more.

## Installation

1. **Clone or Download**
   - Copy the `custom_components/heatmiser_edge` directory into your Home Assistant `custom_components` folder.

2. **Dependencies**
   - Ensure you have the `pymodbus` library installed. Home Assistant will install it automatically via the integration’s manifest.

3. **Restart Home Assistant**
   - After copying, restart Home Assistant to load the integration.

## Configuration

Configuration is handled via the Home Assistant UI:

1. Go to **Settings > Devices & Services > Integrations**.
2. Click **Add Integration** and search for "Heatmiser Edge".
3. Enter the following details:
   - **Hostname / IP Address**: IP of your Modbus TCP bridge (e.g., Waveshare RS485 TO POE ETH (B)).
   - **Port**: Usually `502`.
   - **MODBUS ID (Slave ID)**: Device address (default: `1`).
   - **Name**: Friendly name for your device.

See [`custom_components/heatmiser_edge/config_flow.py`](custom_components/heatmiser_edge/config_flow.py) for details.

## Features

- **Thermostat & Timer Support**: Detects device type automatically.
- **Temperature Control**: Set target temperature, override, schedule, hold, away, and frost protection modes.
- **Schedule Editing**: Modify daily schedules and temperature setpoints.
- **Diagnostics**: View device status, relay state, and sensor readings.
- **Keylock Configuration**: Set or clear keylock password.
- **Entity Types**: Climate, Number, Time, Button, Sensor, Binary Sensor, Switch, Select.

## Services

The integration provides the following services:

### Write Register
Write a single value to a specific register on a Heatmiser Edge device.

```yaml
service: heatmiser_edge.write_register
target:
  device:
    - device_id_here
data:
  register: 100  # Register address (50-217)
  value: 1      # Value to write (0-65535)
  refresh_values_after_writing: true  # Optional, defaults to false
```

### Write Register Range
Write multiple values to consecutive registers starting from a specific address.

```yaml
service: heatmiser_edge.write_register_range
target:
  device:
    - device_id_here
data:
  register: 100          # Starting register address (50-217)
  values: "1,2,3,4,5"   # Comma-separated values to write
  refresh_values_after_writing: true  # Optional, defaults to false
```

**Note**: Register writes are restricted to the schedule area (registers 50-217) for safety.

## Tools

Additional utilities are provided in the `tools/` directory:

- [`tools/backup_and_restore.py`](tools/backup_and_restore.py): Command-line tool to backup and restore all Modbus registers.
- [`tools/backup_and_restore_gui.py`](tools/backup_and_restore_gui.py): GUI tool for register backup/restore.
- [`tools/modbus_gui.py`](tools/modbus_gui.py): GUI tool to decode and display register files using built-in register maps.

## Frontend interface (custom card)

Please see https://github.com/sftgunner/heatmiser-edge-frontend

## Example Devices

- [Waveshare RS485 TO POE ETH (B)](https://www.waveshare.com/wiki/RS485_TO_POE_ETH_(B)) is recommended for bridging MODBUS to Ethernet.

## Troubleshooting

- If you cannot connect, check wiring, IP address, port, and MODBUS ID.
- For advanced diagnostics, use the backup/restore tools in the `tools/` folder.

## Development

- See [`custom_components/heatmiser_edge`](custom_components/heatmiser_edge) for source code.
- Issues and contributions: [GitHub Issue Tracker](https://github.com/sftgunner/heatmiseredge-integration/issues)

## License

See repository for license details.

---

**Note:** This integration is under active development. Breaking changes may occur; backup your configuration
