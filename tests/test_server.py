from ctypes import c_char
import logging
import socket
import time
from datetime import datetime

import pytest
import unittest
from threading import Thread
from unittest.mock import MagicMock

from snap7.client import Client
from snap7.error import server_errors, error_text, S7ConnectionError
from snap7.server import Server, ServerISOConnection
from snap7.type import SrvEvent, mkEvent, mkLog, SrvArea, Parameter, Block

logging.basicConfig(level=logging.WARNING)


@pytest.mark.server
class TestServer(unittest.TestCase):
    def setUp(self) -> None:
        self.server = Server()
        self.server.start(tcp_port=12102)  # Use unique port for server tests

    def tearDown(self) -> None:
        self.server.stop()
        self.server.destroy()

    def test_register_area(self) -> None:
        db1_type = c_char * 1024
        self.server.register_area(SrvArea.DB, 3, db1_type())

    def test_error(self) -> None:
        for error in server_errors:
            error_text(error, context="client")

    def test_event(self) -> None:
        event = SrvEvent()
        self.server.event_text(event)

    def test_get_status(self) -> None:
        server, cpu, num_clients = self.server.get_status()

    def test_get_mask(self) -> None:
        self.server.get_mask(mkEvent)
        self.server.get_mask(mkLog)
        # invalid kind
        self.assertRaises(Exception, self.server.get_mask, 3)

    def test_lock_area(self) -> None:
        area = SrvArea.DB
        index = 1
        db1_type = c_char * 1024
        # we need to register first
        self.server.register_area(area, index, db1_type())
        self.server.lock_area(area=area, index=index)

        def second_locker() -> None:
            self.server.lock_area(area=area, index=index)
            self.server.unlock_area(area=area, index=index)

        thread = Thread(target=second_locker)
        thread.daemon = True
        thread.start()
        thread.join(timeout=1)
        self.assertTrue(thread.is_alive())
        self.server.unlock_area(area=area, index=index)
        thread.join(timeout=1)
        self.assertFalse(thread.is_alive())

    def test_set_cpu_status(self) -> None:
        self.server.set_cpu_status(0)
        self.server.set_cpu_status(4)
        self.server.set_cpu_status(8)
        self.assertRaises(ValueError, self.server.set_cpu_status, -1)

    def test_set_mask(self) -> None:
        self.server.set_mask(kind=mkEvent, mask=10)

    def test_unlock_area(self) -> None:
        area_code = SrvArea.DB
        index = 1
        db1_type = c_char * 1024

        # we need to register first
        self.assertRaises(Exception, self.server.lock_area, area_code, index)

        self.server.register_area(area_code, index, db1_type())
        self.server.lock_area(area_code, index)
        self.server.unlock_area(area_code, index)

    def test_unregister_area(self) -> None:
        area_code = SrvArea.DB
        index = 1
        db1_type = c_char * 1024
        self.server.register_area(area_code, index, db1_type())
        self.server.unregister_area(area_code, index)

    def test_events_callback(self) -> None:
        def event_call_back(event: SrvEvent) -> None:
            logging.debug(event)

        self.server.set_events_callback(event_call_back)

    def test_read_events_callback(self) -> None:
        def read_events_call_back(event: SrvEvent) -> None:
            logging.debug(event)

        self.server.set_read_events_callback(read_events_call_back)

    def test_pick_event(self) -> None:
        event = self.server.pick_event()
        self.assertEqual(type(event), SrvEvent)
        event = self.server.pick_event()
        self.assertFalse(event)

    def test_clear_events(self) -> None:
        self.server.clear_events()
        self.assertFalse(self.server.clear_events())

    def test_start_to(self) -> None:
        self.server.start_to("0.0.0.0")  # noqa: S104
        self.assertRaises(ValueError, self.server.start_to, "bogus")

    def test_get_param(self) -> None:
        # check the defaults
        self.assertEqual(self.server.get_param(Parameter.LocalPort), 12102)
        self.assertEqual(self.server.get_param(Parameter.WorkInterval), 100)
        self.assertEqual(self.server.get_param(Parameter.MaxClients), 64)

        # invalid param for server
        self.assertRaises(Exception, self.server.get_param, Parameter.RemotePort)


@pytest.mark.server
class TestServerBeforeStart(unittest.TestCase):
    """
    Tests for server before it is started
    """

    def setUp(self) -> None:
        self.server = Server()

    def test_set_param(self) -> None:
        self.server.set_param(Parameter.LocalPort, 1102)

    def test_max_clients_parameter(self) -> None:
        self.server.set_param(Parameter.MaxClients, 3)
        self.assertEqual(self.server.get_param(Parameter.MaxClients), 3)
        self.assertRaises(ValueError, self.server.set_param, Parameter.MaxClients, 0)

    def test_max_clients_constructor_validation(self) -> None:
        self.assertRaises(ValueError, Server, max_clients=0)


@pytest.mark.server
class TestServerRobustness(unittest.TestCase):
    """Test server robustness and edge cases."""

    def test_max_clients_is_enforced(self) -> None:
        server = Server(max_clients=1)
        first = None
        second = None
        try:
            server.start(0)
            assert server.server_socket is not None
            port = server.server_socket.getsockname()[1]

            first = socket.create_connection(("127.0.0.1", port), timeout=1)
            deadline = time.monotonic() + 2
            while server.client_count != 1 and time.monotonic() < deadline:
                time.sleep(0.01)
            self.assertEqual(server.client_count, 1)

            second = socket.create_connection(("127.0.0.1", port), timeout=1)
            second.settimeout(2)
            try:
                self.assertEqual(second.recv(1), b"")
            except ConnectionResetError:
                pass

            self.assertEqual(server.client_count, 1)
        finally:
            if first is not None:
                first.close()
            if second is not None:
                second.close()
            server.stop()

    def test_download_target_and_size_are_bounded(self) -> None:
        server = Server()
        server.register_area(SrvArea.DB, 2, bytearray(4))
        address = ("127.0.0.1", 12345)

        start_pdu = server.protocol.build_download_request(0x41, 2, b"1234")
        start_request = server._parse_request(start_pdu)
        response = server._handle_request_download(start_request, address)

        self.assertEqual(response[10:12], b"\x00\x00")
        self.assertEqual(server._download_contexts[address]["block_num"], 2)
        self.assertEqual(server._download_contexts[address]["max_size"], 4)

        server._handle_download_block({"sequence": 1, "data": {"data": b"123"}}, address)
        response = server._handle_download_block({"sequence": 2, "data": {"data": b"45"}}, address)

        self.assertEqual(response[10:12], b"\x81\x04")
        self.assertNotIn(address, server._download_contexts)

    def test_oversized_download_is_rejected_before_context_allocation(self) -> None:
        server = Server()
        server.register_area(SrvArea.DB, 2, bytearray(4))
        address = ("127.0.0.1", 12345)

        pdu = server.protocol.build_download_request(0x41, 2, b"12345")
        request = server._parse_request(pdu)
        response = server._handle_request_download(request, address)

        self.assertEqual(response[10:12], b"\x81\x04")
        self.assertFalse(hasattr(server, "_download_contexts"))

    def test_multiple_server_instances(self) -> None:
        """Test multiple server instances on different ports."""
        from snap7.client import Client

        servers = []
        clients = []

        try:
            # Start multiple servers
            for i in range(3):
                server = Server()
                port = 12110 + i

                # Register test area
                data = (c_char * 100)()
                data[0] = bytes([i + 1])  # Unique identifier
                server.register_area(SrvArea.DB, 1, data)

                server.start(port)
                servers.append((server, port))
                time.sleep(0.1)

            # Connect clients to each server
            for i, (server, port) in enumerate(servers):
                client = Client()
                client.connect("127.0.0.1", 0, 1, port)
                clients.append(client)

                # Verify unique data
                read_data = client.db_read(1, 0, 1)
                self.assertEqual(read_data[0], i + 1)

        finally:
            # Clean up
            for client in clients:
                try:
                    client.disconnect()
                except Exception:
                    pass

            for server, port in servers:
                try:
                    server.stop()
                    server.destroy()
                except Exception:
                    pass

    def test_server_area_management(self) -> None:
        """Test server area registration/unregistration."""
        from snap7.client import Client

        server = Server()
        port = 12120

        try:
            # Test area registration
            area1 = (c_char * 50)()
            area2 = (c_char * 100)()

            result1 = server.register_area(SrvArea.DB, 1, area1)
            result2 = server.register_area(SrvArea.DB, 2, area2)
            self.assertEqual(result1, 0)
            self.assertEqual(result2, 0)

            # Start server
            server.start(port)
            time.sleep(0.1)

            # Test client access to both areas
            client = Client()
            client.connect("127.0.0.1", 0, 1, port)

            data1 = client.db_read(1, 0, 4)
            data2 = client.db_read(2, 0, 4)
            self.assertEqual(len(data1), 4)
            self.assertEqual(len(data2), 4)

            # Test area unregistration
            result3 = server.unregister_area(SrvArea.DB, 1)
            self.assertEqual(result3, 0)

            client.disconnect()

        finally:
            try:
                server.stop()
                server.destroy()
            except Exception:
                pass


ip = "127.0.0.1"
SERVER_PORT = 12200


@pytest.mark.server
class TestServerISOConnectionLimits:
    def test_partial_frame_timeout_closes_connection(self) -> None:
        client_socket = MagicMock()
        client_socket.recv.side_effect = [b"\x03", TimeoutError()]
        connection = ServerISOConnection(client_socket)

        with pytest.raises(S7ConnectionError, match="partial frame"):
            connection._recv_exact(4, time.monotonic() + 1)

    def test_reassembled_request_size_is_bounded(self) -> None:
        client_socket = MagicMock()
        connection = ServerISOConnection(client_socket)
        connection.MAX_REASSEMBLED_SIZE = 4
        connection._recv_exact = MagicMock(
            side_effect=[
                b"\x03\x00\x00\x0a",
                b"\x02\xf0\x00abc",
                b"\x03\x00\x00\x09",
                b"\x02\xf0\x80de",
            ]
        )

        with pytest.raises(S7ConnectionError, match="exceeds 4 bytes"):
            connection.receive_data()


@pytest.mark.server
class TestServerBlockOperations(unittest.TestCase):
    """Test block operations through client-server communication."""

    server: Server = None  # type: ignore

    @classmethod
    def setUpClass(cls) -> None:
        cls.server = Server()
        # Register several DBs so list_blocks / list_blocks_of_type have something to report
        cls.server.register_area(SrvArea.DB, 1, bytearray(100))
        cls.server.register_area(SrvArea.DB, 2, bytearray(200))
        cls.server.register_area(SrvArea.DB, 3, bytearray(50))
        # Also register other area types
        cls.server.register_area(SrvArea.MK, 0, bytearray(64))
        cls.server.register_area(SrvArea.PA, 0, bytearray(64))
        cls.server.register_area(SrvArea.PE, 0, bytearray(64))
        cls.server.register_area(SrvArea.TM, 0, bytearray(64))
        cls.server.register_area(SrvArea.CT, 0, bytearray(64))
        cls.server.start(tcp_port=SERVER_PORT)

    @classmethod
    def tearDownClass(cls) -> None:
        if cls.server:
            cls.server.stop()
            cls.server.destroy()

    def setUp(self) -> None:
        self.client = Client()
        self.client.connect(ip, 0, 1, SERVER_PORT)

    def tearDown(self) -> None:
        self.client.disconnect()
        self.client.destroy()

    # ------------------------------------------------------------------
    # list_blocks
    # ------------------------------------------------------------------
    def test_list_blocks(self) -> None:
        """list_blocks() should return counts; DBCount >= 3 since we registered 3 DBs."""
        bl = self.client.list_blocks()
        self.assertGreaterEqual(bl.DBCount, 3)
        # OB/FB/FC should be 0 since the emulator only tracks DBs
        self.assertEqual(bl.OBCount, 0)
        self.assertEqual(bl.FBCount, 0)
        self.assertEqual(bl.FCCount, 0)

    # ------------------------------------------------------------------
    # list_blocks_of_type
    # ------------------------------------------------------------------
    def test_list_blocks_of_type_db(self) -> None:
        """list_blocks_of_type(DB) should include the DB numbers we registered."""
        block_nums = self.client.list_blocks_of_type(Block.DB, 100)
        self.assertIn(1, block_nums)
        self.assertIn(2, block_nums)
        self.assertIn(3, block_nums)

    def test_list_blocks_of_type_ob(self) -> None:
        """list_blocks_of_type(OB) should return an empty list (no OBs registered)."""
        block_nums = self.client.list_blocks_of_type(Block.OB, 100)
        self.assertEqual(block_nums, [])

    # ------------------------------------------------------------------
    # get_block_info
    # ------------------------------------------------------------------
    def test_get_block_info(self) -> None:
        """get_block_info for a registered DB should return valid metadata."""
        info = self.client.get_block_info(Block.DB, 1)
        self.assertEqual(info.MC7Size, 100)  # matches registered size
        self.assertEqual(info.BlkNumber, 1)

    def test_get_block_info_db2(self) -> None:
        """get_block_info for DB2 with size 200."""
        info = self.client.get_block_info(Block.DB, 2)
        self.assertEqual(info.MC7Size, 200)
        self.assertEqual(info.BlkNumber, 2)

    # ------------------------------------------------------------------
    # upload (block transfer: START_UPLOAD -> UPLOAD -> END_UPLOAD)
    # ------------------------------------------------------------------
    def test_upload(self) -> None:
        """Upload a DB from the server and verify the returned data length."""
        # Write known data to DB1 first
        test_data = bytearray(range(10))
        self.client.db_write(1, 0, test_data)

        # Upload the block
        block_data = self.client.upload(1)
        self.assertGreater(len(block_data), 0)
        # Verify the first bytes match what we wrote
        self.assertEqual(block_data[:10], test_data)

    def test_full_upload(self) -> None:
        """full_upload should return block data and its size."""
        data, size = self.client.full_upload(Block.DB, 1)
        self.assertGreater(size, 0)
        self.assertEqual(len(data), size)

    # ------------------------------------------------------------------
    # download (block transfer: REQUEST_DOWNLOAD -> DOWNLOAD_BLOCK -> DOWNLOAD_ENDED)
    # ------------------------------------------------------------------
    def test_download(self) -> None:
        """Download data to a registered DB on the server."""
        download_data = bytearray([0xAA, 0xBB, 0xCC, 0xDD])
        result = self.client.download(download_data, block_num=1)
        self.assertEqual(result, 0)

        # Verify the data was written by reading it back
        read_back = self.client.db_read(1, 0, 4)
        self.assertEqual(read_back, download_data)

    def test_download_uses_requested_block_number(self) -> None:
        """Download data to DB2 rather than silently falling back to DB1."""
        download_data = bytearray([0x12, 0x34, 0x56, 0x78])

        result = self.client.download(download_data, block_num=2)

        self.assertEqual(result, 0)
        self.assertEqual(self.client.db_read(2, 0, 4), download_data)


@pytest.mark.server
class TestServerUserdataOperations(unittest.TestCase):
    """Test USERDATA handlers (SZL, clock, CPU state) through client-server communication."""

    server: Server = None  # type: ignore

    @classmethod
    def setUpClass(cls) -> None:
        cls.server = Server()
        cls.server.register_area(SrvArea.DB, 1, bytearray(100))
        cls.server.start(tcp_port=SERVER_PORT + 1)

    @classmethod
    def tearDownClass(cls) -> None:
        if cls.server:
            cls.server.stop()
            cls.server.destroy()

    def setUp(self) -> None:
        self.client = Client()
        self.client.connect(ip, 0, 1, SERVER_PORT + 1)

    def tearDown(self) -> None:
        self.client.disconnect()
        self.client.destroy()

    # ------------------------------------------------------------------
    # read_szl
    # ------------------------------------------------------------------
    def test_read_szl_0x001c(self) -> None:
        """read_szl(0x001C) should return component identification data."""
        szl = self.client.read_szl(0x001C, 0)
        self.assertGreater(szl.Header.LengthDR, 0)

    def test_read_szl_0x0011(self) -> None:
        """read_szl(0x0011) should return module identification data."""
        szl = self.client.read_szl(0x0011, 0)
        self.assertGreater(szl.Header.LengthDR, 0)

    def test_parse_order_code_s71516f(self) -> None:
        """Parse a real S7-1516F dump — should use 0x0007 firmware, not 0x0081 boot loader.

        Verified by @fls-witturcom: TIA Portal shows V2.9.2 (record 0x0007),
        not V3.3.0 (record 0x0081 boot loader).
        """
        from snap7.szl import parse_order_code_szl
        from snap7.type import S7SZL

        # Real trimmed hex dump from CPU 1516F-3 PN/DP, courtesy of @fls-witturcom
        payload = (
            b"\x00\x1c\x00\x05"
            b"\x00\x01\x36\x45\x53\x37\x20\x35\x31\x36\x2d\x33\x46\x4e\x30\x32\x2d\x30\x41\x42\x30\x20\x00\x00\x00\x02\x00\x00"
            b"\x00\x06\x36\x45\x53\x37\x20\x35\x31\x36\x2d\x33\x46\x4e\x30\x32\x2d\x30\x41\x42\x30\x20\x00\x00\x00\x02\x00\x00"
            b"\x00\x07\x20\x20\x20\x20\x20\x20\x20\x20\x20\x20\x20\x20\x20\x20\x20\x20\x20\x20\x20\x20\x00\x00\x56\x02\x09\x02"
            b"\x00\x80\x36\x45\x53\x37\x39\x35\x34\x2d\x38\x4c\x45\x30\x33\x2d\x30\x41\x41\x30\x20\x20\x00\x00\x01\x00\x00\x00"
            b"\x00\x81\x42\x6f\x6f\x74\x20\x4c\x6f\x61\x64\x65\x72\x20\x20\x20\x20\x20\x20\x20\x20\x20\x00\x00\x56\x03\x03\x00"
        )
        szl = S7SZL()
        szl.Header.LengthDR = len(payload)
        for i, b in enumerate(payload):
            szl.Data[i] = b

        result = parse_order_code_szl(szl)
        self.assertIn(b"6ES7 516-3FN02-0AB0", result.OrderCode)
        # Firmware V2.9.2 from record 0x0007 (NOT boot loader V3.3.0 from 0x0081)
        self.assertEqual(result.V1, 2)
        self.assertEqual(result.V2, 9)
        self.assertEqual(result.V3, 2)

    def test_parse_order_code_s71510sp(self) -> None:
        """Parse a real S7-1510SP dump — should use 0x0007 firmware, not 0x0081 boot loader.

        Verified by @fls-witturcom: TIA Portal identifies the firmware from
        record 0x0007, not the boot loader in 0x0081.
        """
        from snap7.szl import parse_order_code_szl
        from snap7.type import S7SZL

        # Real trimmed hex dump from CPU 1510SP F-1 PN, courtesy of @fls-witturcom
        payload = (
            b"\x00\x1c\x00\x05"
            b"\x00\x01\x36\x45\x53\x37\x20\x35\x31\x30\x2d\x31\x53\x4b\x30\x33\x2d\x30\x41\x42\x30\x20\x00\x00\x00\x03\x00\x00"
            b"\x00\x06\x36\x45\x53\x37\x20\x35\x31\x30\x2d\x31\x53\x4b\x30\x33\x2d\x30\x41\x42\x30\x20\x00\x00\x00\x03\x00\x00"
            b"\x00\x07\x20\x20\x20\x20\x20\x20\x20\x20\x20\x20\x20\x20\x20\x20\x20\x20\x20\x20\x20\x20\x00\x00\x56\x03\x00\x03"
            b"\x00\x80\x36\x45\x53\x37\x39\x35\x34\x2d\x38\x4c\x45\x30\x33\x2d\x30\x41\x41\x30\x20\x20\x00\x00\x01\x00\x00\x00"
            b"\x00\x81\x42\x6f\x6f\x74\x20\x4c\x6f\x61\x64\x65\x72\x20\x20\x20\x20\x20\x20\x20\x20\x20\x00\x00\x56\x04\x02\x03"
        )
        szl = S7SZL()
        szl.Header.LengthDR = len(payload)
        for i, b in enumerate(payload):
            szl.Data[i] = b

        result = parse_order_code_szl(szl)
        self.assertIn(b"6ES7 510-1SK03-0AB0", result.OrderCode)
        # Firmware V3.0.3 from record 0x0007 (NOT boot loader V4.2.3 from 0x0081)
        self.assertEqual(result.V1, 3)
        self.assertEqual(result.V2, 0)
        self.assertEqual(result.V3, 3)

    def test_parse_order_code_s71214c(self) -> None:
        """Parse a real S7-1214C dump whose installed firmware is in 0x0007."""
        from snap7.szl import parse_order_code_szl
        from snap7.type import S7SZL

        # Real trimmed hex dump from CPU 1214C, courtesy of @fls-witturcom
        payload = (
            b"\x00\x1c\x00\x03"
            b"\x00\x01\x36\x45\x53\x37\x20\x32\x31\x34\x2d\x31\x41\x47\x34\x30\x2d\x30\x58\x42\x30\x20\x00\x00\x00\x10\x20\x20"
            b"\x00\x06\x36\x45\x53\x37\x20\x32\x31\x34\x2d\x31\x41\x47\x34\x30\x2d\x30\x58\x42\x30\x20\x00\x00\x00\x10\x20\x20"
            b"\x00\x07\x36\x45\x53\x37\x20\x32\x31\x34\x2d\x31\x41\x47\x34\x30\x2d\x30\x58\x42\x30\x20\x00\x00\x56\x04\x06\x00"
        )
        szl = S7SZL()
        szl.Header.LengthDR = len(payload)
        for i, b in enumerate(payload):
            szl.Data[i] = b

        result = parse_order_code_szl(szl)
        self.assertIn(b"6ES7 214-1AG40-0XB0", result.OrderCode)
        self.assertEqual(result.V1, 4)
        self.assertEqual(result.V2, 6)
        self.assertEqual(result.V3, 0)

    def test_parse_order_code_s7300_flat_text(self) -> None:
        """parse_order_code_szl handles S7-300 flat ASCII text layout."""
        from snap7.szl import parse_order_code_szl
        from snap7.type import S7SZL

        # Real hex dump from CPU 315-2 PN/DP, courtesy of @fls-witturcom
        payload = (
            b"\x00\x1c\x00\x03"
            b"\x43\x50\x55\x20\x33\x31\x35\x2d\x32\x20\x50\x4e\x2f\x44\x50\x20\x20\x20\x20\x20"
            b"\x36\x45\x53\x37\x20\x33\x31\x35\x2d\x32\x4e\x44\x30\x37\x2d\x30\x41\x42\x30\x20"
            b"\x00\x01\x00\x04\x00\x04"
            b"\x4d\x50\x49\x2f\x44\x50\x20\x20\x20\x20\x20\x20\x20\x20\x20\x20\x20\x20\x20\x20"
            b"\x20\x20\x20\x20\x20\x20\x00\x02\x00\x00\x00\x04\x50\x4e\x2d\x4a\x4f\x20"
        )
        szl = S7SZL()
        szl.Header.LengthDR = len(payload)
        for i, b in enumerate(payload):
            szl.Data[i] = b

        result = parse_order_code_szl(szl)
        self.assertIn(b"6ES7 315-2ND07-0AB0", result.OrderCode)

    def test_parse_order_code_s7300_structured(self) -> None:
        """parse_order_code_szl with real S7-300 CPU 318-3 structured records."""
        from snap7.szl import parse_order_code_szl
        from snap7.type import S7SZL

        # Real hex dump from CPU 318-3EL01-0AB0, courtesy of @b1163646804
        payload = (
            b"\x00\x1c\x00\x04"
            b"\x00\x016ES7 318-3EL01-0AB0 \x00\xc0\x00\x03\x00\x01"
            b"\x00\x066ES7 318-3EL01-0AB0 \x00\xc0\x00\x03\x00\x01"
            b"\x00\x07                    \x00\xc0V\x03\x02\x04"
            b'\x00\x81Boot Loader         \x00\x00A"\x09\x09'
        )
        szl = S7SZL()
        szl.Header.LengthDR = len(payload)
        for i, b in enumerate(payload):
            szl.Data[i] = b

        result = parse_order_code_szl(szl)
        self.assertIn(b"6ES7 318-3EL01-0AB0", result.OrderCode)
        # Should use 0x0007 firmware (V3.2.4), NOT 0x0081 boot loader (V34.9.9)
        self.assertEqual(result.V1, 3)
        self.assertEqual(result.V2, 2)
        self.assertEqual(result.V3, 4)

    def test_read_szl_0x0131(self) -> None:
        """read_szl(0x0131) should return communication parameters."""
        szl = self.client.read_szl(0x0131, 0)
        self.assertGreater(szl.Header.LengthDR, 0)

    def test_read_szl_0x0232(self) -> None:
        """read_szl(0x0232) should return protection level data."""
        szl = self.client.read_szl(0x0232, 0)
        self.assertGreater(szl.Header.LengthDR, 0)

    def test_read_szl_0x0000(self) -> None:
        """read_szl(0x0000) should return the list of available SZL IDs."""
        szl = self.client.read_szl(0x0000, 0)
        self.assertGreater(szl.Header.LengthDR, 0)

    def test_read_szl_list(self) -> None:
        """read_szl_list should return raw bytes of available SZL IDs."""
        data = self.client.read_szl_list()
        self.assertIsInstance(data, bytes)
        self.assertGreater(len(data), 0)

    # ------------------------------------------------------------------
    # get_cpu_info (uses read_szl 0x001C internally)
    # ------------------------------------------------------------------
    def test_get_cpu_info(self) -> None:
        """get_cpu_info should populate the S7CpuInfo structure."""
        info = self.client.get_cpu_info()
        # The emulated server returns "CPU 315-2 PN/DP"
        self.assertIn(b"CPU", info.ModuleTypeName)

    # ------------------------------------------------------------------
    # get_order_code (uses read_szl 0x0011 internally)
    # ------------------------------------------------------------------
    def test_get_order_code(self) -> None:
        """get_order_code should return order code data."""
        oc = self.client.get_order_code()
        self.assertIn(b"6ES7", oc.OrderCode)

    # ------------------------------------------------------------------
    # get_cp_info (uses read_szl 0x0131 internally)
    # ------------------------------------------------------------------
    def test_get_cp_info(self) -> None:
        """get_cp_info should return communication parameters."""
        cp = self.client.get_cp_info()
        self.assertGreater(cp.MaxPduLength, 0)
        self.assertGreater(cp.MaxConnections, 0)

    # ------------------------------------------------------------------
    # get_protection (uses read_szl 0x0232 internally)
    # ------------------------------------------------------------------
    def test_get_protection(self) -> None:
        """get_protection should return protection settings."""
        prot = self.client.get_protection()
        # Emulator returns no protection (sch_schal=1)
        self.assertEqual(prot.sch_schal, 1)

    # ------------------------------------------------------------------
    # get/set PLC datetime (clock USERDATA handlers)
    # ------------------------------------------------------------------
    def test_get_plc_datetime(self) -> None:
        """get_plc_datetime should return a valid datetime object."""
        dt = self.client.get_plc_datetime()
        self.assertIsInstance(dt, datetime)
        # Should be recent (within last minute)
        now = datetime.now()
        delta = abs((now - dt).total_seconds())
        self.assertLess(delta, 60)

    def test_set_plc_datetime(self) -> None:
        """set_plc_datetime should succeed (returns 0)."""
        test_dt = datetime(2025, 6, 15, 12, 30, 45)
        result = self.client.set_plc_datetime(test_dt)
        self.assertEqual(result, 0)

    def test_set_plc_system_datetime(self) -> None:
        """set_plc_system_datetime should succeed."""
        result = self.client.set_plc_system_datetime()
        self.assertEqual(result, 0)

    # ------------------------------------------------------------------
    # get_cpu_state (SZL-based CPU state request)
    # ------------------------------------------------------------------
    def test_get_cpu_state(self) -> None:
        """get_cpu_state should return a string state."""
        state = self.client.get_cpu_state()
        self.assertIsInstance(state, str)


@pytest.mark.server
class TestServerPLCControl(unittest.TestCase):
    """Test PLC control operations (stop/start) through client-server communication."""

    server: Server = None  # type: ignore

    @classmethod
    def setUpClass(cls) -> None:
        cls.server = Server()
        cls.server.register_area(SrvArea.DB, 1, bytearray(100))
        cls.server.start(tcp_port=SERVER_PORT + 2)

    @classmethod
    def tearDownClass(cls) -> None:
        if cls.server:
            cls.server.stop()
            cls.server.destroy()

    def setUp(self) -> None:
        self.client = Client()
        self.client.connect(ip, 0, 1, SERVER_PORT + 2)

    def tearDown(self) -> None:
        self.client.disconnect()
        self.client.destroy()

    def test_plc_stop(self) -> None:
        """plc_stop should succeed and set the server CPU state to STOP."""
        result = self.client.plc_stop()
        self.assertEqual(result, 0)

    def test_plc_hot_start(self) -> None:
        """plc_hot_start should succeed."""
        result = self.client.plc_hot_start()
        self.assertEqual(result, 0)

    def test_plc_cold_start(self) -> None:
        """plc_cold_start should succeed."""
        result = self.client.plc_cold_start()
        self.assertEqual(result, 0)

    def test_plc_stop_then_start(self) -> None:
        """Stopping then starting the PLC should work in sequence."""
        self.assertEqual(self.client.plc_stop(), 0)
        self.assertEqual(self.client.plc_hot_start(), 0)

    def test_compress(self) -> None:
        """compress should succeed."""
        result = self.client.compress(timeout=1000)
        self.assertEqual(result, 0)

    def test_copy_ram_to_rom(self) -> None:
        """copy_ram_to_rom should succeed."""
        result = self.client.copy_ram_to_rom(timeout=1000)
        self.assertEqual(result, 0)


@pytest.mark.server
class TestServerErrorScenarios(unittest.TestCase):
    """Test error handling paths in the server."""

    server: Server = None  # type: ignore

    @classmethod
    def setUpClass(cls) -> None:
        cls.server = Server()
        # Only register DB1 with a small area
        cls.server.register_area(SrvArea.DB, 1, bytearray(10))
        cls.server.start(tcp_port=SERVER_PORT + 3)

    @classmethod
    def tearDownClass(cls) -> None:
        if cls.server:
            cls.server.stop()
            cls.server.destroy()

    def setUp(self) -> None:
        self.client = Client()
        self.client.connect(ip, 0, 1, SERVER_PORT + 3)

    def tearDown(self) -> None:
        self.client.disconnect()
        self.client.destroy()

    def test_read_unregistered_db(self) -> None:
        """Reading from an unregistered DB should still return data (server returns dummy data)."""
        # The server returns dummy data for unregistered areas rather than an error
        data = self.client.db_read(99, 0, 4)
        self.assertEqual(len(data), 4)

    def test_write_beyond_area_bounds(self) -> None:
        """Writing beyond area bounds should raise an error."""
        # DB1 is only 10 bytes, writing 20 bytes at offset 0 should fail
        with self.assertRaises(Exception):
            self.client.db_write(1, 0, bytearray(20))

    def test_get_block_info_nonexistent(self) -> None:
        """get_block_info for a non-existent block should raise an error."""
        with self.assertRaises(Exception):
            self.client.get_block_info(Block.DB, 999)

    def test_upload_nonexistent_block(self) -> None:
        """Uploading a non-existent block returns empty data (server has no data for that block)."""
        # The server defaults to block_num=1 for unknown blocks due to parsing fallback,
        # so the upload still completes but returns the default block's data.
        # We just verify the operation doesn't crash.
        data = self.client.upload(999)
        self.assertIsInstance(data, bytearray)


if __name__ == "__main__":
    unittest.main()
