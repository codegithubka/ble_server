# BLE IMU Communication System

A Bluetooth Low Energy (BLE) system for collecting and transmitting IMU (Inertial Measurement Unit) sensor data between a Raspberry Pi peripheral and a central node. The system supports both synchronous and asynchronous operations.

## Features

- Real-time IMU data transmission over BLE
- Support for accelerometer, gyroscope, and magnetometer data
- Both synchronous and asynchronous client implementations
- Robust error handling and automatic reconnection
- Comprehensive test suite
- Data validation and buffering
- Resource management via context managers

## Hardware Requirements

- Raspberry Pi (3 or newer) for the peripheral device
- BerryIMU v1, v2, or v3
- BLE-capable device for the central node

## Software Requirements

- Python 3.7 or newer
- Raspberry Pi OS (formerly Raspbian)
- Bluetooth support enabled

## Installation

1. Clone the repository:
```bash
git clone https://github.com/codegitgubka/ble_pi_4
cd ble_pi_4
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure Bluetooth on Raspberry Pi:
```bash
# Edit Bluetooth configuration
sudo nano /lib/systemd/system/bluetooth.service
# Add --experimental to ExecStart line:
ExecStart=/usr/libexec/bluetooth/bluetoothd --experimental

# Restart Bluetooth service
sudo systemctl daemon-reload
sudo systemctl restart bluetooth

# Add user to Bluetooth group
sudo usermod -aG bluetooth $USER

# Enable Bluetooth at startup
sudo nano /etc/bluetooth/main.conf
# Add or modify:
AutoEnable=true

# Configure Bluetooth visibility
sudo hciconfig hci0 piscan
```

## Project Structure

```
project_root/
├── requirements.txt
├── README.md
├── src/
│   ├── localGATT.py
│   ├── central.py
│   ├── peripheral.py
│   └── IMU.py
└── tests/
    ├── __init__.py
    └── test_ble.py
```

## Usage

### Starting the Peripheral (Raspberry Pi)

```python
from src.peripheral import IMUPeripheral

peripheral = IMUPeripheral()
peripheral.start()
```

### Using the Synchronous Central

```python
from src.central import BLECentral

central = BLECentral(
    device_addr="XX:XX:XX:XX:XX:XX",  # Replace with your peripheral's address
    service_uuid="1b9998a2-1234-5678-1234-56789abcdef0",
    char_uuids={
        'accel': '2713d05a-1234-5678-1234-56789abcdef1',
        'gyro': '2713d05b-1234-5678-1234-56789abcdef2',
        'mag': '2713d05c-1234-5678-1234-56789abcdef3'
    }
)

# Using context manager
with central.connection():
    accel_data = central.read_imu_data('accel')
    print(f"Accelerometer data: {accel_data}")
```

### Using the Asynchronous Central

```python
import asyncio
from src.central import AsyncBLECentral

async def main():
    central = AsyncBLECentral(
        device_addr="XX:XX:XX:XX:XX:XX",
        service_uuid="1b9998a2-1234-5678-1234-56789abcdef0",
        char_uuids={
            'accel': '2713d05a-1234-5678-1234-56789abcdef1',
            'gyro': '2713d05b-1234-5678-1234-56789abcdef2',
            'mag': '2713d05c-1234-5678-1234-56789abcdef3'
        }
    )
    
    async with central.connection():
        accel_data = await central.read_imu_data_async('accel')
        print(f"Accelerometer data: {accel_data}")

asyncio.run(main())
```

## Testing

Run the test suite:

```bash
# Run all tests
pytest -v

# Run specific test class
pytest -v -k TestBLECentral

# Run only unit tests (skip integration)
pytest -v -k "not integration"
```

## Troubleshooting

If you encounter Bluetooth issues:

1. Check Bluetooth service status:
```bash
sudo systemctl status bluetooth
```

2. View Bluetooth logs:
```bash
journalctl -u bluetooth.service
```

3. Scan for devices:
```bash
bluetoothctl
scan on
```

4. Check adapter status:
```bash
hciconfig hci0
```

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Acknowledgments

- BerryIMU library and documentation
- BluezZero Python library
- Raspberry Pi Bluetooth documentation

