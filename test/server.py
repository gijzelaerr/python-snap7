import unittest2

from snap7.server import create, register_area, set_events_callback, start,\
    error_text, stop, destroy, srvAreaDB


class Server(unittest2.TestCase):
    def test_create(self):
        server = create()

        import ctypes

        db1_type = ctypes.c_char * 512
        db2_type = ctypes.c_char * 128
        db3_type = ctypes.c_char * 1024

        db1 = db1_type()
        db2 = db2_type()
        db3 = db3_type()

        register_area(server, srvAreaDB, 1, db1)
        register_area(server, srvAreaDB, 2, db2)
        register_area(server, srvAreaDB, 3, db3)

        def event_call_back(event):
            print event

        set_events_callback(server, event_call_back)

        error = start(server)
        if error:
            print(error_text(error))

        stop(server)
        destroy(server)


if __name__ == '__main__':
    unittest2.main()
