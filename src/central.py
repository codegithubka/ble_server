"""
BLE Central Implementation for IMU Data Collection

This module provides both synchronous and asynchronous implementations for a BLE Central
node that collects IMU sensor data from a peripheral device.
"""

import asyncio
import logging
import time
from typing import Dict, Optional, Tuple
from dataclasses import dataclass
from collections import deque
from contextlib import asynccontextmanager, contextmanager

from bluezero import adapter, device, GATT, tools


@dataclass
class IMUCharacteristics:
    """Storage for IMU BLE characteristics"""
    accel: GATT.Characteristic
    gyro: GATT.Characteristic
    mag: GATT.Characteristic


class BLECentral:
    """Base BLE Central implementation with core functionality"""

    def __init__(
            self,
            device_addr: str,
            service_uuid: str,
            char_uuids: Dict[str, str],
            adapter_addr: Optional[str] = None,
            max_retries: int = 3,
            retry_delay: float = 2.0
    ):
        """
        Initialize BLE Central.

        Args:
            device_addr: MAC address of target peripheral
            service_uuid: UUID of the IMU service
            char_uuids: Dictionary of characteristic UUIDs for each sensor
            adapter_addr: Optional specific adapter address
            max_retries: Maximum connection retry attempts
            retry_delay: Delay between retries in seconds
        """
        self.logger = logging.getLogger(__name__)

        # Store configuration
        self.device_addr = device_addr
        self.service_uuid = service_uuid
        self.char_uuids = char_uuids
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        # Initialize state
        self.connected = False
        self._characteristics = None

        # Setup adapter
        self.adapter = adapter.Adapter(adapter_addr)
        if not self.adapter.powered:
            self.adapter.powered = True

        # Setup device
        self.device = device.Device(self.adapter.address, device_addr)

    def connect(self) -> bool:
        """
        Establish connection to peripheral.

        Returns:
            bool: True if connection successful
        """
        if self.connected:
            return True

        try:
            self.logger.info(f"Connecting to {self.device_addr}...")
            self.device.connect()

            # Wait for service discovery
            retry = 30
            while not self.device.services_resolved and retry > 0:
                retry -= 1
                time.sleep(0.5)

            if not self.device.services_resolved:
                raise TimeoutError("Service discovery timed out")

            self._load_characteristics()
            self.connected = True
            self.logger.info("Connected successfully")
            return True

        except Exception as e:
            self.logger.error(f"Connection failed: {e}")
            self.connected = False
            return False

    def disconnect(self):
        """Disconnect from peripheral"""
        if self.connected:
            try:
                self.device.disconnect()
            except Exception as e:
                self.logger.error(f"Error during disconnect: {e}")
            finally:
                self.connected = False
                self._characteristics = None

    def _load_characteristics(self):
        """Load BLE characteristics"""
        try:
            characteristics = {}
            for name, uuid in self.char_uuids.items():
                char = GATT.Characteristic(
                    adapter_addr=self.adapter.address,
                    device_addr=self.device_addr,
                    srv_uuid=self.service_uuid,
                    chrc_uuid=uuid
                )
                if not char.resolve_gatt():
                    raise RuntimeError(f"Failed to resolve {name} characteristic")
                characteristics[name] = char

            self._characteristics = IMUCharacteristics(**characteristics)

        except Exception as e:
            self.logger.error(f"Error loading characteristics: {e}")
            raise

    def read_imu_data(self, sensor_type: str) -> Optional[Tuple[int, int, int]]:
        """
        Read IMU sensor data.

        Args:
            sensor_type: Type of sensor to read ('accel', 'gyro', 'mag')

        Returns:
            Optional[Tuple[int, int, int]]: Sensor values or None if read fails
        """
        if not self.connected or not self._characteristics:
            if not self.connect():
                return None

        try:
            char = getattr(self._characteristics, sensor_type)
            raw_data = char.read_value()
            return tools.bytes_to_xyz(raw_data)
        except Exception as e:
            self.logger.error(f"Error reading {sensor_type} data: {e}")
            self.connected = False
            return None

    @contextmanager
    def connection(self):
        """Context manager for handling connections"""
        try:
            self.connect()
            yield self
        finally:
            self.disconnect()


class AsyncBLECentral(BLECentral):
    """Asynchronous BLE Central implementation"""

    async def connect_async(self) -> bool:
        """
        Establish connection asynchronously.

        Returns:
            bool: True if connection successful
        """
        if self.connected:
            return True

        try:
            self.logger.info(f"Connecting to {self.device_addr}...")

            # Run blocking connect in executor
            await asyncio.get_event_loop().run_in_executor(
                None, self.device.connect
            )

            # Wait for service discovery
            retry = 30
            while not self.device.services_resolved and retry > 0:
                retry -= 1
                await asyncio.sleep(0.5)

            if not self.device.services_resolved:
                raise TimeoutError("Service discovery timed out")

            self._load_characteristics()
            self.connected = True
            self.logger.info("Connected successfully")
            return True

        except Exception as e:
            self.logger.error(f"Connection failed: {e}")
            self.connected = False
            return False

    async def disconnect_async(self):
        """Disconnect asynchronously"""
        if self.connected:
            try:
                await asyncio.get_event_loop().run_in_executor(
                    None, self.device.disconnect
                )
            except Exception as e:
                self.logger.error(f"Error during disconnect: {e}")
            finally:
                self.connected = False
                self._characteristics = None

    async def read_imu_data_async(self, sensor_type: str) -> Optional[Tuple[int, int, int]]:
        """
        Read IMU sensor data asynchronously.

        Args:
            sensor_type: Type of sensor to read ('accel', 'gyro', 'mag')

        Returns:
            Optional[Tuple[int, int, int]]: Sensor values or None if read fails
        """
        if not self.connected or not self._characteristics:
            if not await self.connect_async():
                return None

        try:
            char = getattr(self._characteristics, sensor_type)
            raw_data = await asyncio.get_event_loop().run_in_executor(
                None, char.read_value
            )
            return tools.bytes_to_xyz(raw_data)
        except Exception as e:
            self.logger.error(f"Error reading {sensor_type} data: {e}")
            self.connected = False
            return None

    @asynccontextmanager
    async def connection(self):
        """Async context manager for handling connections"""
        try:
            await self.connect_async()
            yield self
        finally:
            await self.disconnect_async()


# Example usage:
def sync_example():
    central = BLECentral(
        device_addr="XX:XX:XX:XX:XX:XX",
        service_uuid="1b9998a2-1234-5678-1234-56789abcdef0",
        char_uuids={
            'accel': '2713d05a-1234-5678-1234-56789abcdef1',
            'gyro': '2713d05b-1234-5678-1234-56789abcdef2',
            'mag': '2713d05c-1234-5678-1234-56789abcdef3'
        }
    )

    with central.connection():
        accel_data = central.read_imu_data('accel')
        print(f"Accelerometer data: {accel_data}")


async def async_example():
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


if __name__ == "__main__":
    # Run sync example
    sync_example()

    # Run async example
    asyncio.run(async_example())