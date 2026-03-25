"""Tests for the unified s7 package."""

import pytest
from unittest.mock import MagicMock, patch

from s7 import Client, Server, Protocol, Area, Block, WordLen


class TestProtocol:
    """Test Protocol enum."""

    def test_enum_values(self) -> None:
        assert Protocol.AUTO.value == "auto"
        assert Protocol.LEGACY.value == "legacy"
        assert Protocol.S7COMMPLUS.value == "s7commplus"


class TestClientInit:
    """Test Client initialization."""

    def test_default_state(self) -> None:
        client = Client()
        assert client.protocol == Protocol.AUTO
        assert client.connected is False

    def test_repr_disconnected(self) -> None:
        client = Client()
        assert "disconnected" in repr(client)


class TestClientLegacy:
    """Test Client with legacy protocol (mocked)."""

    @patch("s7.client.S7CommPlusClient")
    @patch("s7.client.LegacyClient")
    def test_connect_legacy_fallback(self, mock_legacy_cls: MagicMock, mock_plus_cls: MagicMock) -> None:
        """When S7CommPlus fails, client falls back to legacy."""
        # S7CommPlus connect raises
        mock_plus = MagicMock()
        mock_plus.connect.side_effect = RuntimeError("Connection refused")
        mock_plus_cls.return_value = mock_plus

        # Legacy connects fine
        mock_legacy = MagicMock()
        mock_legacy.connected = True
        mock_legacy_cls.return_value = mock_legacy

        client = Client()
        result = client.connect("192.168.1.10", 0, 1)

        assert result is client
        assert client.protocol == Protocol.LEGACY
        mock_legacy.connect.assert_called_once_with("192.168.1.10", 0, 1, 102)

    @patch("s7.client.S7CommPlusClient")
    @patch("s7.client.LegacyClient")
    def test_connect_explicit_legacy(self, mock_legacy_cls: MagicMock, mock_plus_cls: MagicMock) -> None:
        """When protocol=LEGACY, S7CommPlus is not attempted."""
        mock_legacy = MagicMock()
        mock_legacy.connected = True
        mock_legacy_cls.return_value = mock_legacy

        client = Client()
        client.connect("192.168.1.10", 0, 1, protocol=Protocol.LEGACY)

        assert client.protocol == Protocol.LEGACY
        mock_plus_cls.assert_not_called()

    @patch("s7.client.S7CommPlusClient")
    @patch("s7.client.LegacyClient")
    def test_db_read_delegates_to_legacy(self, mock_legacy_cls: MagicMock, mock_plus_cls: MagicMock) -> None:
        """db_read delegates to legacy when protocol is LEGACY."""
        mock_legacy = MagicMock()
        mock_legacy.connected = True
        mock_legacy.db_read.return_value = bytearray([1, 2, 3, 4])
        mock_legacy_cls.return_value = mock_legacy

        mock_plus = MagicMock()
        mock_plus.connect.side_effect = RuntimeError("fail")
        mock_plus_cls.return_value = mock_plus

        client = Client()
        client.connect("192.168.1.10", 0, 1)
        data = client.db_read(1, 0, 4)

        assert data == bytearray([1, 2, 3, 4])
        mock_legacy.db_read.assert_called_once_with(1, 0, 4)

    @patch("s7.client.S7CommPlusClient")
    @patch("s7.client.LegacyClient")
    def test_db_write_delegates_to_legacy(self, mock_legacy_cls: MagicMock, mock_plus_cls: MagicMock) -> None:
        mock_legacy = MagicMock()
        mock_legacy.connected = True
        mock_legacy.db_write.return_value = 0
        mock_legacy_cls.return_value = mock_legacy

        mock_plus = MagicMock()
        mock_plus.connect.side_effect = RuntimeError("fail")
        mock_plus_cls.return_value = mock_plus

        client = Client()
        client.connect("192.168.1.10", 0, 1)
        result = client.db_write(1, 0, bytearray([1, 2, 3, 4]))

        assert result == 0
        mock_legacy.db_write.assert_called_once()

    @patch("s7.client.S7CommPlusClient")
    @patch("s7.client.LegacyClient")
    def test_getattr_delegates_to_legacy(self, mock_legacy_cls: MagicMock, mock_plus_cls: MagicMock) -> None:
        """Methods not on unified client delegate to legacy."""
        mock_legacy = MagicMock()
        mock_legacy.connected = True
        mock_legacy.get_cpu_info.return_value = "cpu_info"
        mock_legacy_cls.return_value = mock_legacy

        mock_plus = MagicMock()
        mock_plus.connect.side_effect = RuntimeError("fail")
        mock_plus_cls.return_value = mock_plus

        client = Client()
        client.connect("192.168.1.10", 0, 1)
        info = client.get_cpu_info()

        assert info == "cpu_info"
        mock_legacy.get_cpu_info.assert_called_once()

    @patch("s7.client.S7CommPlusClient")
    @patch("s7.client.LegacyClient")
    def test_disconnect(self, mock_legacy_cls: MagicMock, mock_plus_cls: MagicMock) -> None:
        mock_legacy = MagicMock()
        mock_legacy.connected = True
        mock_legacy_cls.return_value = mock_legacy

        mock_plus = MagicMock()
        mock_plus.connect.side_effect = RuntimeError("fail")
        mock_plus_cls.return_value = mock_plus

        client = Client()
        client.connect("192.168.1.10", 0, 1)
        result = client.disconnect()

        assert result == 0
        mock_legacy.disconnect.assert_called_once()


class TestClientS7CommPlus:
    """Test Client with S7CommPlus protocol (mocked)."""

    @patch("s7.client.S7CommPlusClient")
    @patch("s7.client.LegacyClient")
    def test_connect_s7commplus(self, mock_legacy_cls: MagicMock, mock_plus_cls: MagicMock) -> None:
        """When S7CommPlus succeeds, protocol is S7COMMPLUS."""
        mock_plus = MagicMock()
        mock_plus.using_legacy_fallback = False
        mock_plus.connected = True
        mock_plus_cls.return_value = mock_plus

        mock_legacy = MagicMock()
        mock_legacy.connected = True
        mock_legacy_cls.return_value = mock_legacy

        client = Client()
        client.connect("192.168.1.10", 0, 1)

        assert client.protocol == Protocol.S7COMMPLUS

    @patch("s7.client.S7CommPlusClient")
    @patch("s7.client.LegacyClient")
    def test_db_read_uses_s7commplus(self, mock_legacy_cls: MagicMock, mock_plus_cls: MagicMock) -> None:
        """db_read uses S7CommPlus when available."""
        mock_plus = MagicMock()
        mock_plus.using_legacy_fallback = False
        mock_plus.connected = True
        mock_plus.db_read.return_value = b"\x01\x02\x03\x04"
        mock_plus_cls.return_value = mock_plus

        mock_legacy = MagicMock()
        mock_legacy.connected = True
        mock_legacy_cls.return_value = mock_legacy

        client = Client()
        client.connect("192.168.1.10", 0, 1)
        data = client.db_read(1, 0, 4)

        assert data == bytearray([1, 2, 3, 4])
        assert isinstance(data, bytearray)
        mock_plus.db_read.assert_called_once_with(1, 0, 4)
        mock_legacy.db_read.assert_not_called()

    @patch("s7.client.S7CommPlusClient")
    @patch("s7.client.LegacyClient")
    def test_db_write_uses_s7commplus(self, mock_legacy_cls: MagicMock, mock_plus_cls: MagicMock) -> None:
        mock_plus = MagicMock()
        mock_plus.using_legacy_fallback = False
        mock_plus.connected = True
        mock_plus_cls.return_value = mock_plus

        mock_legacy = MagicMock()
        mock_legacy.connected = True
        mock_legacy_cls.return_value = mock_legacy

        client = Client()
        client.connect("192.168.1.10", 0, 1)
        result = client.db_write(1, 0, bytearray([1, 2, 3, 4]))

        assert result == 0
        mock_plus.db_write.assert_called_once_with(1, 0, b"\x01\x02\x03\x04")
        mock_legacy.db_write.assert_not_called()

    @patch("s7.client.S7CommPlusClient")
    @patch("s7.client.LegacyClient")
    def test_legacy_methods_still_delegate(self, mock_legacy_cls: MagicMock, mock_plus_cls: MagicMock) -> None:
        """Even with S7CommPlus, legacy-only methods go to legacy client."""
        mock_plus = MagicMock()
        mock_plus.using_legacy_fallback = False
        mock_plus.connected = True
        mock_plus_cls.return_value = mock_plus

        mock_legacy = MagicMock()
        mock_legacy.connected = True
        mock_legacy.list_blocks.return_value = "blocks"
        mock_legacy_cls.return_value = mock_legacy

        client = Client()
        client.connect("192.168.1.10", 0, 1)
        blocks = client.list_blocks()

        assert blocks == "blocks"
        mock_legacy.list_blocks.assert_called_once()

    @patch("s7.client.S7CommPlusClient")
    @patch("s7.client.LegacyClient")
    def test_s7commplus_fallback_detected(self, mock_legacy_cls: MagicMock, mock_plus_cls: MagicMock) -> None:
        """If S7CommPlus connects but falls back, unified client uses LEGACY."""
        mock_plus = MagicMock()
        mock_plus.using_legacy_fallback = True  # Data ops not supported
        mock_plus_cls.return_value = mock_plus

        mock_legacy = MagicMock()
        mock_legacy.connected = True
        mock_legacy_cls.return_value = mock_legacy

        client = Client()
        client.connect("192.168.1.10", 0, 1)

        assert client.protocol == Protocol.LEGACY
        # S7CommPlus should have been disconnected
        mock_plus.disconnect.assert_called_once()

    @patch("s7.client.S7CommPlusClient")
    @patch("s7.client.LegacyClient")
    def test_explore_requires_s7commplus(self, mock_legacy_cls: MagicMock, mock_plus_cls: MagicMock) -> None:
        """explore() raises when S7CommPlus is not active."""
        mock_plus = MagicMock()
        mock_plus.connect.side_effect = RuntimeError("fail")
        mock_plus_cls.return_value = mock_plus

        mock_legacy = MagicMock()
        mock_legacy.connected = True
        mock_legacy_cls.return_value = mock_legacy

        client = Client()
        client.connect("192.168.1.10", 0, 1)

        with pytest.raises(RuntimeError, match="S7CommPlus"):
            client.explore()

    @patch("s7.client.S7CommPlusClient")
    @patch("s7.client.LegacyClient")
    def test_explicit_s7commplus_fails(self, mock_legacy_cls: MagicMock, mock_plus_cls: MagicMock) -> None:
        """protocol=S7COMMPLUS raises if S7CommPlus fails."""
        mock_plus = MagicMock()
        mock_plus.connect.side_effect = RuntimeError("fail")
        mock_plus_cls.return_value = mock_plus

        client = Client()
        with pytest.raises(RuntimeError, match="explicitly requested"):
            client.connect("192.168.1.10", 0, 1, protocol=Protocol.S7COMMPLUS)


class TestClientContextManager:
    """Test context manager protocol."""

    @patch("s7.client.S7CommPlusClient")
    @patch("s7.client.LegacyClient")
    def test_context_manager(self, mock_legacy_cls: MagicMock, mock_plus_cls: MagicMock) -> None:
        mock_plus = MagicMock()
        mock_plus.connect.side_effect = RuntimeError("fail")
        mock_plus_cls.return_value = mock_plus

        mock_legacy = MagicMock()
        mock_legacy.connected = True
        mock_legacy_cls.return_value = mock_legacy

        with Client() as client:
            client.connect("192.168.1.10", 0, 1)
            assert client.connected

        mock_legacy.disconnect.assert_called_once()


class TestClientDbReadMulti:
    """Test db_read_multi."""

    @patch("s7.client.S7CommPlusClient")
    @patch("s7.client.LegacyClient")
    def test_multi_read_s7commplus(self, mock_legacy_cls: MagicMock, mock_plus_cls: MagicMock) -> None:
        mock_plus = MagicMock()
        mock_plus.using_legacy_fallback = False
        mock_plus.connected = True
        mock_plus.db_read_multi.return_value = [b"\x01\x02", b"\x03\x04"]
        mock_plus_cls.return_value = mock_plus

        mock_legacy = MagicMock()
        mock_legacy.connected = True
        mock_legacy_cls.return_value = mock_legacy

        client = Client()
        client.connect("192.168.1.10", 0, 1)
        results = client.db_read_multi([(1, 0, 2), (1, 2, 2)])

        assert len(results) == 2
        assert all(isinstance(r, bytearray) for r in results)
        mock_plus.db_read_multi.assert_called_once()

    @patch("s7.client.S7CommPlusClient")
    @patch("s7.client.LegacyClient")
    def test_multi_read_legacy(self, mock_legacy_cls: MagicMock, mock_plus_cls: MagicMock) -> None:
        mock_plus = MagicMock()
        mock_plus.connect.side_effect = RuntimeError("fail")
        mock_plus_cls.return_value = mock_plus

        mock_legacy = MagicMock()
        mock_legacy.connected = True
        mock_legacy.db_read.side_effect = [bytearray([1, 2]), bytearray([3, 4])]
        mock_legacy_cls.return_value = mock_legacy

        client = Client()
        client.connect("192.168.1.10", 0, 1)
        results = client.db_read_multi([(1, 0, 2), (1, 2, 2)])

        assert len(results) == 2
        assert mock_legacy.db_read.call_count == 2


class TestImports:
    """Test that s7 package exports are accessible."""

    def test_types_exported(self) -> None:
        assert Area is not None
        assert Block is not None
        assert WordLen is not None

    def test_protocol_exported(self) -> None:
        assert Protocol.AUTO is not None


class TestServer:
    """Test unified Server (mocked)."""

    @patch("s7.server.S7CommPlusServer")
    @patch("s7.server.LegacyServer")
    def test_start_legacy_only(self, mock_legacy_cls: MagicMock, mock_plus_cls: MagicMock) -> None:
        mock_legacy = MagicMock()
        mock_legacy.start.return_value = 0
        mock_legacy_cls.return_value = mock_legacy

        mock_plus = MagicMock()
        mock_plus_cls.return_value = mock_plus

        server = Server()
        result = server.start(tcp_port=11020)

        assert result == 0
        mock_legacy.start.assert_called_once_with(tcp_port=11020)
        mock_plus.start.assert_not_called()

    @patch("s7.server.S7CommPlusServer")
    @patch("s7.server.LegacyServer")
    def test_start_both(self, mock_legacy_cls: MagicMock, mock_plus_cls: MagicMock) -> None:
        mock_legacy = MagicMock()
        mock_legacy.start.return_value = 0
        mock_legacy_cls.return_value = mock_legacy

        mock_plus = MagicMock()
        mock_plus_cls.return_value = mock_plus

        server = Server()
        server.start(tcp_port=11020, s7commplus_port=11021)

        mock_legacy.start.assert_called_once_with(tcp_port=11020)
        mock_plus.start.assert_called_once_with(port=11021, use_tls=False, tls_cert=None, tls_key=None)

    @patch("s7.server.S7CommPlusServer")
    @patch("s7.server.LegacyServer")
    def test_stop_both(self, mock_legacy_cls: MagicMock, mock_plus_cls: MagicMock) -> None:
        mock_legacy = MagicMock()
        mock_legacy.start.return_value = 0
        mock_legacy.stop.return_value = 0
        mock_legacy_cls.return_value = mock_legacy

        mock_plus = MagicMock()
        mock_plus_cls.return_value = mock_plus

        server = Server()
        server.start(tcp_port=11020, s7commplus_port=11021)
        result = server.stop()

        assert result == 0
        mock_plus.stop.assert_called_once()
        mock_legacy.stop.assert_called_once()

    @patch("s7.server.S7CommPlusServer")
    @patch("s7.server.LegacyServer")
    def test_getattr_delegates(self, mock_legacy_cls: MagicMock, mock_plus_cls: MagicMock) -> None:
        mock_legacy = MagicMock()
        mock_legacy.get_status.return_value = ("running", "ok", 0)
        mock_legacy_cls.return_value = mock_legacy

        mock_plus = MagicMock()
        mock_plus_cls.return_value = mock_plus

        server = Server()
        status = server.get_status()

        assert status == ("running", "ok", 0)

    @patch("s7.server.S7CommPlusServer")
    @patch("s7.server.LegacyServer")
    def test_context_manager(self, mock_legacy_cls: MagicMock, mock_plus_cls: MagicMock) -> None:
        mock_legacy = MagicMock()
        mock_legacy.start.return_value = 0
        mock_legacy.stop.return_value = 0
        mock_legacy_cls.return_value = mock_legacy

        mock_plus = MagicMock()
        mock_plus_cls.return_value = mock_plus

        with Server() as server:
            server.start(tcp_port=11020)

        mock_legacy.stop.assert_called_once()
