"""S7CommPlus server emulator example for testing.

Usage:
    python example/s7commplus_server.py
"""

import struct
import time

from s7commplus import Server

server = Server()

# Register DB1 with test data
db1_data = bytearray(100)
struct.pack_into(">f", db1_data, 0, 23.5)  # temperature
struct.pack_into(">h", db1_data, 4, 42)  # set point
server.register_raw_db(1, db1_data)

server.start(port=11020)
print("S7CommPlus server running on port 11020")
print("Press Ctrl+C to stop")

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    server.stop()
    print("Server stopped")
