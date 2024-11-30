import asyncio
import json
import logging
import struct
import time
from bleak import BleakServer, BleakService, BleakCharacteristic
import IMU

IMU_SERVICE_UUID = "0000181a-0000-1000-8000-00805f9b34fb"
IMU_CHARACTERISTIC_UUID = "00002a56-0000-1000-8000-00805f9b34fb"


class IMUDataSenderBLE:
    def __init__(self, update_interval=0.1):
        """
        Initialize IMU data sender via BLE

        :param update_interval: Time between data sends
        """
        # Logging setup
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

        # IMU setup
        IMU.detectIMU()
        if IMU.imu_sensor.BerryIMUversion == 99:
            self.logger.error("No BerryIMU found")
            raise RuntimeError("No BerryIMU detected")

        IMU.initIMU()

        # Data collection settings
        self.update_interval = update_interval
        self.stop_event = asyncio.Event()
        self.sensor_data = None

    def collect_sensor_data(self):
        """
        Collect raw sensor data from IMU

        :return: Dictionary of sensor readings
        """
        try:
            return {
                'timestamp': time.time(),
                'ACC': {
                    'X': IMU.readACCx(),
                    'Y': IMU.readACCy(),
                    'Z': IMU.readACCz()
                },
                'GYR': {
                    'X': IMU.readGYRx(),
                    'Y': IMU.readGYRy(),
                    'Z': IMU.readGYRz()
                },
                'MAG': {
                    'X': IMU.readMAGx(),
                    'Y': IMU.readMAGy(),
                    'Z': IMU.readMAGz()
                }
            }
        except Exception as e:
            self.logger.error(f"Error collecting sensor data: {e}")
            return None

    async def imu_update_callback(self):
        """
        Continuously update IMU data for BLE
        """
        while not self.stop_event.is_set():
            # Collect sensor data
            sensor_data = self.collect_sensor_data()
            if sensor_data:
                self.sensor_data = struct.pack(
                    '<fffffffff',
                    sensor_data['ACC']['X'], sensor_data['ACC']['Y'], sensor_data['ACC']['Z'],
                    sensor_data['GYR']['X'], sensor_data['GYR']['Y'], sensor_data['GYR']['Z'],
                    sensor_data['MAG']['X'], sensor_data['MAG']['Y'], sensor_data['MAG']['Z']
                )
            await asyncio.sleep(self.update_interval)

    async def read_imu_data(self, char: BleakCharacteristic):
        """
        Read IMU data as a BLE characteristic

        :param char: BleakCharacteristic
        :return: Sensor data encoded as bytes
        """
        if self.sensor_data:
            return self.sensor_data
        else:
            return b"No data"

    async def start_ble_server(self):
        """
        Start the BLE server to send IMU data
        """
        try:
            imu_service = BleakService(IMU_SERVICE_UUID)
            imu_char = BleakCharacteristic(
                IMU_CHARACTERISTIC_UUID,
                ["read", "notify"],
                value_getter=self.read_imu_data
            )
            imu_service.add_characteristic(imu_char)

            server = BleakServer([imu_service])
            await server.start()
            self.logger.info("BLE Server Started, broadcasting IMU Data")

            # Continuously update sensor data
            await self.imu_update_callback()

        except Exception as e:
            self.logger.error(f"Error starting BLE server: {e}")
            self.stop_event.set()

    async def stop(self):
        """
        Stop data transmission
        """
        self.stop_event.set()


if __name__ == "__main__":
    sender = IMUDataSenderBLE()
    try:
        asyncio.run(sender.start_ble_server())
    except KeyboardInterrupt:
        asyncio.run(sender.stop())
