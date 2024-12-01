from IMU import IMUSensor
from bluezero import adapter
from bluezero import advertisement
from bluezero import async_tools
from bluezero import tools
import struct
import time
import logging
import dbus
import dbus.mainloop.glib

# Initialize dbus mainloop
dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)


class IMUAdvertisement(advertisement.Advertisement):
    """Custom Advertisement with stronger parameters"""

    def __init__(self, device_name):
        super().__init__(0, 'peripheral')  # Use instance 0
        self.local_name = device_name
        self.include_tx_power = True
        # Add manufacturer data using the correct method
        self.manufacturer_data(0xFFFF, [0x01, 0x02])  # Company ID and data


class IMUPeripheral:
    """BLE Peripheral that broadcasts IMU sensor data"""

    IMU_SERVICE_UUID = '1b9998a2-1234-5678-1234-56789abcdef0'
    ACCEL_CHAR_UUID = '2713d05a-1234-5678-1234-56789abcdef1'
    GYRO_CHAR_UUID = '2713d05b-1234-5678-1234-56789abcdef2'
    MAG_CHAR_UUID = '2713d05c-1234-5678-1234-56789abcdef3'

    def __init__(self, adapter_addr=None, update_rate=0.1):
        self.logger = logging.getLogger(__name__)
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )

        self.logger.info("Initializing IMU Peripheral...")

        # Get adapter address and check status
        if adapter_addr is None:
            adapters = list(adapter.Adapter.available())
            if len(adapters) > 0:
                adapter_addr = adapters[0].address
                self.logger.info(f"Found adapter: {adapter_addr}")
            else:
                raise RuntimeError("No Bluetooth adapters found")

        # Initialize adapter directly first
        self.dongle = adapter.Adapter(adapter_addr)
        self.logger.info(f"Adapter powered: {self.dongle.powered}")
        self.logger.info(f"Adapter discoverable: {self.dongle.discoverable}")

        # Power cycle the adapter
        self.logger.info("Power cycling adapter...")
        self.dongle.powered = False
        time.sleep(1)
        self.dongle.powered = True
        time.sleep(1)

        # Set adapter properties
        self.dongle.discoverable = True
        self.dongle.pairable = True

        # Initialize peripheral
        self.peripheral = Peripheral(adapter_addr, local_name='IMU_Sensor')

        # Create advertisement and manager
        self.advertisement = IMUAdvertisement('IMU_Sensor')
        self.advertisement.service_UUIDs = [self.IMU_SERVICE_UUID]
        self.ad_manager = advertisement.AdvertisingManager(adapter_addr)

        # Initialize IMU
        self.imu = IMUSensor()
        imu_version = self.imu.detectIMU()
        if imu_version == 99:
            raise RuntimeError("No IMU detected")
        self.logger.info(f"Detected IMU version: {imu_version}")
        self.imu.initIMU()

        # Setup services and characteristics
        self._setup_gatt_server()

        self.update_rate = update_rate
        self.running = True

    def _setup_gatt_server(self):
        """Setup GATT services and characteristics"""
        self.logger.debug("Setting up GATT server...")

        # Add IMU service
        self.peripheral.add_service(
            srv_id=1,
            uuid=self.IMU_SERVICE_UUID,
            primary=True
        )
        self.logger.debug("Added IMU service")

        # Add characteristics with more descriptive UUIDs
        self.peripheral.add_characteristic(
            srv_id=1,
            chr_id=1,
            uuid=self.ACCEL_CHAR_UUID,
            value=[0] * 6,
            notifying=True,
            flags=['read', 'notify'],
            read_callback=self._read_accelerometer
        )

        self.peripheral.add_characteristic(
            srv_id=1,
            chr_id=2,
            uuid=self.GYRO_CHAR_UUID,
            value=[0] * 6,
            notifying=True,
            flags=['read', 'notify'],
            read_callback=self._read_gyroscope
        )

        self.peripheral.add_characteristic(
            srv_id=1,
            chr_id=3,
            uuid=self.MAG_CHAR_UUID,
            value=[0] * 6,
            notifying=True,
            flags=['read', 'notify'],
            read_callback=self._read_magnetometer
        )

    def _read_accelerometer(self):
        """Callback for reading accelerometer values"""
        x = self.imu.readACCx()
        y = self.imu.readACCy()
        z = self.imu.readACCz()
        self.logger.debug(f"ACC: X={x}, Y={y}, Z={z}")
        return list(struct.pack('<hhh', int(x), int(y), int(z)))

    def _read_gyroscope(self):
        """Callback for reading gyroscope values"""
        x = self.imu.readGYRx()
        y = self.imu.readGYRy()
        z = self.imu.readGYRz()
        self.logger.debug(f"GYR: X={x}, Y={y}, Z={z}")
        return list(struct.pack('<hhh', int(x), int(y), int(z)))

    def _read_magnetometer(self):
        """Callback for reading magnetometer values"""
        x = self.imu.readMAGx()
        y = self.imu.readMAGy()
        z = self.imu.readMAGz()
        self.logger.debug(f"MAG: X={x}, Y={y}, Z={z}")
        return list(struct.pack('<hhh', int(x), int(y), int(z)))

    def start(self):
        """Start the peripheral"""
        try:
            self.logger.info("Starting IMU peripheral...")

            # Double check adapter status before starting
            self.logger.info(f"Final adapter status:")
            self.logger.info(f"  - Powered: {self.dongle.powered}")
            self.logger.info(f"  - Discoverable: {self.dongle.discoverable}")
            self.logger.info(f"  - Pairable: {self.dongle.pairable}")
            self.logger.info(f"  - Address: {self.dongle.address}")

            # Register advertisement
            self.logger.info("Registering advertisement...")
            self.ad_manager.register_advertisement(self.advertisement, {})

            # Start the peripheral
            self.logger.info("Publishing peripheral...")
            self.peripheral.publish()

            self.logger.info("IMU peripheral started successfully")

        except Exception as e:
            self.logger.error(f"Error starting peripheral: {e}", exc_info=True)
            raise

        def stop(self):
            """Stop the peripheral"""
            try:
                self.logger.info("Stopping IMU peripheral...")
                self.running = False
                self.ad_manager.unregister_advertisement(self.advertisement)
                self.dongle.discoverable = False
            except Exception as e:
                self.logger.error(f"Error stopping peripheral: {e}")

if __name__ == '__main__':
    try:
        peripheral = IMUPeripheral()
        peripheral.start()
    except KeyboardInterrupt:
        print("\nStopping IMU Peripheral...")
        if 'peripheral' in locals():
            peripheral.stop()
    except Exception as e:
        print(f"Fatal error: {e}")