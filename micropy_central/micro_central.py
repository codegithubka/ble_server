import asyncio
from bleak import BleakScanner, BleakClient
from bleak.exc import BleakError

# Your UUIDs from the peripheral
IMU_SERVICE_UUID = "1b9998a2-1234-5678-1234-56789abcdef0"
ACCEL_CHAR_UUID = "2713d05a-1234-5678-1234-56789abcdef1"
GYRO_CHAR_UUID = "2713d05b-1234-5678-1234-56789abcdef2"
MAG_CHAR_UUID = "2713d05c-1234-5678-1234-56789abcdef3"


async def find_imu_peripheral():
    try:
        print("Scanning for IMU_Sensor peripheral...")

        def detection_callback(device, advertising_data):
            # Print all devices found for debugging
            print(f"Found device: {device.name} ({device.address})")
            if device.name and "IMU_Sensor" in device.name:
                print("IMU_Sensor found!")
                return True
            return False

        device = await BleakScanner.find_device_by_filter(
            detection_callback,
            timeout=10.0  # Increased timeout to 10 seconds
        )

        if device:
            print(f"\nIMU_Sensor found!")
            print(f"Name: {device.name}")
            print(f"Address: {device.address}")
            return device
        else:
            print("IMU_Sensor not found")
            return None

    except BleakError as e:
        print(f"BLE Error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")


async def main():
    while True:  # Keep scanning until device is found
        print("\nStarting scan...")
        device = await find_imu_peripheral()
        if device:
            try:
                print("\nAttempting to connect...")
                async with BleakClient(device) as client:
                    print(f"Connected: {client.is_connected}")

                    # Read characteristics
                    accel = await client.read_gatt_char(ACCEL_CHAR_UUID)
                    gyro = await client.read_gatt_char(GYRO_CHAR_UUID)
                    mag = await client.read_gatt_char(MAG_CHAR_UUID)

                    print("\nSensor Data:")
                    print(f"Accelerometer: {accel}")
                    print(f"Gyroscope: {gyro}")
                    print(f"Magnetometer: {mag}")

            except Exception as e:
                print(f"Connection error: {e}")

        await asyncio.sleep(2)  # Wait before scanning again


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nStopped by user")