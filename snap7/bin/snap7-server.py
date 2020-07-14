#!/usr/bin/env python
"""
This is an example snap7 server. It doesn't do much, but accepts
connection. Useful for running the python-snap7 test suite.
"""
import time
import logging
from ..snap7types import wordlen_to_ctypes, srvAreaDB, srvAreaPA, srvAreaTM, srvAreaCT
from ..common import load_library
import snap7
import sys

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

tcpport = 1102


def mainloop():
    server = snap7.server.Server()
    size = 100
    DBdata = (wordlen_to_ctypes[snap7.snap7types.S7WLByte] * size)()
    PAdata = (wordlen_to_ctypes[snap7.snap7types.S7WLByte] * size)()
    TMdata = (wordlen_to_ctypes[snap7.snap7types.S7WLByte] * size)()
    CTdata = (wordlen_to_ctypes[snap7.snap7types.S7WLByte] * size)()
    server.register_area(srvAreaDB, 1, DBdata)
    server.register_area(srvAreaPA, 1, PAdata)
    server.register_area(srvAreaTM, 1, TMdata)
    server.register_area(srvAreaCT, 1, CTdata)
    server.start(tcpport=tcpport)
    while True:
        while True:
            event = server.pick_event()
            if event:
                logger.info(server.event_text(event))
            else:
                break
        time.sleep(1)


if __name__ == '__main__':
    if len(sys.argv) > 1:
        load_library(sys.argv[1])
    mainloop()
