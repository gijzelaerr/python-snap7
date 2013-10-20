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
    size = 100
    data = (snap7.types.wordlen_to_ctypes[snap7.types.S7WLByte] * size)()
    server.register_area(snap7.types.srvAreaDB, 1, data)

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
