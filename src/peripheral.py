"""
BLE Peripheral Implementation for IMU Data Transmission

This module implements a BLE peripheral that broadcasts IMU sensor data.
It handles automatic advertising, characteristic updates, and proper resource cleanup.
"""

import asyncio
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass
import struct
import time
from contextlib import contextmanager

from bluezero import adapter, advertisement, tools, localGATT
import dbus
import dbus.mainloop.glib
from dbus.mainloop.glib import DBusGMainLoop

from IMU import IMUSensor

# Initialize dbus mainloop
DBusGMainLoop(set_as_default=True)


@dataclass
class IMUService:
    """Configuration for IMU BLE service"""
    SERVICE_UUID = "1b9998a2-1234-5678-1234-56789abcdef0"
    ACCEL_CHAR_UUID = "2713d05a-1234-5678-1234-56789abcdef1"
    GYRO_CHAR_UUID = "2713d05b-1234-5678-1234-56789abcdef2"
    MAG_CHAR_UUID = "2713d05c-1234-5678-1234-56789abcdef3"


class IMUAdvertisement(advertisement.Advertisement):
    """Enhanced BLE advertisement for IMU peripheral"""

    def __init__(self, device_name: str):
        """
        Initialize advertisement with device name and service UUID.

        Args:
            device_name: Name to advertise for the device
        """
        super().__init__(0, 'peripheral')
        self.local_name = device_name
        self.include_tx_power = True
        self.service_UUIDs = [IMUService.SERVICE_UUID]
        self.manufacturer_data = {
            0xFFFF: [0x01, 0x02]  # Company ID and data
        }


class IMUPeripheral:
    """BLE Peripheral for broadcasting IMU sensor data"""

    def __init__(
            self,
            adapter_addr: Optional[str] = None,
            device_name: str = "IMU_Sensor",
            update_interval: float = 0.1
    ):
        """
        Initialize IMU peripheral.

        Args:
            adapter_addr: Optional specific adapter address
            device_name: Name to advertise for the device
            update_interval: Interval between sensor updates in seconds
        """
        self.logger = logging.getLogger(__name__)
        logging.basicConfig(level=logging.INFO)

        # Initialize state
        self.running = False
        self.update_interval = update_interval

        # Initialize adapter
        self.adapter = adapter.Adapter(adapter_addr)
        self._ensure_adapter_config()

        # Initialize IMU
        self.imu = IMUSensor()
        self._init_imu()

        # Initialize BLE components
        self.app = localGATT.Application()
        self.advertisement = IMUAdvertisement(device_name)
        self.ad_manager = advertisement.AdvertisingManager(self.adapter.address)

        # Set up GATT server
        self._setup_gatt_server()

    def _ensure_adapter_config(self):
        """Ensure adapter is properly configured"""
        if not self.adapter.powered:
            self.adapter.powered = True
            time.sleep(1)  # Wait for power up

        self.adapter.discoverable = True
        self.adapter.pairable = True

    def _init_imu(self):
        """Initialize and verify IMU sensor"""
        imu_version = self.imu.detectIMU()
        if imu_version == 99:
            raise RuntimeError("No IMU detected")

        self.logger.info(f"Detected IMU version: {imu_version}")
        if not self.imu.initIMU():
            raise RuntimeError("Failed to initialize IMU")

    def _setup_gatt_server(self):
        """Set up GATT server with IMU characteristics"""
        # Create IMU service
        service = localGATT.Service(
            1,  # service ID
            IMUService.SERVICE_UUID,
            True  # primary service
        )
        self.app.add_managed_object(service)

        # Add characteristics
        self._add_characteristic(
            service, 1, IMUService.ACCEL_CHAR_UUID, self._read_accelerometer
        )
        self._add_characteristic(
            service, 2, IMUService.GYRO_CHAR_UUID, self._read_gyroscope
        )
        self._add_characteristic(
            service, 3, IMUService.MAG_CHAR_UUID, self._read_magnetometer
        )

    def _add_characteristic(self, service: localGATT.Service, char_id: int, uuid: str, read_cb):
        """Helper to add a characteristic to the service"""
        char = localGATT.Characteristic(
            service.get_path(),
            char_id,
            uuid,
            ['read', 'notify'],
            read_cb
        )

        self.app.add_managed_object(char)
        return char

    def _read_accelerometer(self) -> bytes:
        """Callback for reading accelerometer values"""
        x = self.imu.readACCx()
        y = self.imu.readACCy()
        z = self.imu.readACCz()
        self.logger.debug(f"ACC: X={x}, Y={y}, Z={z}")
        return struct.pack('<hhh', int(x), int(y), int(z))

    def _read_gyroscope(self) -> bytes:
        """Callback for reading gyroscope values"""
        x = self.imu.readGYRx()
        y = self.imu.readGYRy()
        z = self.imu.readGYRz()
        self.logger.debug(f"GYR: X={x}, Y={y}, Z={z}")
        return struct.pack('<hhh', int(x), int(y), int(z))

    def _read_magnetometer(self) -> bytes:
        """Callback for reading magnetometer values"""
        x = self.imu.readMAGx()
        y = self.imu.readMAGy()
        z = self.imu.readMAGz()
        self.logger.debug(f"MAG: X={x}, Y={y}, Z={z}")
        return struct.pack('<hhh', int(x), int(y), int(z))

    @contextmanager
    def advertising(self):
        """Context manager for handling advertisement"""
        try:
            self.ad_manager.register_advertisement(self.advertisement, {})
            yield
        finally:
            self.ad_manager.unregister_advertisement(self.advertisement)

    def start(self):
        """Start the peripheral"""
        try:
            self.logger.info("Starting IMU peripheral...")
            self._ensure_adapter_config()

            with self.advertising():
                self.running = True
                self.app.run()  # Start GATT server

        except Exception as e:
            self.logger.error(f"Error starting peripheral: {e}", exc_info=True)
            self.running = False
            raise

    def stop(self):
        """Stop the peripheral"""
        try:
            self.logger.info("Stopping IMU peripheral...")
            self.running = False
            self.app.quit()
            self.adapter.discoverable = False
            self.logger.info("IMU peripheral stopped")

        except Exception as e:
            self.logger.error(f"Error stopping peripheral: {e}")
            raise


class AsyncIMUPeripheral(IMUPeripheral):
    """Asynchronous version of IMU Peripheral"""

    async def start_async(self):
        """Start the peripheral asynchronously"""
        try:
            self.logger.info("Starting IMU peripheral (async)...")
            self._ensure_adapter_config()

            with self.advertising():
                self.running = True
                # Convert synchronous app.run() to async
                while self.running:
                    await asyncio.sleep(self.update_interval)

        except Exception as e:
            self.logger.error(f"Error starting peripheral: {e}", exc_info=True)
            self.running = False
            raise

    async def stop_async(self):
        """Stop the peripheral asynchronously"""
        await asyncio.get_event_loop().run_in_executor(None, self.stop)


def main():
    """Main function to run the peripheral"""
    try:
        peripheral = IMUPeripheral()
        peripheral.start()
    except KeyboardInterrupt:
        print("\nStopping IMU Peripheral...")
        if 'peripheral' in locals():
            peripheral.stop()
    except Exception as e:
        print(f"Fatal error: {e}")


async def main_async():
    """Async main function to run the peripheral"""
    try:
        peripheral = AsyncIMUPeripheral()
        await peripheral.start_async()
    except KeyboardInterrupt:
        print("\nStopping IMU Peripheral...")
        if 'peripheral' in locals():
            await peripheral.stop_async()
    except Exception as e:
        print(f"Fatal error: {e}")


if __name__ == "__main__":
    import sys

    if "--async" in sys.argv:
        asyncio.run(main_async())
    else:
        main()