from ctypes import c_char
import gc
import logging

import pytest
import unittest
from threading import Thread
from unittest import mock

from snap7.error import server_errors, error_text
from snap7.server import Server
from snap7.type import SrvEvent, mkEvent, mkLog, SrvArea, Parameter

logging.basicConfig(level=logging.WARNING)


@pytest.mark.server
class TestServer(unittest.TestCase):
    def setUp(self) -> None:
        self.server = Server()
        self.server.start(tcp_port=1102)

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
        def event_call_back(event: str) -> None:
            logging.debug(event)

        self.server.set_events_callback(event_call_back)

    def test_read_events_callback(self) -> None:
        def read_events_call_back(event: str) -> None:
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
        self.assertEqual(self.server.get_param(Parameter.LocalPort), 1102)
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
class TestLibraryIntegration(unittest.TestCase):
    def setUp(self) -> None:
        # replace the function load_library with a mock
        self.loadlib_patch = mock.patch("snap7.server.load_library")
        self.loadlib_func = self.loadlib_patch.start()

        # have load_library return another mock
        self.mocklib = mock.MagicMock()
        self.loadlib_func.return_value = self.mocklib

        # have the Srv_Create of the mock return None
        self.mocklib.Srv_Create.return_value = None
        self.mocklib.Srv_Destroy.return_value = None

    def tearDown(self) -> None:
        # restore load_library
        self.loadlib_patch.stop()

    def test_create(self) -> None:
        server = Server(log=False)
        del server
        gc.collect()
        self.mocklib.Srv_Create.assert_called_once()

    def test_context_manager(self) -> None:
        with Server(log=False) as _:
            pass


if __name__ == "__main__":
    import logging

    logging.basicConfig()
    unittest.main()
