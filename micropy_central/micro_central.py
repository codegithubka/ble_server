from bluetooth import BLE
import struct
from time import sleep

PERIPHERAL_NAME = "IMU_Sensor"
SERVICE_UUID = "1b9998a2-1234-5678-1234-56789abcdef0"
CHAR_UUID = "2713d05a-1234-5678-1234-56789abcdef1"


class CentralDevice:
    def __init__(self):
        self.ble = BLE()
        self.ble.active(True)
        self.ble.irq(self._irq_handler)
        self.scanning = False
        self.connected = False
        self.conn_handle = None
        self.accel_handle = None

    def _irq_handler(self, event, data):
        if event == 5:  # _IRQ_SCAN_RESULT
            if len(data) >= 5:
                addr_type, addr, adv_type, rssi, adv_data = data
                adv_data = bytes(adv_data)  # Convert memoryview to bytes

                name = self._decode_name(adv_data)
                if name:
                    print(f"Device name: {name}")

                if name == PERIPHERAL_NAME:
                    print(f"Found IMU Peripheral, RSSI: {rssi}")
                    self.ble.gap_connect(addr_type, addr)
                    self.scanning = False
            else:
                print(f"Unexpected data format for scan result: {data}")

        elif event == 6:  # _IRQ_SCAN_DONE
            print("Scan complete.")
            self.scanning = False

        elif event == 3:  # _IRQ_PERIPHERAL_CONNECT
            if len(data) >= 3:
                conn_handle, _, _ = data
                print("Connected")
                self.conn_handle = conn_handle
                self.connected = True
                self.ble.gattc_discover_services(self.conn_handle)
            else:
                print(f"Unexpected data format for connection: {data}")

        elif event == 8:  # _IRQ_GATTC_SERVICE_RESULT
            if len(data) >= 4:
                conn_handle, start_handle, end_handle, uuid = data
                if self._parse_uuid(uuid) == SERVICE_UUID.replace('-', ''):
                    self.ble.gattc_discover_characteristics(self.conn_handle, start_handle, end_handle)
            else:
                print(f"Unexpected data format for service result: {data}")

        elif event == 7:  # _IRQ_GATTC_CHARACTERISTIC_RESULT
            if len(data) >= 5:
                _, _, value_handle, _, uuid = data
                if self._parse_uuid(uuid) == CHAR_UUID.replace('-', ''):
                    self.accel_handle = value_handle
                    print("Found accelerometer characteristic")

        elif event == 9:  # _IRQ_GATTC_READ_RESULT
            if len(data) >= 3:
                _, _, value = data
                try:
                    x, y, z = struct.unpack('<hhh', value)
                    print(f"Accel: X={x}, Y={y}, Z={z}")
                except struct.error:
                    print("Invalid accelerometer data format")
            else:
                print(f"Unexpected data format for read result: {data}")

        elif event == 4:  # _IRQ_PERIPHERAL_DISCONNECT
            if len(data) >= 3:
                self.connected = False
                self.conn_handle = None
                self.accel_handle = None
                print("Disconnected")

    def _parse_uuid(self, uuid):
        return ''.join(f'{b:02x}' for b in uuid)

    def _decode_name(self, adv_data):
        """Decode the advertised name from advertisement data."""
        i = 0
        while i < len(adv_data):
            length = adv_data[i]
            if length == 0:
                break
            type = adv_data[i + 1]
            if type == 0x09:
                try:
                    name = adv_data[i + 2:i + 1 + length].decode("utf-8")
                    return name
                except UnicodeDecodeError:
                    return None
            i += 1 + length
        return None

    def scan(self):
        if not self.scanning:
            print("Starting scan...")
            self.scanning = True
            self.ble.gap_scan(0, 2000000, 500000, True)

    def read_accelerometer(self):
        if self.connected and self.accel_handle:
            self.ble.gattc_read(self.conn_handle, self.accel_handle)

    def run(self):
        while True:
            if not self.connected:
                self.scan()
                sleep(5)
            else:
                self.read_accelerometer()
                sleep(1)


if __name__ == "__main__":
    central = CentralDevice()
    try:
        central.run()
    except KeyboardInterrupt:
        print("Exiting...")

