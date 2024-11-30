import asyncio
import logging
import struct
from bleak import BleakClient

IMU_SERVICE_UUID = "0000181a-0000-1000-8000-00805f9b34fb"
IMU_CHARACTERISTIC_UUID = "00002a56-0000-1000-8000-00805f9b34fb"


class IMUDataReceiverBLE:
    def __init__(self, address):
        """
        Initialize IMU data receiver via BLE

        :param address: BLE address of the IMU data sender
        """
        self.address = address
        self.client = BleakClient(self.address)
        self.logger = logging.getLogger(__name__)
        logging.basicConfig(level=logging.INFO)

    async def handle_notification(self, sender, data):
        """
        Handle notifications from the BLE characteristic

        :param sender: The handle of the characteristic that sent the notification
        :param data: The data sent by the characteristic
        """
        try:
            accel_x, accel_y, accel_z, gyro_x, gyro_y, gyro_z, mag_x, mag_y, mag_z = struct.unpack('<fffffffff', data)
            self.logger.info(f"Received IMU data:")
            self.logger.info(f"Accel(x:{accel_x:.2f}, y:{accel_y:.2f}, z:{accel_z:.2f})")
            self.logger.info(f"Gyro(x:{gyro_x:.2f}, y:{gyro_y:.2f}, z:{gyro_z:.2f})")
            self.logger.info(f"Mag(x:{mag_x:.2f}, y:{mag_y:.2f}, z:{mag_z:.2f})")
        except struct.error as e:
            self.logger.error(f"Error unpacking data: {e}")

    async def start_receiver(self):
        """
        Start the BLE client to receive IMU data
        """
        try:
            await self.client.connect()
            self.logger.info(f"Connected to BLE device at address {self.address}")

            await self.client.start_notify(IMU_CHARACTERISTIC_UUID, self.handle_notification)
            self.logger.info("Started receiving notifications for IMU data")

            # Keep the connection alive
            while True:
                await asyncio.sleep(1)

        except Exception as e:
            self.logger.error(f"Error in BLE connection: {e}")
        finally:
            await self.client.disconnect()
            self.logger.info("Disconnected from BLE device")

if __name__ == "__main__":
    receiver_address = "XX:XX:XX:XX:XX:XX"  # Replace with actual BLE address of the sender
    receiver = IMUDataReceiverBLE(receiver_address)
    try:
        asyncio.run(receiver.start_receiver())
    except KeyboardInterrupt:
        asyncio.run(receiver.client.disconnect())
