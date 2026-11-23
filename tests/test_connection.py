"""Tests for snap7.connection module — socket mocking, COTP parsing, exception paths."""

import socket
import struct
import threading
import time
import pytest
from unittest.mock import patch, MagicMock

from snap7.connection import ISOTCPConnection, TPDUSize
from snap7.error import S7ConnectionError, S7TimeoutError


class TestTPDUSize:
    """Test TPDUSize enum values."""

    def test_sizes(self) -> None:
        assert TPDUSize.S_128.value == 0x07
        assert TPDUSize.S_1024.value == 0x0A
        assert TPDUSize.S_8192.value == 0x0D


class TestISOTCPConnectionInit:
    """Test constructor defaults."""

    def test_defaults(self) -> None:
        conn = ISOTCPConnection("1.2.3.4")
        assert conn.host == "1.2.3.4"
        assert conn.port == 102
        assert conn.connected is False
        assert conn.socket is None
        assert conn.pdu_size == 240

    def test_custom_params(self) -> None:
        conn = ISOTCPConnection("1.2.3.4", port=1102, local_tsap=0x200, remote_tsap=0x300, tpdu_size=TPDUSize.S_512)
        assert conn.port == 1102
        assert conn.local_tsap == 0x200
        assert conn.remote_tsap == 0x300
        assert conn.tpdu_size == TPDUSize.S_512


class TestBuildTPKT:
    """Test TPKT frame building."""

    def test_tpkt_structure(self) -> None:
        conn = ISOTCPConnection("1.2.3.4")
        payload = b"\x01\x02\x03"
        frame = conn._build_tpkt(payload)
        assert frame[:2] == b"\x03\x00"  # version=3, reserved=0
        length = struct.unpack(">H", frame[2:4])[0]
        assert length == 7  # 4 header + 3 payload
        assert frame[4:] == payload


class TestBuildCOTPCR:
    """Test COTP Connection Request building."""

    def test_cr_structure(self) -> None:
        conn = ISOTCPConnection("1.2.3.4", local_tsap=0x0100, remote_tsap=0x0102)
        cr = conn._build_cotp_cr()
        # First byte = PDU length
        pdu_type = cr[1]
        assert pdu_type == 0xE0  # COTP_CR
        # Should contain parameters for TSAP and PDU size
        assert len(cr) > 7


class TestBuildCOTPDT:
    """Test COTP Data Transfer building."""

    def test_dt_structure(self) -> None:
        conn = ISOTCPConnection("1.2.3.4")
        data = b"\xaa\xbb"
        dt = conn._build_cotp_dt(data)
        assert dt[0] == 2  # PDU length
        assert dt[1] == 0xF0  # COTP_DT
        assert dt[2] == 0x80  # EOT
        assert dt[3:] == data


class TestParseCOTPCC:
    """Test COTP Connection Confirm parsing."""

    def test_valid_cc(self) -> None:
        conn = ISOTCPConnection("1.2.3.4")
        # Build a valid CC: len, type, dst_ref (echoes ours), src_ref (the peer's), class_opt
        cc_data = struct.pack(">BBHHB", 6, 0xD0, 0x0001, 0x1234, 0x00)
        conn._parse_cotp_cc(cc_data)
        assert conn.dst_ref == 0x1234

    # COTP CC from a CP 343-1 in front of an S7-313C-2 DP, captured for #972 (after the
    # TPKT header): dst-ref 0x0001 echoes our reference, src-ref 0x4431 is the CP's.
    CAPTURED_CC = bytes.fromhex("11 d0 0001 4431 00 c0 01 0a c1 02 01 00 c2 02 01 02")
    # The DR must address the CP's reference; python-snap7 3.3.1 sent 06 80 0001 0001 00 00,
    # and up to 3.4.0 a stray user-data byte followed the reason.

    def test_captured_cc_gives_the_peer_reference(self) -> None:
        conn = ISOTCPConnection("1.2.3.4")
        conn._parse_cotp_cc(self.CAPTURED_CC)
        assert conn.dst_ref == 0x4431
        assert conn.src_ref == 0x0001

    def test_disconnect_sends_no_disconnect_request(self) -> None:
        conn = ISOTCPConnection("1.2.3.4")
        conn._parse_cotp_cc(self.CAPTURED_CC)
        sock = MagicMock()
        sock.recv.return_value = b""
        conn.socket = sock
        conn.connected = True
        conn.disconnect()
        sock.sendall.assert_not_called()
        sock.shutdown.assert_called_once_with(socket.SHUT_WR)

    def test_cc_too_short(self) -> None:
        conn = ISOTCPConnection("1.2.3.4")
        with pytest.raises(S7ConnectionError, match="too short"):
            conn._parse_cotp_cc(b"\x00\x01\x02")

    def test_cc_wrong_type(self) -> None:
        conn = ISOTCPConnection("1.2.3.4")
        cc_data = struct.pack(">BBHHB", 6, 0xE0, 0x0000, 0x0001, 0x00)  # CR instead of CC
        with pytest.raises(S7ConnectionError, match="Expected COTP CC"):
            conn._parse_cotp_cc(cc_data)

    def test_cc_with_pdu_size_param_1byte(self) -> None:
        conn = ISOTCPConnection("1.2.3.4")
        base = struct.pack(">BBHHB", 10, 0xD0, 0x0001, 0x0001, 0x00)
        # PDU size parameter: code=0xC0, len=1, value=0x0A (=1024)
        param = struct.pack(">BBB", 0xC0, 1, 0x0A)
        conn._parse_cotp_cc(base + param)
        assert conn.pdu_size == 1024

    def test_cc_with_pdu_size_param_2byte(self) -> None:
        conn = ISOTCPConnection("1.2.3.4")
        base = struct.pack(">BBHHB", 11, 0xD0, 0x0001, 0x0001, 0x00)
        # PDU size parameter: code=0xC0, len=2, value=2048
        param = struct.pack(">BBH", 0xC0, 2, 2048)
        conn._parse_cotp_cc(base + param)
        assert conn.pdu_size == 2048


class TestParseCOTPParameters:
    """Test COTP parameter parsing edge cases."""

    def test_unknown_parameter(self) -> None:
        conn = ISOTCPConnection("1.2.3.4")
        # Unknown param code 0xFF, length 1, data 0x00
        params = struct.pack(">BBB", 0xFF, 1, 0x00)
        conn._parse_cotp_parameters(params)
        # Should not crash; pdu_size should remain default
        assert conn.pdu_size == 240

    def test_truncated_params(self) -> None:
        conn = ISOTCPConnection("1.2.3.4")
        # Just one byte — should break out of loop
        conn._parse_cotp_parameters(b"\xc0")
        assert conn.pdu_size == 240

    def test_param_len_exceeds_data(self) -> None:
        conn = ISOTCPConnection("1.2.3.4")
        # code=0xC0, len=5, but only 1 byte of data follows
        params = struct.pack(">BBB", 0xC0, 5, 0x0A)
        conn._parse_cotp_parameters(params)
        # Should break early without error
        assert conn.pdu_size == 240

    @pytest.mark.parametrize(
        "params",
        [
            struct.pack(">BBB", 0xC0, 1, 0x00),
            struct.pack(">BBB", 0xC0, 1, 0xFF),
            struct.pack(">BBH", 0xC0, 2, 127),
            struct.pack(">BBH", 0xC0, 2, 8193),
        ],
    )
    def test_invalid_pdu_size_keeps_default(self, params: bytes) -> None:
        conn = ISOTCPConnection("1.2.3.4")

        conn._parse_cotp_parameters(params)

        assert conn.pdu_size == 240


class TestParseCOTPData:
    """Test COTP Data Transfer parsing."""

    def test_valid_dt(self) -> None:
        conn = ISOTCPConnection("1.2.3.4")
        pdu = struct.pack(">BBB", 2, 0xF0, 0x80) + b"\xde\xad"
        result = conn._parse_cotp_data(pdu)
        assert result == b"\xde\xad"

    def test_dt_too_short(self) -> None:
        conn = ISOTCPConnection("1.2.3.4")
        with pytest.raises(S7ConnectionError, match="too short"):
            conn._parse_cotp_data(b"\x02")

    def test_dt_wrong_type(self) -> None:
        conn = ISOTCPConnection("1.2.3.4")
        pdu = struct.pack(">BBB", 2, 0xD0, 0x80)  # CC instead of DT
        with pytest.raises(S7ConnectionError, match="Expected COTP DT"):
            conn._parse_cotp_data(pdu)


class TestSendData:
    """Test send_data() error paths."""

    def test_send_when_not_connected(self) -> None:
        conn = ISOTCPConnection("1.2.3.4")
        with pytest.raises(S7ConnectionError, match="Not connected"):
            conn.send_data(b"\x00")

    def test_send_socket_error(self) -> None:
        conn = ISOTCPConnection("1.2.3.4")
        conn.connected = True
        conn.socket = MagicMock()
        conn.socket.sendall.side_effect = socket.error("broken pipe")
        with pytest.raises(S7ConnectionError, match="Send failed"):
            conn.send_data(b"\x00")
        assert conn.connected is False


class TestReceiveData:
    """Test receive_data() error paths."""

    def test_receive_when_not_connected(self) -> None:
        conn = ISOTCPConnection("1.2.3.4")
        with pytest.raises(S7ConnectionError, match="Not connected"):
            conn.receive_data()

    def test_receive_invalid_tpkt_version(self) -> None:
        conn = ISOTCPConnection("1.2.3.4")
        conn.connected = True
        mock_socket = MagicMock()
        conn.socket = mock_socket
        # TPKT with version 5 instead of 3
        mock_socket.recv.return_value = struct.pack(">BBH", 5, 0, 10)
        with pytest.raises(S7ConnectionError, match="Invalid TPKT version"):
            conn.receive_data()

    def test_receive_invalid_tpkt_length(self) -> None:
        conn = ISOTCPConnection("1.2.3.4")
        conn.connected = True
        mock_socket = MagicMock()
        conn.socket = mock_socket
        # Length = 3, remaining = -1
        mock_socket.recv.return_value = struct.pack(">BBH", 3, 0, 3)
        with pytest.raises(S7ConnectionError, match="Invalid TPKT length"):
            conn.receive_data()

    def test_receive_timeout(self) -> None:
        conn = ISOTCPConnection("1.2.3.4")
        conn.connected = True
        mock_socket = MagicMock()
        conn.socket = mock_socket
        mock_socket.recv.side_effect = socket.timeout("timeout")
        with pytest.raises(S7TimeoutError, match="Receive timeout"):
            conn.receive_data()
        assert conn.connected is False

    def test_receive_socket_error(self) -> None:
        conn = ISOTCPConnection("1.2.3.4")
        conn.connected = True
        mock_socket = MagicMock()
        conn.socket = mock_socket
        # First recv returns valid TPKT header, second raises error
        mock_socket.recv.side_effect = [struct.pack(">BBH", 3, 0, 10), socket.error("reset")]
        with pytest.raises(S7ConnectionError, match="Receive error"):
            conn.receive_data()
        assert conn.connected is False


class TestRecvExact:
    """Test _recv_exact() with various scenarios."""

    def test_socket_none(self) -> None:
        conn = ISOTCPConnection("1.2.3.4")
        with pytest.raises(S7ConnectionError, match="Socket not initialized"):
            conn._recv_exact(4)

    def test_connection_closed(self) -> None:
        conn = ISOTCPConnection("1.2.3.4")
        conn.socket = MagicMock()
        conn.socket.recv.return_value = b""  # empty = connection closed
        with pytest.raises(S7ConnectionError, match="Connection closed"):
            conn._recv_exact(4)
        assert conn.connected is False

    def test_partial_reads(self) -> None:
        conn = ISOTCPConnection("1.2.3.4")
        conn.socket = MagicMock()
        conn.socket.recv.side_effect = [b"\x01\x02", b"\x03\x04"]
        result = conn._recv_exact(4)
        assert result == b"\x01\x02\x03\x04"

    def test_timeout(self) -> None:
        conn = ISOTCPConnection("1.2.3.4")
        conn.socket = MagicMock()
        conn.socket.recv.side_effect = socket.timeout("timeout")
        with pytest.raises(S7TimeoutError):
            conn._recv_exact(4)

    def test_socket_error(self) -> None:
        conn = ISOTCPConnection("1.2.3.4")
        conn.socket = MagicMock()
        conn.socket.recv.side_effect = socket.error("broken")
        with pytest.raises(S7ConnectionError, match="Receive error"):
            conn._recv_exact(4)


class TestConnect:
    """Test connect() orchestration."""

    @patch.object(ISOTCPConnection, "_tcp_connect")
    @patch.object(ISOTCPConnection, "_iso_connect")
    def test_successful_connect(self, mock_iso: MagicMock, mock_tcp: MagicMock) -> None:
        conn = ISOTCPConnection("1.2.3.4")
        conn.connect(timeout=2.0)
        assert conn.connected is True
        assert conn.timeout == 2.0
        mock_tcp.assert_called_once()
        mock_iso.assert_called_once()

    @patch.object(ISOTCPConnection, "_tcp_connect", side_effect=OSError("connection refused"))
    @patch.object(ISOTCPConnection, "disconnect")
    def test_connect_failure_wraps_in_s7error(self, mock_disc: MagicMock, mock_tcp: MagicMock) -> None:
        conn = ISOTCPConnection("1.2.3.4")
        with pytest.raises(S7ConnectionError, match="Connection failed"):
            conn.connect()
        mock_disc.assert_called_once()

    @patch.object(ISOTCPConnection, "_tcp_connect")
    @patch.object(ISOTCPConnection, "_iso_connect", side_effect=S7ConnectionError("COTP fail"))
    @patch.object(ISOTCPConnection, "disconnect")
    def test_connect_reraises_s7_errors(self, mock_disc: MagicMock, mock_iso: MagicMock, mock_tcp: MagicMock) -> None:
        conn = ISOTCPConnection("1.2.3.4")
        with pytest.raises(S7ConnectionError, match="COTP fail"):
            conn.connect()


class TestDisconnect:
    """Test disconnect() behavior."""

    def test_disconnect_when_no_socket(self) -> None:
        conn = ISOTCPConnection("1.2.3.4")
        # Should not raise
        conn.disconnect()

    def test_disconnect_closes_socket(self) -> None:
        conn = ISOTCPConnection("1.2.3.4")
        mock_socket = MagicMock()
        mock_socket.recv.return_value = b""
        conn.socket = mock_socket
        conn.connected = True
        conn.disconnect()
        mock_socket.close.assert_called_once()
        assert conn.socket is None
        assert conn.connected is False

    def test_disconnect_ignores_errors(self) -> None:
        conn = ISOTCPConnection("1.2.3.4")
        mock_socket = MagicMock()
        mock_socket.close.side_effect = OSError("already closed")
        conn.socket = mock_socket
        conn.connected = False
        conn.disconnect()
        assert conn.socket is None


class TestDisconnectClosesTheTcpConnection:
    """disconnect() sends no COTP DR: it sends a FIN and lets the peer close first (#972)."""

    @staticmethod
    def _connected_pair() -> tuple[ISOTCPConnection, socket.socket]:
        ours, peer = socket.socketpair()
        conn = ISOTCPConnection("1.2.3.4")
        conn.socket = ours
        conn.connected = True
        conn.dst_ref = 0x4431
        return conn, peer

    def test_peer_sees_only_a_fin_and_can_still_answer(self) -> None:
        conn, peer = self._connected_pair()
        seen: dict[str, object] = {}

        def answer() -> None:
            peer.settimeout(2.0)
            seen["received"] = peer.recv(64)
            # Our side is only half closed: the peer can still send before it closes.
            try:
                peer.sendall(b"late")
                seen["could_send"] = True
            except OSError:
                seen["could_send"] = False
            peer.close()

        thread = threading.Thread(target=answer)
        thread.start()
        start = time.monotonic()
        conn.disconnect()
        elapsed = time.monotonic() - start
        thread.join(5.0)

        assert seen["received"] == b""  # a FIN, and no disconnect request before it
        assert seen["could_send"] is True
        assert elapsed < 0.5  # returned when the peer closed, not at the timeout
        assert conn.socket is None and conn.connected is False

    def test_returns_when_the_peer_has_closed(self) -> None:
        conn, peer = self._connected_pair()
        peer.close()
        start = time.monotonic()
        conn.disconnect()
        assert time.monotonic() - start < 0.5
        assert conn.socket is None

    def test_silent_peer_is_bounded(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(ISOTCPConnection, "DISCONNECT_CLOSE_TIMEOUT", 0.2)
        conn, peer = self._connected_pair()
        start = time.monotonic()
        conn.disconnect()
        elapsed = time.monotonic() - start
        peer.close()
        assert 0.15 <= elapsed < 1.0

    def test_discards_data_in_flight(self) -> None:
        conn, peer = self._connected_pair()
        peer.sendall(bytes.fromhex("03 00 00 07 02 f0 80"))
        peer.close()
        start = time.monotonic()
        conn.disconnect()
        assert time.monotonic() - start < 0.5

    def test_socket_is_closed_when_shutdown_fails(self) -> None:
        conn = ISOTCPConnection("1.2.3.4")
        sock = MagicMock()
        sock.shutdown.side_effect = OSError("not connected")
        conn.socket = sock
        conn.connected = True
        conn.disconnect()
        sock.close.assert_called_once()
        assert conn.socket is None and conn.connected is False


class TestContextManager:
    """Test __enter__ / __exit__."""

    def test_enter_returns_self(self) -> None:
        conn = ISOTCPConnection("1.2.3.4")
        assert conn.__enter__() is conn

    def test_exit_calls_disconnect(self) -> None:
        conn = ISOTCPConnection("1.2.3.4")
        conn.socket = MagicMock()
        conn.socket.recv.return_value = b""
        conn.connected = True
        conn.__exit__(None, None, None)
        assert conn.socket is None
        assert conn.connected is False

    def test_context_manager_protocol(self) -> None:
        conn = ISOTCPConnection("1.2.3.4")
        with conn as c:
            assert c is conn
        assert conn.connected is False


class TestCheckConnection:
    """Test check_connection() method."""

    def test_not_connected(self) -> None:
        conn = ISOTCPConnection("1.2.3.4")
        assert conn.check_connection() is False

    def test_socket_none(self) -> None:
        conn = ISOTCPConnection("1.2.3.4")
        conn.connected = True
        conn.socket = None
        assert conn.check_connection() is False

    def test_connection_alive_no_data(self) -> None:
        conn = ISOTCPConnection("1.2.3.4")
        conn.connected = True
        mock_socket = MagicMock()
        conn.socket = mock_socket
        mock_socket.gettimeout.return_value = 5.0
        mock_socket.recv.side_effect = BlockingIOError
        assert conn.check_connection() is True

    def test_connection_alive_with_data(self) -> None:
        conn = ISOTCPConnection("1.2.3.4")
        conn.connected = True
        mock_socket = MagicMock()
        conn.socket = mock_socket
        mock_socket.gettimeout.return_value = 5.0
        mock_socket.recv.return_value = b"\x00"
        assert conn.check_connection() is True

    def test_connection_closed_by_peer(self) -> None:
        conn = ISOTCPConnection("1.2.3.4")
        conn.connected = True
        mock_socket = MagicMock()
        conn.socket = mock_socket
        mock_socket.gettimeout.return_value = 5.0
        mock_socket.recv.return_value = b""
        assert conn.check_connection() is False
        assert conn.connected is False

    def test_connection_socket_error(self) -> None:
        conn = ISOTCPConnection("1.2.3.4")
        conn.connected = True
        mock_socket = MagicMock()
        conn.socket = mock_socket
        mock_socket.gettimeout.return_value = 5.0
        mock_socket.recv.side_effect = socket.error("reset")
        assert conn.check_connection() is False
        assert conn.connected is False

    def test_connection_exception_in_outer_try(self) -> None:
        conn = ISOTCPConnection("1.2.3.4")
        conn.connected = True
        mock_socket = MagicMock()
        conn.socket = mock_socket
        mock_socket.gettimeout.side_effect = Exception("unexpected")
        assert conn.check_connection() is False


class TestTCPConnect:
    """Test _tcp_connect()."""

    @patch("snap7.connection.socket.socket")
    def test_tcp_connect_failure(self, mock_socket_cls: MagicMock) -> None:
        mock_sock = MagicMock()
        mock_socket_cls.return_value = mock_sock
        mock_sock.connect.side_effect = socket.error("refused")
        conn = ISOTCPConnection("1.2.3.4")
        with pytest.raises(S7ConnectionError, match="TCP connection failed"):
            conn._tcp_connect()

    @patch("snap7.connection.socket.socket")
    def test_tcp_connect_success(self, mock_socket_cls: MagicMock) -> None:
        mock_sock = MagicMock()
        mock_socket_cls.return_value = mock_sock
        conn = ISOTCPConnection("1.2.3.4")
        conn._tcp_connect()
        mock_sock.settimeout.assert_called_once()
        mock_sock.connect.assert_called_once_with(("1.2.3.4", 102))

    @patch("snap7.connection.socket.socket")
    def test_tcp_connect_sets_tcp_nodelay(self, mock_socket_cls: MagicMock) -> None:
        """TCP_NODELAY must be set to eliminate Nagle buffering latency."""
        import socket as _socket

        mock_sock = MagicMock()
        mock_socket_cls.return_value = mock_sock
        conn = ISOTCPConnection("1.2.3.4")
        conn._tcp_connect()
        mock_sock.setsockopt.assert_any_call(_socket.IPPROTO_TCP, _socket.TCP_NODELAY, 1)

    @patch("snap7.connection.socket.socket")
    def test_tcp_connect_sets_so_keepalive(self, mock_socket_cls: MagicMock) -> None:
        """SO_KEEPALIVE must be set to detect dead connections during idle periods."""
        import socket as _socket

        mock_sock = MagicMock()
        mock_socket_cls.return_value = mock_sock
        conn = ISOTCPConnection("1.2.3.4")
        conn._tcp_connect()
        mock_sock.setsockopt.assert_any_call(_socket.SOL_SOCKET, _socket.SO_KEEPALIVE, 1)

    @patch("snap7.connection.socket.socket")
    @patch("snap7.connection.socket")
    def test_tcp_connect_sets_keepalive_timing(self, mock_socket_mod: MagicMock, mock_socket_cls: MagicMock) -> None:
        """Keepalive timing parameters must be set when the platform supports them."""
        import socket as _socket

        # Simulate a platform that has all three timing attributes
        mock_socket_mod.AF_INET = _socket.AF_INET
        mock_socket_mod.SOCK_STREAM = _socket.SOCK_STREAM
        mock_socket_mod.SOL_SOCKET = _socket.SOL_SOCKET
        mock_socket_mod.SO_KEEPALIVE = _socket.SO_KEEPALIVE
        mock_socket_mod.IPPROTO_TCP = _socket.IPPROTO_TCP
        mock_socket_mod.TCP_NODELAY = _socket.TCP_NODELAY
        mock_socket_mod.TCP_KEEPIDLE = 4  # simulate attribute present
        mock_socket_mod.TCP_KEEPINTVL = 5
        mock_socket_mod.TCP_KEEPCNT = 6

        mock_sock = MagicMock()
        mock_socket_mod.socket.return_value = mock_sock

        conn = ISOTCPConnection("1.2.3.4")
        conn._tcp_connect()

        mock_sock.setsockopt.assert_any_call(_socket.IPPROTO_TCP, 4, 60)
        mock_sock.setsockopt.assert_any_call(_socket.IPPROTO_TCP, 5, 10)
        mock_sock.setsockopt.assert_any_call(_socket.IPPROTO_TCP, 6, 3)


class TestISOConnect:
    """Test _iso_connect()."""

    def test_iso_connect_no_socket(self) -> None:
        conn = ISOTCPConnection("1.2.3.4")
        conn.socket = None
        with pytest.raises(S7ConnectionError, match="Socket not initialized"):
            conn._iso_connect()

    def test_iso_connect_bad_tpkt_version(self) -> None:
        conn = ISOTCPConnection("1.2.3.4")
        mock_socket = MagicMock()
        conn.socket = mock_socket
        # Build a valid CC response wrapped in a bad TPKT
        cc = struct.pack(">BBHHB", 6, 0xD0, 0x0001, 0x0001, 0x00)
        bad_tpkt = struct.pack(">BBH", 5, 0, 4 + len(cc))
        mock_socket.recv.side_effect = [bad_tpkt, cc]
        with pytest.raises(S7ConnectionError, match="Invalid TPKT version"):
            conn._iso_connect()
