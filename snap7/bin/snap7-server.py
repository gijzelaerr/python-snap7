#!/usr/bin/env python

import time
import logging
import snap7
import ctypes

logging.basicConfig()
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def server():
    server = snap7.server.Server()
    data = (ctypes.c_int * 10)()
    server.register_area(snap7.server.srvAreaDB, 1, data)

    server.start()
    while True:
        #logger.info("server: %s cpu: %s users: %s" % server.get_status())
        while True:
            event = server.pick_event()
            if event:
                logger.info(snap7.server.event_text(event))
            else:
                break
        time.sleep(1)

if __name__ == '__main__':
    server()
