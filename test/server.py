import unittest2
import logging
import snap7
import ctypes


logging.basicConfig()
l = logging.getLogger()
l.setLevel(logging.INFO)


class Server(unittest2.TestCase):
    def setUp(self):
        self.server = snap7.server.Server()
        self.server.start()

    def tearDown(self):
        self.server.stop()
        self.server.destroy()

    def test_register_area(self):
        db1_type = ctypes.c_char * 1024
        self.server.register_area(snap7.server.srvAreaDB, 3, db1_type())

    def test_error(self):
        self.server.error_text()

    def test_callback(self):
        def event_call_back(event):
            print event
        self.server.set_events_callback(event_call_back)

    def test_error(self):
        for error in snap7.error.server_errors:
            snap7.server.error_text(error)



if __name__ == '__main__':
    unittest2.main()
