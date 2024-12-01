"""

UUIDs

- Central node uses the same UUID as defined in the peripheral
- Characteristics UUIDs:
    - Accelerometer: 2713d05a-1234-5678-1234-56789abcdef1
    - Gyroscope: 2713d05b-1234-5678-1234-56789abcdef2
    - Magnetometer: 2713d05c-1234-5678-1234-56789abcdef3

central = CentralIMU(
    device_addr="PERIPHERAL_MAC",
    imu_srv_uuid="1b9998a2-1234-5678-1234-56789abcdef0",
    imu_chrc_uuid={
        'accel': '2713d05a-1234-5678-1234-56789abcdef1',
        'gyro': '2713d05b-1234-5678-1234-56789abcdef2',
        'mag': '2713d05c-1234-5678-1234-56789abcdef3'
    }
)

"""




from time import sleep
from bluezero import adapter, device, GATT, tools


class CentralIMU:
    """Central Node to read IMU values from a Peripheral."""

    def __init__(self, device_addr, imu_srv_uuid, imu_chrc_uuid, adapter_addr=None):
        if adapter_addr is None:
            self.dongle = adapter.Adapter()
        else:
            self.dongle = adapter.Adapter(adapter_addr)

        if not self.dongle.powered:
            self.dongle.powered = True

        self.rmt_device = device.Device(self.dongle.address, device_addr)
        self.imu_service_uuid = imu_srv_uuid
        self.imu_char_uuid = imu_chrc_uuid
        self.imu_characteristic = None

    def connect_to_device(self, timeout=35):
        """Connect to the peripheral device."""
        print(f"Connecting to device {self.rmt_device.address}...")
        self.rmt_device.connect(timeout=timeout)

        # Wait until services are resolved
        while not self.rmt_device.services_resolved:
            sleep(0.5)

        print("Connected and services resolved.")
        self.load_imu_characteristic()

    def load_imu_characteristic(self):
        """Load the IMU characteristic."""
        print("Loading IMU characteristic...")
        self.imu_characteristic = GATT.Characteristic(
            adapter_addr=self.dongle.address,
            device_addr=self.rmt_device.address,
            srv_uuid=self.imu_service_uuid,
            chrc_uuid=self.imu_char_uuid
        )
        if self.imu_characteristic.resolve_gatt():
            print(f"IMU characteristic loaded: {self.imu_char_uuid}")
        else:
            print("Failed to load IMU characteristic.")

    def read_imu_data(self):
        """Read IMU data from the characteristic."""
        if self.imu_characteristic:
            raw_data = self.imu_characteristic.read_value()
            imu_values = tools.bytes_to_xyz(raw_data)
            print(f"IMU Data: X={imu_values[0]}, Y={imu_values[1]}, Z={imu_values[2]}")
            return imu_values
        else:
            print("IMU characteristic not loaded.")
            return None

    def disconnect(self):
        """Disconnect from the peripheral."""
        print(f"Disconnecting from device {self.rmt_device.address}...")
        self.rmt_device.disconnect()
        print("Disconnected.")
