import dbus
from bluezero import adapter
from bluezero import localGATT
from IMU import IMUSensor
import struct
import time
import logging


class IMUPeripheral:
    """BLE Peripheral that broadcasts IMU sensor data"""

    # Service and characteristic UUIDs
    IMU_SERVICE_UUID = '1b9998a2-e730-4d61-8d01-8c0f6a81ba0f'
    ACCEL_CHAR_UUID = '2713d05a-6604-4d51-9f1e-aa4981a51d02'
    GYRO_CHAR_UUID = '2713d05b-6604-4d51-9f1e-aa4981a51d02'
    MAG_CHAR_UUID = '2713d05c-6604-4d51-9f1e-aa4981a51d02'

    def __init__(self, adapter_addr=None, update_rate=0.1):
        """
        Initialize IMU Peripheral

        :param adapter_addr: Optional specific adapter address
        :param update_rate: Sensor update rate in seconds
        """
        self.logger = logging.getLogger(__name__)
        logging.basicConfig(level=logging.INFO)

        # Initialize BLE adapter
        if adapter_addr:
            self.dongle = adapter.Adapter(adapter_addr)
        else:
            self.dongle = adapter.Adapter()

        if not self.dongle.powered:
            self.dongle.powered = True

        # Initialize IMU
        self.imu = IMUSensor()
        if self.imu.detectIMU() == 99:
            raise RuntimeError("No IMU detected")
        self.imu.initIMU()

        # Create BLE application
        self.app = localGATT.Application()

        # Create service
        self.imu_service = self._setup_imu_service()

        # Store characteristics for updating
        self.accel_char = None
        self.gyro_char = None
        self.mag_char = None

        self.update_rate = update_rate
        self.running = False

    def _setup_imu_service(self):
        """Setup IMU service with characteristics"""
        # Create main service
        service = localGATT.Service(0, self.IMU_SERVICE_UUID, True)
        self.app.add_managed_object(service)

        # Add characteristics
        self.accel_char = self._add_characteristic(
            service,
            self.ACCEL_CHAR_UUID,
            [0, 0, 0, 0, 0, 0],  # Space for 3 int16 values
            notifying=True
        )

        self.gyro_char = self._add_characteristic(
            service,
            self.GYRO_CHAR_UUID,
            [0, 0, 0, 0, 0, 0],
            notifying=True
        )

        self.mag_char = self._add_characteristic(
            service,
            self.MAG_CHAR_UUID,
            [0, 0, 0, 0, 0, 0],
            notifying=True
        )

        return service

    def _add_characteristic(self, service, uuid, initial_value, notifying=False):
        """Helper method to add a characteristic to a service"""
        flags = ['read', 'notify']
        char = localGATT.Characteristic(
            service_id=0,
            characteristic_id=len(getattr(service, 'characteristics', [])),
            uuid=uuid,
            value=initial_value,
            notifying=notifying,
            flags=flags
        )

        if not hasattr(service, 'characteristics'):
            service.characteristics = []
        service.characteristics.append(char)

        self.app.add_managed_object(char)
        return char

    def _pack_sensor_values(self, x, y, z):
        """Pack three sensor values into a bytearray"""
        # Convert to bytearray, assuming int16 values
        return list(struct.pack('<hhh', int(x), int(y), int(z)))

    def update_sensor_values(self):
        """Read and update all sensor values"""
        try:
            # Read accelerometer
            acc_x = self.imu.readACCx()
            acc_y = self.imu.readACCy()
            acc_z = self.imu.readACCz()
            self.accel_char.set_value(self._pack_sensor_values(acc_x, acc_y, acc_z))

            # Read gyroscope
            gyr_x = self.imu.readGYRx()
            gyr_y = self.imu.readGYRy()
            gyr_z = self.imu.readGYRz()
            self.gyro_char.set_value(self._pack_sensor_values(gyr_x, gyr_y, gyr_z))

            # Read magnetometer
            mag_x = self.imu.readMAGx()
            mag_y = self.imu.readMAGy()
            mag_z = self.imu.readMAGz()
            self.mag_char.set_value(self._pack_sensor_values(mag_x, mag_y, mag_z))

        except Exception as e:
            self.logger.error(f"Error updating sensor values: {e}")

    def start(self):
        """Start the peripheral and begin broadcasting sensor data"""
        try:
            # Set device name
            self.dongle.alias = 'IMU_Sensor'

            # Start BLE application
            self.running = True

            self.logger.info("Starting IMU peripheral...")

            # Start update loop in the main thread
            while self.running:
                self.update_sensor_values()
                time.sleep(self.update_rate)

        except Exception as e:
            self.logger.error(f"Error in peripheral operation: {e}")
        finally:
            self.stop()

    def stop(self):
        """Stop the peripheral"""
        self.running = False
        self.app.stop()


if __name__ == '__main__':
    try:
        peripheral = IMUPeripheral()
        peripheral.start()
    except KeyboardInterrupt:
        print("\nStopping IMU Peripheral...")
    except Exception as e:
        print(f"Error: {e}")