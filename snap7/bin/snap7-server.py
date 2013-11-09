#!/usr/bin/env python
"""
This is an example snap7 server. It doesn't do much, but accepts
connection. Usefull for running the python-snap7 test suite.
"""
import time
import logging
import snap7
import ctypes

def mainloop():
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
                logger.info(server.event_text(event))
            else:
                break
        time.sleep(1)


def check_root():
    """
    check if uid of this process is root
    """
    import os
    if os.getuid() == 0:
        return True


root_msg = "it sucks, but you need to run this as root. The snap7 library is" \
           " hardcoded run on port 102, which requires root privileges."

if __name__ == '__main__':
    logging.basicConfig()
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    if not check_root():
        logging.error(root_msg)
    mainloop()
