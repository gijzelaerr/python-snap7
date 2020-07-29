#!/usr/bin/env python
"""
This is an example snap7 server. It doesn't do much, but accepts
connection. Useful for running the python-snap7 test suite.
"""
import logging
import sys

import snap7
from snap7.server import mainloop

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

tcpport = 1102

if __name__ == '__main__':
    if len(sys.argv) > 1:
        snap7.common.load_library(sys.argv[1])
    mainloop(tcpport)
