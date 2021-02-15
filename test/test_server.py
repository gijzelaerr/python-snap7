import ctypes
import logging
import unittest
from unittest import mock

import snap7.error
import snap7.server
import snap7.types

logging.basicConfig(level=logging.WARNING)


class TestServer(unittest.TestCase):

    def setUp(self):
        self.server = snap7.server.Server()
        self.server.start(tcpport=1102)

    def tearDown(self):
        self.server.stop()
        self.server.destroy()

    def test_register_area(self):
        db1_type = ctypes.c_char * 1024
        self.server.register_area(snap7.types.srvAreaDB, 3, db1_type())

    def test_error(self):
        for error in snap7.error.server_errors:
            snap7.common.error_text(error, context="client")

    def test_event(self):
        event = snap7.types.SrvEvent()
        self.server.event_text(event)

    def test_get_status(self):
        server, cpu, num_clients = self.server.get_status()

    def test_get_mask(self):
        self.server.get_mask(snap7.types.mkEvent)
        self.server.get_mask(snap7.types.mkLog)
        # invalid kind
        self.assertRaises(Exception, self.server.get_mask, 3)

    def test_lock_area(self):
        from threading import Thread
        area_code = snap7.types.srvAreaDB
        index = 1
        db1_type = ctypes.c_char * 1024
        # we need to register first
        self.server.register_area(area_code, index, db1_type())
        self.server.lock_area(code=area_code, index=index)

        def second_locker():
            self.server.lock_area(code=area_code, index=index)
            self.server.unlock_area(code=area_code, index=index)

        thread = Thread(target=second_locker)
        thread.daemon = True
        thread.start()
        thread.join(timeout=1)
        self.assertTrue(thread.is_alive())
        self.server.unlock_area(code=area_code, index=index)
        thread.join(timeout=1)
        self.assertFalse(thread.is_alive())

    def test_set_cpu_status(self):
        self.server.set_cpu_status(0)
        self.server.set_cpu_status(4)
        self.server.set_cpu_status(8)
        self.assertRaises(ValueError, self.server.set_cpu_status, -1)

    def test_set_mask(self):
        self.server.set_mask(kind=snap7.types.mkEvent, mask=10)

    def test_unlock_area(self):
        area_code = snap7.types.srvAreaDB
        index = 1
        db1_type = ctypes.c_char * 1024

        # we need to register first
        self.assertRaises(Exception, self.server.lock_area, area_code, index)

        self.server.register_area(area_code, index, db1_type())
        self.server.lock_area(area_code, index)
        self.server.unlock_area(area_code, index)

    def test_unregister_area(self):
        area_code = snap7.types.srvAreaDB
        index = 1
        db1_type = ctypes.c_char * 1024
        self.server.register_area(area_code, index, db1_type())
        self.server.unregister_area(area_code, index)

    def test_events_callback(self):
        def event_call_back(event):
            logging.debug(event)

        self.server.set_events_callback(event_call_back)

    def test_read_events_callback(self):
        def read_events_call_back(event):
            logging.debug(event)

        self.server.set_read_events_callback(read_events_call_back)

    def test_pick_event(self):
        event = self.server.pick_event()
        self.assertEqual(type(event), snap7.types.SrvEvent)
        event = self.server.pick_event()
        self.assertFalse(event)

    def test_clear_events(self):
        self.server.clear_events()
        self.assertFalse(self.server.clear_events())

    def test_start_to(self):
        self.server.start_to('0.0.0.0')
        self.assertRaises(ValueError, self.server.start_to, 'bogus')

    def test_get_param(self):
        # check the defaults
        self.assertEqual(self.server.get_param(snap7.types.LocalPort), 1102)
        self.assertEqual(self.server.get_param(snap7.types.WorkInterval), 100)
        self.assertEqual(self.server.get_param(snap7.types.MaxClients), 1024)

        # invalid param for server
        self.assertRaises(Exception, self.server.get_param,
                          snap7.types.RemotePort)


class TestServerBeforeStart(unittest.TestCase):
    """
    Tests for server before it is started
    """

    def setUp(self):
        self.server = snap7.server.Server()

    def test_set_param(self):
        self.server.set_param(snap7.types.LocalPort, 1102)


class TestLibraryIntegration(unittest.TestCase):
    def setUp(self):
        # replace the function load_library with a mock
        self.loadlib_patch = mock.patch('snap7.server.load_library')
        self.loadlib_func = self.loadlib_patch.start()

        # have load_library return another mock
        self.mocklib = mock.MagicMock()
        self.loadlib_func.return_value = self.mocklib

        # have the Srv_Create of the mock return None
        self.mocklib.Srv_Create.return_value = None

    def tearDown(self):
        # restore load_library
        self.loadlib_patch.stop()

    def test_create(self):
        server = snap7.server.Server(log=False)
        self.mocklib.Srv_Create.assert_called_once()

    def test_gc(self):
        server = snap7.server.Server(log=False)
        del server
        self.mocklib.Srv_Destroy.assert_called_once()


if __name__ == '__main__':
    import logging

    logging.basicConfig()
    unittest.main()
