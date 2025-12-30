from ctypes import c_char
import logging
import time

import pytest
import unittest
from threading import Thread

from snap7.error import server_errors, error_text
from snap7.server import Server
from snap7.type import SrvEvent, mkEvent, mkLog, SrvArea, Parameter

logging.basicConfig(level=logging.WARNING)


@pytest.mark.server
class TestServer(unittest.TestCase):
    def setUp(self) -> None:
        self.server = Server()
        self.server.start(tcp_port=12102)  # Use unique port for server tests

    def tearDown(self) -> None:
        self.server.stop()
        self.server.destroy()
        time.sleep(0.2)  # Give OS time to release the port

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
        self.assertEqual(self.server.get_param(Parameter.MaxClients), 1024)

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


@pytest.mark.server
class TestServerRobustness(unittest.TestCase):
    """Test server robustness and edge cases."""

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


if __name__ == "__main__":
    import logging

    logging.basicConfig()
    unittest.main()
