"""
Test suite for BLE Central and Peripheral implementations.
Includes both unit tests and integration tests.

# Run all tests
pytest -v

# Run specific test class
pytest -v -k TestBLECentral

# Run only unit tests (skip integration)
pytest -v -k "not integration"
"""

import pytest
import asyncio
from unittest.mock import Mock, patch
from typing import Generator
import logging

# Import your implementations
from src.central import BLECentral, AsyncBLECentral
from src.peripheral import IMUPeripheral
from src.IMU import IMUSensor

# Test configurations
TEST_DEVICE_ADDR = "11:22:33:44:55:66"
TEST_SERVICE_UUID = "1b9998a2-1234-5678-1234-56789abcdef0"
TEST_CHAR_UUIDS = {
    'accel': '2713d05a-1234-5678-1234-56789abcdef1',
    'gyro': '2713d05b-1234-5678-1234-56789abcdef2',
    'mag': '2713d05c-1234-5678-1234-56789abcdef3'
}

# Setup logging for tests
logging.basicConfig(level=logging.DEBUG)


@pytest.fixture
def mock_adapter():
    """Mock BLE adapter"""
    with patch('bluezero.adapter.Adapter') as mock:
        adapter = mock.return_value
        adapter.powered = True
        adapter.address = "00:00:00:00:00:00"
        yield adapter


@pytest.fixture
def mock_device():
    """Mock BLE device"""
    with patch('bluezero.device.Device') as mock:
        device = mock.return_value
        device.connected = False
        device.services_resolved = True
        yield device


@pytest.fixture
def mock_characteristic():
    """Mock BLE characteristic"""
    with patch('bluezero.GATT.Characteristic') as mock:
        char = mock.return_value
        char.resolve_gatt.return_value = True
        char.read_value.return_value = bytes([0, 0, 0, 0, 0, 0])  # Mock IMU data
        yield char


@pytest.fixture
def mock_imu():
    """Mock IMU sensor"""
    with patch('src.IMU.IMUSensor') as mock:
        imu = mock.return_value
        imu.readACCx.return_value = 0
        imu.readACCy.return_value = 0
        imu.readACCz.return_value = 0
        yield imu


class TestBLECentral:
    """Unit tests for synchronous BLE Central implementation"""

    def test_init(self, mock_adapter):
        """Test central initialization"""
        central = BLECentral(
            device_addr=TEST_DEVICE_ADDR,
            service_uuid=TEST_SERVICE_UUID,
            char_uuids=TEST_CHAR_UUIDS
        )
        assert central.device_addr == TEST_DEVICE_ADDR
        assert central.service_uuid == TEST_SERVICE_UUID
        assert central.connected is False

    def test_connect(self, mock_adapter, mock_device, mock_characteristic):
        """Test connection establishment"""
        central = BLECentral(
            device_addr=TEST_DEVICE_ADDR,
            service_uuid=TEST_SERVICE_UUID,
            char_uuids=TEST_CHAR_UUIDS
        )

        success = central.connect()
        assert success is True
        assert central.connected is True
        mock_device.connect.assert_called_once()

    def test_disconnect(self, mock_adapter, mock_device):
        """Test disconnection"""
        central = BLECentral(
            device_addr=TEST_DEVICE_ADDR,
            service_uuid=TEST_SERVICE_UUID,
            char_uuids=TEST_CHAR_UUIDS
        )

        central.connected = True
        central.disconnect()
        assert central.connected is False
        mock_device.disconnect.assert_called_once()

    def test_read_imu_data(self, mock_adapter, mock_device, mock_characteristic):
        """Test reading IMU data"""
        central = BLECentral(
            device_addr=TEST_DEVICE_ADDR,
            service_uuid=TEST_SERVICE_UUID,
            char_uuids=TEST_CHAR_UUIDS
        )

        central.connect()
        data = central.read_imu_data('accel')
        assert data is not None
        assert len(data) == 3  # Should return x, y, z values


class TestAsyncBLECentral:
    """Unit tests for asynchronous BLE Central implementation"""

    @pytest.mark.asyncio
    async def test_async_connect(self, mock_adapter, mock_device, mock_characteristic):
        """Test async connection"""
        central = AsyncBLECentral(
            device_addr=TEST_DEVICE_ADDR,
            service_uuid=TEST_SERVICE_UUID,
            char_uuids=TEST_CHAR_UUIDS
        )

        success = await central.connect_async()
        assert success is True
        assert central.connected is True

    @pytest.mark.asyncio
    async def test_async_disconnect(self, mock_adapter, mock_device):
        """Test async disconnection"""
        central = AsyncBLECentral(
            device_addr=TEST_DEVICE_ADDR,
            service_uuid=TEST_SERVICE_UUID,
            char_uuids=TEST_CHAR_UUIDS
        )

        central.connected = True
        await central.disconnect_async()
        assert central.connected is False

    @pytest.mark.asyncio
    async def test_async_read_imu_data(self, mock_adapter, mock_device, mock_characteristic):
        """Test async IMU data reading"""
        central = AsyncBLECentral(
            device_addr=TEST_DEVICE_ADDR,
            service_uuid=TEST_SERVICE_UUID,
            char_uuids=TEST_CHAR_UUIDS
        )

        await central.connect_async()
        data = await central.read_imu_data_async('accel')
        assert data is not None
        assert len(data) == 3


class TestIMUPeripheral:
    """Unit tests for IMU Peripheral implementation"""

    def test_peripheral_init(self, mock_adapter, mock_imu):
        """Test peripheral initialization"""
        peripheral = IMUPeripheral()
        assert peripheral.imu is not None
        mock_imu.detectIMU.assert_called_once()

    def test_peripheral_start(self, mock_adapter, mock_imu):
        """Test starting the peripheral"""
        peripheral = IMUPeripheral()
        with patch('bluezero.advertisement.AdvertisingManager'):
            peripheral.start()
            assert peripheral.running is True


@pytest.mark.integration
class TestIntegration:
    """Integration tests for BLE system"""

    @pytest.mark.asyncio
    async def test_full_connection_cycle(self, mock_adapter, mock_device, mock_characteristic, mock_imu):
        """Test full connection cycle between peripheral and central"""
        # Start peripheral
        peripheral = IMUPeripheral()
        peripheral.start()

        # Connect with central
        central = AsyncBLECentral(
            device_addr=TEST_DEVICE_ADDR,
            service_uuid=TEST_SERVICE_UUID,
            char_uuids=TEST_CHAR_UUIDS
        )

        try:
            async with central.connection():
                # Read all sensors
                sensors = ['accel', 'gyro', 'mag']
                for sensor in sensors:
                    data = await central.read_imu_data_async(sensor)
                    assert data is not None
                    assert len(data) == 3
        finally:
            peripheral.stop()


def test_error_handling(mock_adapter, mock_device):
    """Test error handling scenarios"""
    central = BLECentral(
        device_addr=TEST_DEVICE_ADDR,
        service_uuid=TEST_SERVICE_UUID,
        char_uuids=TEST_CHAR_UUIDS
    )

    # Test connection failure
    mock_device.connect.side_effect = Exception("Connection failed")
    success = central.connect()
    assert success is False
    assert central.connected is False

    # Test read failure
    mock_device.connect.side_effect = None
    central.connect()
    mock_device.services_resolved = False
    data = central.read_imu_data('accel')
    assert data is None


if __name__ == "__main__":
    pytest.main(["-v", __file__])