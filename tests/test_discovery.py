"""Tests for PROFINET DCP network discovery."""

import dataclasses
from unittest.mock import MagicMock, patch

import pytest

from snap7.discovery import Device, discover, identify


@pytest.mark.util
class TestDevice:
    def test_device_creation(self) -> None:
        device = Device(name="plc-1", ip="192.168.1.10", mac="00:1b:1b:12:34:56")
        assert device.name == "plc-1"
        assert device.ip == "192.168.1.10"
        assert device.mac == "00:1b:1b:12:34:56"
        assert device.netmask == ""
        assert device.gateway == ""

    def test_device_with_all_fields(self) -> None:
        device = Device(
            name="plc-2",
            ip="10.0.0.1",
            mac="AA:BB:CC:DD:EE:FF",
            netmask="255.255.255.0",
            gateway="10.0.0.254",
            family="S7-1500",
        )
        assert device.netmask == "255.255.255.0"
        assert device.gateway == "10.0.0.254"
        assert device.family == "S7-1500"

    def test_device_is_frozen(self) -> None:
        device = Device(name="plc-1", ip="192.168.1.10", mac="00:00:00:00:00:00")
        with pytest.raises(dataclasses.FrozenInstanceError):
            device.name = "changed"  # type: ignore[misc]

    def test_device_str(self) -> None:
        device = Device(name="plc-1", ip="192.168.1.10", mac="00:1b:1b:12:34:56")
        result = str(device)
        assert "plc-1" in result
        assert "192.168.1.10" in result
        assert "00:1b:1b:12:34:56" in result


@pytest.mark.util
class TestDiscover:
    def test_import_error_when_pnio_dcp_not_installed(self) -> None:
        with patch.dict("sys.modules", {"pnio_dcp": None}):
            with pytest.raises(ImportError, match="pnio-dcp is required"):
                discover("192.168.1.1")

    def test_discover_returns_devices(self) -> None:
        mock_raw_device = MagicMock()
        mock_raw_device.name_of_station = "plc-1"
        mock_raw_device.IP = "192.168.1.10"
        mock_raw_device.MAC = "00:1b:1b:12:34:56"
        mock_raw_device.netmask = "255.255.255.0"
        mock_raw_device.gateway = "192.168.1.1"
        mock_raw_device.family = "S7-1200"

        mock_dcp_class = MagicMock()
        mock_dcp_instance = MagicMock()
        mock_dcp_class.return_value = mock_dcp_instance
        mock_dcp_instance.identify_all.return_value = [mock_raw_device]

        mock_module = MagicMock()
        mock_module.DCP = mock_dcp_class

        with patch.dict("sys.modules", {"pnio_dcp": mock_module}):
            devices = discover("192.168.1.1", timeout=3.0)

        assert len(devices) == 1
        assert devices[0].name == "plc-1"
        assert devices[0].ip == "192.168.1.10"
        assert devices[0].mac == "00:1b:1b:12:34:56"
        assert devices[0].netmask == "255.255.255.0"

    def test_discover_empty_network(self) -> None:
        mock_dcp_class = MagicMock()
        mock_dcp_instance = MagicMock()
        mock_dcp_class.return_value = mock_dcp_instance
        mock_dcp_instance.identify_all.return_value = []

        mock_module = MagicMock()
        mock_module.DCP = mock_dcp_class

        with patch.dict("sys.modules", {"pnio_dcp": mock_module}):
            devices = discover("192.168.1.1")

        assert devices == []

    def test_discover_multiple_devices(self) -> None:
        raw_devices = []
        for i in range(3):
            mock = MagicMock()
            mock.name_of_station = f"plc-{i}"
            mock.IP = f"192.168.1.{10 + i}"
            mock.MAC = f"00:1b:1b:12:34:{56 + i:02X}"
            mock.netmask = "255.255.255.0"
            mock.gateway = "192.168.1.1"
            mock.family = "S7-1500"
            raw_devices.append(mock)

        mock_dcp_class = MagicMock()
        mock_dcp_instance = MagicMock()
        mock_dcp_class.return_value = mock_dcp_instance
        mock_dcp_instance.identify_all.return_value = raw_devices

        mock_module = MagicMock()
        mock_module.DCP = mock_dcp_class

        with patch.dict("sys.modules", {"pnio_dcp": mock_module}):
            devices = discover("192.168.1.1")

        assert len(devices) == 3
        assert devices[0].name == "plc-0"
        assert devices[2].ip == "192.168.1.12"


@pytest.mark.util
class TestIdentify:
    def test_import_error_when_pnio_dcp_not_installed(self) -> None:
        with patch.dict("sys.modules", {"pnio_dcp": None}):
            with pytest.raises(ImportError, match="pnio-dcp is required"):
                identify("192.168.1.1", "00:1b:1b:12:34:56")

    def test_identify_returns_device(self) -> None:
        mock_raw = MagicMock()
        mock_raw.name_of_station = "plc-1"
        mock_raw.IP = "192.168.1.10"
        mock_raw.MAC = "00:1b:1b:12:34:56"
        mock_raw.netmask = "255.255.255.0"
        mock_raw.gateway = "192.168.1.1"
        mock_raw.family = "S7-1200"

        mock_dcp_class = MagicMock()
        mock_dcp_instance = MagicMock()
        mock_dcp_class.return_value = mock_dcp_instance
        mock_dcp_instance.identify.return_value = mock_raw

        mock_module = MagicMock()
        mock_module.DCP = mock_dcp_class
        mock_module.DcpTimeoutError = type("DcpTimeoutError", (Exception,), {})

        with patch.dict("sys.modules", {"pnio_dcp": mock_module}):
            device = identify("192.168.1.1", "00:1b:1b:12:34:56")

        assert device.name == "plc-1"
        assert device.ip == "192.168.1.10"

    def test_identify_timeout(self) -> None:
        mock_timeout_error = type("DcpTimeoutError", (Exception,), {})

        mock_dcp_class = MagicMock()
        mock_dcp_instance = MagicMock()
        mock_dcp_class.return_value = mock_dcp_instance
        mock_dcp_instance.identify.side_effect = mock_timeout_error()

        mock_module = MagicMock()
        mock_module.DCP = mock_dcp_class
        mock_module.DcpTimeoutError = mock_timeout_error

        with patch.dict("sys.modules", {"pnio_dcp": mock_module}):
            with pytest.raises(TimeoutError, match="No response"):
                identify("192.168.1.1", "00:1b:1b:12:34:56")
