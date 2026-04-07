import logging
import socket
import struct
import threading
import time

import pytest
import unittest as unittest
from snap7.connection import ISOTCPConnection
from snap7.error import error_text, S7Error, S7ConnectionError

import snap7.partner
from snap7.partner import Partner, PartnerStatus
from snap7.type import Parameter

logging.basicConfig(level=logging.WARNING)


@pytest.mark.partner
class TestPartner(unittest.TestCase):
    def setUp(self) -> None:
        self.partner = snap7.partner.Partner()
        self.partner.port = 12103  # Use unique port for partner tests
        self.partner.remote_port = 12103
        self.partner.start()

    def tearDown(self) -> None:
        self.partner.stop()
        self.partner.destroy()

    def test_as_b_send(self) -> None:
        self.partner.as_b_send()

    def test_b_send_recv(self) -> None:
        self.partner.b_send()
        # self.partner.b_recv()

    def test_check_as_b_recv_completion(self) -> None:
        self.partner.check_as_b_recv_completion()

    def test_check_as_b_send_completion(self) -> None:
        self.partner.check_as_b_send_completion()

    def test_create(self) -> None:
        self.partner.create()

    def test_destroy(self) -> None:
        self.partner.destroy()

    def test_error_text(self) -> None:
        error_text(0, context="partner")

    def test_get_last_error(self) -> None:
        self.partner.get_last_error()

    def test_get_param(self) -> None:
        expected = (
            (Parameter.LocalPort, 0),
            (Parameter.RemotePort, 12103),  # Non-privileged port for tests
            (Parameter.PingTimeout, 750),
            (Parameter.SendTimeout, 10),
            (Parameter.RecvTimeout, 3000),
            (Parameter.SrcRef, 256),
            (Parameter.DstRef, 0),
            (Parameter.PDURequest, 480),
            (Parameter.WorkInterval, 100),
            (Parameter.BSendTimeout, 3000),
            (Parameter.BRecvTimeout, 3000),
            (Parameter.RecoveryTime, 500),
            (Parameter.KeepAliveTime, 5000),
        )
        for param, value in expected:
            self.assertEqual(self.partner.get_param(param), value)

        self.assertRaises(Exception, self.partner.get_param, Parameter.MaxClients)

    def test_get_stats(self) -> None:
        self.partner.get_stats()

    def test_get_status(self) -> None:
        self.partner.get_status()

    def test_get_times(self) -> None:
        self.partner.get_times()

    def test_set_param(self) -> None:
        values = (
            (Parameter.PingTimeout, 800),
            (Parameter.SendTimeout, 15),
            (Parameter.RecvTimeout, 3500),
            (Parameter.WorkInterval, 50),
            (Parameter.SrcRef, 128),
            (Parameter.DstRef, 128),
            (Parameter.SrcTSap, 128),
            (Parameter.PDURequest, 470),
            (Parameter.BSendTimeout, 2000),
            (Parameter.BRecvTimeout, 2000),
            (Parameter.RecoveryTime, 400),
            (Parameter.KeepAliveTime, 4000),
        )
        for param, value in values:
            self.partner.set_param(param, value)

        self.assertRaises(Exception, self.partner.set_param, Parameter.RemotePort, 1)

    def test_set_recv_callback(self) -> None:
        self.partner.set_recv_callback()

    def test_set_send_callback(self) -> None:
        self.partner.set_send_callback()

    def test_start(self) -> None:
        self.partner.start()

    def test_start_to(self) -> None:
        self.partner.start_to("0.0.0.0", "0.0.0.0", 0, 0)  # noqa: S104

    def test_stop(self) -> None:
        self.partner.stop()

    def test_wait_as_b_send_completion(self) -> None:
        self.assertRaises(RuntimeError, self.partner.wait_as_b_send_completion)


def _free_port() -> int:
    """Return a free TCP port chosen by the OS."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        port: int = s.getsockname()[1]
        return port


# ---------------------------------------------------------------------------
# PDU building / parsing unit tests (no network required)
# ---------------------------------------------------------------------------


@pytest.mark.partner
class TestPartnerPDU:
    """Unit tests for partner PDU building and parsing."""

    def test_build_partner_data_pdu_small(self) -> None:
        p = Partner()
        data = b"\x01\x02\x03"
        pdu = p._build_partner_data_pdu(data)
        # S7 USERDATA header
        assert pdu[0:1] == b"\x32"
        assert pdu[1:2] == b"\x07"
        # Roundtrip recovers the payload
        payload, r_id, pdu_ref = p._parse_partner_data_pdu(pdu)
        assert payload == data

    def test_build_partner_data_pdu_empty(self) -> None:
        p = Partner()
        pdu = p._build_partner_data_pdu(b"")
        assert pdu[0:1] == b"\x32"
        payload, _, _ = p._parse_partner_data_pdu(pdu)
        assert payload == b""

    def test_build_partner_data_pdu_large(self) -> None:
        p = Partner()
        data = bytes(range(256)) * 4  # 1024 bytes
        pdu = p._build_partner_data_pdu(data)
        payload, _, _ = p._parse_partner_data_pdu(pdu)
        assert payload == data

    def test_build_partner_data_pdu_r_id(self) -> None:
        """R-ID is embedded in the data section and extracted by parser."""
        p = Partner()
        p.r_id = 0xDEADBEEF
        pdu = p._build_partner_data_pdu(b"\x01")
        payload, r_id, _pdu_ref = p._parse_partner_data_pdu(pdu)
        assert payload == b"\x01"
        assert r_id == 0xDEADBEEF

    def test_parse_partner_data_pdu_roundtrip(self) -> None:
        p = Partner()
        original = b"Hello, Partner!"
        pdu = p._build_partner_data_pdu(original)
        parsed, _, _ = p._parse_partner_data_pdu(pdu)
        assert parsed == original

    def test_parse_partner_data_pdu_roundtrip_various_sizes(self) -> None:
        p = Partner()
        for size in [0, 1, 10, 100, 500, 1024]:
            data = (bytes(range(256)) * (size // 256 + 1))[:size]
            pdu = p._build_partner_data_pdu(data)
            payload, _, _ = p._parse_partner_data_pdu(pdu)
            assert payload == data

    def test_parse_partner_data_pdu_too_short(self) -> None:
        p = Partner()
        with pytest.raises(S7Error, match="too short"):
            p._parse_partner_data_pdu(b"\x32\x07\x00")

    def test_build_partner_ack(self) -> None:
        p = Partner()
        ack = p._build_partner_ack()
        # S7 USERDATA header (10 bytes) + parameter section + data section
        assert ack[0:1] == b"\x32"
        assert ack[1:2] == b"\x07"  # USERDATA type

    def test_build_partner_ack_pdu_ref(self) -> None:
        """ACK echoes the PDU reference from the data PDU."""
        p = Partner()
        ack = p._build_partner_ack(pdu_ref=0x1234)
        _, _, _, pdu_ref, _, _ = struct.unpack(">BBHHHH", ack[:10])
        assert pdu_ref == 0x1234

    def test_parse_partner_ack_valid(self) -> None:
        p = Partner()
        ack = p._build_partner_ack()
        p._parse_partner_ack(ack)

    def test_parse_partner_ack_too_short(self) -> None:
        p = Partner()
        with pytest.raises(S7Error, match="too short"):
            p._parse_partner_ack(b"\x32")

    def test_parse_partner_ack_wrong_type(self) -> None:
        p = Partner()
        # Build a PDU with REQUEST type instead of USERDATA
        bad_ack = struct.pack(">BBHHHH", 0x32, 0x01, 0x0000, 0x0000, 0x0000, 0x0000)
        with pytest.raises(S7Error, match="Expected partner ACK"):
            p._parse_partner_ack(bad_ack)

    def test_ack_roundtrip(self) -> None:
        p = Partner()
        ack = p._build_partner_ack()
        p._parse_partner_ack(ack)


# ---------------------------------------------------------------------------
# Status, stats, lifecycle tests
# ---------------------------------------------------------------------------


@pytest.mark.partner
class TestPartnerLifecycle:
    """Tests for partner lifecycle, status, and context manager."""

    def test_initial_status_stopped(self) -> None:
        p = Partner()
        assert p.get_status().value == PartnerStatus.STOPPED

    def test_status_running_passive(self) -> None:
        port = _free_port()
        p = Partner(active=False)
        p.port = port
        try:
            p.start_to("127.0.0.1", "", 0x0100, 0x0102)
            assert p.running is True
            assert p.get_status().value == PartnerStatus.RUNNING
        finally:
            p.stop()

    def test_stop_idempotent(self) -> None:
        p = Partner()
        p.stop()
        p.stop()

    def test_destroy_returns_zero(self) -> None:
        p = Partner()
        assert p.destroy() == 0

    def test_context_manager(self) -> None:
        port = _free_port()
        with Partner(active=False) as p:
            p.port = port
            p.start_to("127.0.0.1", "", 0x0100, 0x0102)
            assert p.running is True
        assert p.running is False

    def test_del_cleanup(self) -> None:
        port = _free_port()
        p = Partner(active=False)
        p.port = port
        p.start_to("127.0.0.1", "", 0x0100, 0x0102)
        assert p.running is True
        p.__del__()
        assert p.running is False

    def test_create_noop(self) -> None:
        p = Partner()
        p.create(active=True)

    def test_get_stats_initial(self) -> None:
        p = Partner()
        sent, recv, s_err, r_err = p.get_stats()
        assert sent.value == 0
        assert recv.value == 0
        assert s_err.value == 0
        assert r_err.value == 0

    def test_get_times_initial(self) -> None:
        p = Partner()
        send_t, recv_t = p.get_times()
        assert send_t.value == 0
        assert recv_t.value == 0

    def test_get_last_error_initial(self) -> None:
        p = Partner()
        assert p.get_last_error().value == 0


# ---------------------------------------------------------------------------
# Send / recv data buffer tests
# ---------------------------------------------------------------------------


@pytest.mark.partner
class TestPartnerSendRecvBuffers:
    """Tests for set_send_data / get_recv_data and error paths."""

    def test_set_send_data_and_retrieve(self) -> None:
        p = Partner()
        assert p._send_data is None
        p.set_send_data(b"test")
        assert p._send_data == b"test"

    def test_get_recv_data_initially_none(self) -> None:
        p = Partner()
        assert p.get_recv_data() is None

    def test_b_send_no_data(self) -> None:
        p = Partner()
        assert p.b_send() == -1

    def test_b_send_not_connected(self) -> None:
        p = Partner()
        p.set_send_data(b"data")
        with pytest.raises(S7ConnectionError, match="Not connected"):
            p.b_send()

    def test_b_recv_not_connected(self) -> None:
        p = Partner()
        result = p.b_recv()
        assert result == -1
        assert p.get_recv_data() is None

    def test_as_b_send_no_data(self) -> None:
        p = Partner()
        assert p.as_b_send() == -1

    def test_as_b_send_not_connected(self) -> None:
        p = Partner()
        p.set_send_data(b"data")
        result = p.as_b_send()
        assert result == -1

    def test_as_b_recv_not_connected(self) -> None:
        p = Partner()
        assert p.as_b_recv() == -1

    def test_as_b_recv_already_in_progress(self) -> None:
        p = Partner()
        p.connected = True
        p._async_recv_in_progress = True
        assert p.as_b_recv() == -1
        p._async_recv_in_progress = False

    def test_wait_as_b_recv_no_operation(self) -> None:
        p = Partner()
        with pytest.raises(RuntimeError, match="No async receive"):
            p.wait_as_b_recv_completion()

    def test_wait_as_b_recv_timeout(self) -> None:
        p = Partner()
        p._async_recv_in_progress = True
        result = p.wait_as_b_recv_completion(timeout=50)
        assert result == -1
        p._async_recv_in_progress = False

    def test_wait_as_b_recv_completes(self) -> None:
        p = Partner()
        p._async_recv_in_progress = True
        p._async_recv_result = 0

        def clear_flag() -> None:
            time.sleep(0.05)
            p._async_recv_in_progress = False

        t = threading.Thread(target=clear_flag)
        t.start()
        result = p.wait_as_b_recv_completion(timeout=2000)
        t.join()
        assert result == 0

    def test_check_as_b_recv_completion_error(self) -> None:
        p = Partner()
        p._async_recv_result = -1
        assert p.check_as_b_recv_completion() == -1
        p._async_recv_result = 0

    def test_check_as_b_recv_completion_empty(self) -> None:
        p = Partner()
        assert p.check_as_b_recv_completion() == 1

    def test_check_as_b_recv_completion_with_data(self) -> None:
        p = Partner()
        p._async_recv_queue.put(b"queued data")
        assert p.check_as_b_recv_completion() == 0
        assert p._recv_data == b"queued data"

    def test_check_as_b_send_completion_not_in_progress(self) -> None:
        p = Partner()
        status, result = p.check_as_b_send_completion()
        assert status == "job complete"

    def test_check_as_b_send_completion_in_progress(self) -> None:
        p = Partner()
        p._async_send_in_progress = True
        status, result = p.check_as_b_send_completion()
        assert status == "job in progress"

    def test_wait_as_b_send_no_operation(self) -> None:
        p = Partner()
        with pytest.raises(RuntimeError, match="No async send"):
            p.wait_as_b_send_completion()

    def test_wait_as_b_send_timeout(self) -> None:
        p = Partner()
        p._async_send_in_progress = True
        result = p.wait_as_b_send_completion(timeout=50)
        assert result == -1

    def test_wait_as_b_send_completes(self) -> None:
        p = Partner()
        p._async_send_in_progress = True
        p._async_send_result = 0

        def clear_flag() -> None:
            time.sleep(0.05)
            p._async_send_in_progress = False

        t = threading.Thread(target=clear_flag)
        t.start()
        result = p.wait_as_b_send_completion(timeout=2000)
        t.join()
        assert result == 0


# ---------------------------------------------------------------------------
# Parameter tests
# ---------------------------------------------------------------------------


@pytest.mark.partner
class TestPartnerParams:
    """Tests for get_param / set_param."""

    def test_get_param_unsupported(self) -> None:
        p = Partner()
        with pytest.raises(RuntimeError, match="not supported"):
            p.get_param(Parameter.MaxClients)

    def test_set_param_remote_port_raises(self) -> None:
        p = Partner()
        with pytest.raises(RuntimeError, match="Cannot set"):
            p.set_param(Parameter.RemotePort, 1234)

    def test_set_param_local_port(self) -> None:
        p = Partner()
        p.set_param(Parameter.LocalPort, 5555)
        assert p.local_port == 5555

    def test_set_param_returns_zero(self) -> None:
        p = Partner()
        assert p.set_param(Parameter.PingTimeout, 999) == 0

    def test_set_recv_callback_returns_zero(self) -> None:
        p = Partner()
        assert p.set_recv_callback() == 0

    def test_set_recv_callback_with_function(self) -> None:
        p = Partner()
        assert p.set_recv_callback(lambda data: None) == 0
        assert p._recv_callback is not None
        assert p.set_recv_callback(None) == 0
        assert p._recv_callback is None

    def test_set_send_callback_returns_zero(self) -> None:
        p = Partner()
        assert p.set_send_callback() == 0

    def test_set_send_callback_with_function(self) -> None:
        p = Partner()
        assert p.set_send_callback(lambda result: None) == 0
        assert p._send_callback_fn is not None
        assert p.set_send_callback(None) == 0
        assert p._send_callback_fn is None


# ---------------------------------------------------------------------------
# Dual-partner integration tests using raw socket pairing
# ---------------------------------------------------------------------------


def _make_socket_pair() -> tuple[socket.socket, socket.socket]:
    """Create a connected TCP socket pair via a temporary server socket."""
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("127.0.0.1", 0))
    srv.listen(1)
    port = srv.getsockname()[1]

    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect(("127.0.0.1", port))
    server_side, _ = srv.accept()
    srv.close()
    return client, server_side


def _wire_partner(partner: Partner, sock: socket.socket) -> None:
    """Wire a connected socket into a Partner so it appears connected."""
    conn = ISOTCPConnection(host="127.0.0.1", port=0, local_tsap=0x0100, remote_tsap=0x0102)
    conn.socket = sock
    conn.connected = True
    partner._socket = sock
    partner._connection = conn
    partner.connected = True
    partner.running = True


@pytest.mark.partner
class TestDualPartner:
    """Integration tests using two Partner instances exchanging data over sockets."""

    def test_active_to_passive_send(self) -> None:
        sock_a, sock_b = _make_socket_pair()
        pa, pb = Partner(), Partner()
        try:
            _wire_partner(pa, sock_a)
            _wire_partner(pb, sock_b)

            payload = b"Hello from A"
            pa.set_send_data(payload)

            errors: list[Exception] = []

            def do_send() -> None:
                try:
                    pa.b_send()
                except Exception as e:
                    errors.append(e)

            t = threading.Thread(target=do_send)
            t.start()

            assert pb.b_recv() == 0
            t.join(timeout=3.0)
            assert pb.get_recv_data() == payload
            assert not errors
        finally:
            pa.stop()
            pb.stop()

    def test_passive_to_active_send(self) -> None:
        sock_a, sock_b = _make_socket_pair()
        pa, pb = Partner(), Partner()
        try:
            _wire_partner(pa, sock_a)
            _wire_partner(pb, sock_b)

            payload = b"Hello from B"
            pb.set_send_data(payload)

            errors: list[Exception] = []

            def do_send() -> None:
                try:
                    pb.b_send()
                except Exception as e:
                    errors.append(e)

            t = threading.Thread(target=do_send)
            t.start()

            assert pa.b_recv() == 0
            t.join(timeout=3.0)
            assert pa.get_recv_data() == payload
            assert not errors
        finally:
            pa.stop()
            pb.stop()

    def test_bidirectional_exchange(self) -> None:
        sock_a, sock_b = _make_socket_pair()
        pa, pb = Partner(), Partner()
        try:
            _wire_partner(pa, sock_a)
            _wire_partner(pb, sock_b)

            errors: list[Exception] = []

            # A -> B
            pa.set_send_data(b"A->B")

            def send_a() -> None:
                try:
                    pa.b_send()
                except Exception as e:
                    errors.append(e)

            t1 = threading.Thread(target=send_a)
            t1.start()
            pb.b_recv()
            t1.join(timeout=3.0)
            assert pb.get_recv_data() == b"A->B"

            # B -> A
            pb.set_send_data(b"B->A")

            def send_b() -> None:
                try:
                    pb.b_send()
                except Exception as e:
                    errors.append(e)

            t2 = threading.Thread(target=send_b)
            t2.start()
            pa.b_recv()
            t2.join(timeout=3.0)
            assert pa.get_recv_data() == b"B->A"
            assert not errors
        finally:
            pa.stop()
            pb.stop()

    def test_various_payload_sizes(self) -> None:
        sock_a, sock_b = _make_socket_pair()
        pa, pb = Partner(), Partner()
        try:
            _wire_partner(pa, sock_a)
            _wire_partner(pb, sock_b)

            for size in [1, 10, 100, 480]:
                payload = (bytes(range(256)) * (size // 256 + 1))[:size]
                pa.set_send_data(payload)
                errors: list[Exception] = []

                def do_send() -> None:
                    try:
                        pa.b_send()
                    except Exception as e:
                        errors.append(e)

                t = threading.Thread(target=do_send)
                t.start()
                pb.b_recv()
                t.join(timeout=3.0)
                assert pb.get_recv_data() == payload, f"Failed for size {size}"
                assert not errors
        finally:
            pa.stop()
            pb.stop()

    def test_stats_updated_after_exchange(self) -> None:
        sock_a, sock_b = _make_socket_pair()
        pa, pb = Partner(), Partner()
        try:
            _wire_partner(pa, sock_a)
            _wire_partner(pb, sock_b)

            payload = b"stats test"
            pa.set_send_data(payload)

            def do_send() -> None:
                pa.b_send()

            t = threading.Thread(target=do_send)
            t.start()
            pb.b_recv()
            t.join(timeout=3.0)

            sent, _, s_err, _ = pa.get_stats()
            assert sent.value == len(payload)
            assert s_err.value == 0

            _, recv, _, r_err = pb.get_stats()
            assert recv.value == len(payload)
            assert r_err.value == 0

            send_t, _ = pa.get_times()
            assert send_t.value >= 0
            _, recv_t = pb.get_times()
            assert recv_t.value >= 0
        finally:
            pa.stop()
            pb.stop()

    def test_status_connected(self) -> None:
        sock_a, sock_b = _make_socket_pair()
        pa, pb = Partner(), Partner()
        try:
            _wire_partner(pa, sock_a)
            _wire_partner(pb, sock_b)
            assert pa.get_status().value == PartnerStatus.CONNECTED
            assert pb.get_status().value == PartnerStatus.CONNECTED
        finally:
            pa.stop()
            pb.stop()

    def test_status_after_stop(self) -> None:
        sock_a, sock_b = _make_socket_pair()
        pa, pb = Partner(), Partner()
        try:
            _wire_partner(pa, sock_a)
            _wire_partner(pb, sock_b)
            pa.stop()
            assert pa.get_status().value == PartnerStatus.STOPPED
        finally:
            pa.stop()
            pb.stop()

    def test_recv_callback_fires(self) -> None:
        sock_a, sock_b = _make_socket_pair()
        pa, pb = Partner(), Partner()
        try:
            _wire_partner(pa, sock_a)
            _wire_partner(pb, sock_b)

            received_data: list[bytes] = []
            pb._recv_callback = lambda data: received_data.append(data)

            payload = b"callback test"
            pa.set_send_data(payload)

            def do_send() -> None:
                pa.b_send()

            t = threading.Thread(target=do_send)
            t.start()
            pb.b_recv()
            t.join(timeout=3.0)

            assert len(received_data) == 1
            assert received_data[0] == payload
        finally:
            pa.stop()
            pb.stop()

    def test_as_b_recv_with_check(self) -> None:
        """Async receive completes and data is available via check_as_b_recv_completion."""
        sock_a, sock_b = _make_socket_pair()
        pa, pb = Partner(), Partner()
        try:
            _wire_partner(pa, sock_a)
            _wire_partner(pb, sock_b)

            payload = b"async recv test"

            # Start async receive on B
            assert pb.as_b_recv() == 0

            # Send from A (in a thread because b_send blocks waiting for ACK)
            errors: list[Exception] = []

            def do_send() -> None:
                try:
                    pa.set_send_data(payload)
                    pa.b_send()
                except Exception as e:
                    errors.append(e)

            t = threading.Thread(target=do_send)
            t.start()

            # Poll until receive completes
            deadline = time.time() + 3.0
            while time.time() < deadline:
                if pb.check_as_b_recv_completion() == 0:
                    break
                time.sleep(0.01)

            t.join(timeout=3.0)
            assert not errors
            assert pb.get_recv_data() == payload
        finally:
            pa.stop()
            pb.stop()

    def test_as_b_recv_with_wait(self) -> None:
        """Async receive completes when using wait_as_b_recv_completion."""
        sock_a, sock_b = _make_socket_pair()
        pa, pb = Partner(), Partner()
        try:
            _wire_partner(pa, sock_a)
            _wire_partner(pb, sock_b)

            payload = b"wait recv test"

            assert pb.as_b_recv() == 0

            errors: list[Exception] = []

            def do_send() -> None:
                try:
                    pa.set_send_data(payload)
                    pa.b_send()
                except Exception as e:
                    errors.append(e)

            t = threading.Thread(target=do_send)
            t.start()

            result = pb.wait_as_b_recv_completion(timeout=3000)
            t.join(timeout=3.0)
            assert result == 0
            assert not errors
            assert pb.get_recv_data() == payload
        finally:
            pa.stop()
            pb.stop()

    def test_as_b_recv_callback_fires(self) -> None:
        """Receive callback is invoked during async receive."""
        sock_a, sock_b = _make_socket_pair()
        pa, pb = Partner(), Partner()
        try:
            _wire_partner(pa, sock_a)
            _wire_partner(pb, sock_b)

            received_data: list[bytes] = []
            pb.set_recv_callback(lambda data: received_data.append(data))

            payload = b"callback async"
            assert pb.as_b_recv() == 0

            errors: list[Exception] = []

            def do_send() -> None:
                try:
                    pa.set_send_data(payload)
                    pa.b_send()
                except Exception as e:
                    errors.append(e)

            t = threading.Thread(target=do_send)
            t.start()

            result = pb.wait_as_b_recv_completion(timeout=3000)
            t.join(timeout=3.0)
            assert result == 0
            assert not errors
            assert len(received_data) == 1
            assert received_data[0] == payload
        finally:
            pa.stop()
            pb.stop()

    def test_as_b_send_callback_fires(self) -> None:
        """Send callback is invoked during async send."""
        sock_a, sock_b = _make_socket_pair()
        pa, pb = Partner(), Partner()
        try:
            _wire_partner(pa, sock_a)
            _wire_partner(pb, sock_b)

            send_results: list[int] = []
            pa.set_send_callback(lambda result: send_results.append(result))

            payload = b"send callback"
            pa.set_send_data(payload)

            # Start async processor thread for pa
            pa._stop_event.clear()
            pa._async_thread = threading.Thread(target=pa._async_processor, daemon=True)
            pa._async_thread.start()

            assert pa.as_b_send() == 0

            # Receive on B side
            assert pb.b_recv() == 0

            # Wait for async send to complete
            deadline = time.time() + 3.0
            while pa._async_send_in_progress and time.time() < deadline:
                time.sleep(0.01)

            assert pb.get_recv_data() == payload
            assert len(send_results) == 1
            assert send_results[0] == 0
        finally:
            pa.stop()
            pb.stop()

    def test_as_b_recv_then_send(self) -> None:
        """After async recv completes, sending still works (lock coordination)."""
        sock_a, sock_b = _make_socket_pair()
        pa, pb = Partner(), Partner()
        try:
            _wire_partner(pa, sock_a)
            _wire_partner(pb, sock_b)

            # Phase 1: A sends, B receives async
            assert pb.as_b_recv() == 0

            errors: list[Exception] = []

            def do_send_a() -> None:
                try:
                    pa.set_send_data(b"phase1")
                    pa.b_send()
                except Exception as e:
                    errors.append(e)

            t1 = threading.Thread(target=do_send_a)
            t1.start()
            result = pb.wait_as_b_recv_completion(timeout=3000)
            t1.join(timeout=3.0)
            assert result == 0
            assert pb.get_recv_data() == b"phase1"
            assert not errors

            # Phase 2: B sends back, A receives sync
            pb.set_send_data(b"phase2")

            def do_send_b() -> None:
                try:
                    pb.b_send()
                except Exception as e:
                    errors.append(e)

            t2 = threading.Thread(target=do_send_b)
            t2.start()
            assert pa.b_recv() == 0
            t2.join(timeout=3.0)
            assert pa.get_recv_data() == b"phase2"
            assert not errors
        finally:
            pa.stop()
            pb.stop()

    def test_b_recv_error_returns_negative(self) -> None:
        """b_recv returns -1 on receive error when no data arrives."""
        sock_a, sock_b = _make_socket_pair()
        pa, pb = Partner(), Partner()
        try:
            _wire_partner(pa, sock_a)
            _wire_partner(pb, sock_b)
            # Close sender side so receiver gets an error
            sock_a.close()
            result = pb.b_recv()
            assert result == -1
        finally:
            pa.stop()
            pb.stop()


# ---------------------------------------------------------------------------
# Passive partner accept/listen tests
# ---------------------------------------------------------------------------


@pytest.mark.partner
class TestPassivePartner:
    """Tests for passive partner listening and accept behavior."""

    def test_accept_connection_server_socket_none(self) -> None:
        """_accept_connection returns immediately if server socket is None."""
        p = Partner(active=False)
        p._server_socket = None
        p._accept_connection()  # Should not raise


# ---------------------------------------------------------------------------
# Active partner connection error tests
# ---------------------------------------------------------------------------


@pytest.mark.partner
class TestPartnerConnectionErrors:
    """Tests for connection error paths."""

    def test_active_no_remote_ip(self) -> None:
        p = Partner(active=True)
        with pytest.raises(S7ConnectionError, match="Remote IP"):
            p.start_to("127.0.0.1", "", 0x0100, 0x0102)

    def test_active_connect_refused(self) -> None:
        p = Partner(active=True)
        port = _free_port()
        p.port = port
        with pytest.raises(S7ConnectionError):
            p.start_to("127.0.0.1", "127.0.0.1", 0x0100, 0x0102)

    def test_b_send_increments_send_errors(self) -> None:
        p = Partner()
        p.set_send_data(b"data")
        try:
            p.b_send()
        except S7ConnectionError:
            pass
        _, _, s_err, _ = p.get_stats()
        assert s_err.value == 1

    def test_b_recv_increments_recv_errors(self) -> None:
        p = Partner()
        p.b_recv()
        _, _, _, r_err = p.get_stats()
        assert r_err.value == 1


if __name__ == "__main__":
    unittest.main()
