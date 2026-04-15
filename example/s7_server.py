"""s7 Server emulator example — run a PLC simulator for testing.

Usage:
    python example/s7_server.py
"""

import struct
import time
from ctypes import c_char

from s7 import Server
from snap7.type import SrvArea

server = Server()

# Register DB1 with test data on the legacy server
db1_data = bytearray(100)
struct.pack_into(">f", db1_data, 0, 23.5)  # temperature
struct.pack_into(">h", db1_data, 4, 42)  # set point
db1_array = (c_char * 100).from_buffer(db1_data)
server.legacy_server.register_area(SrvArea.DB, 1, db1_array)

# Register DB1 on S7CommPlus server too
server.register_raw_db(1, bytearray(db1_data))

# Start both servers
server.start(tcp_port=1102, s7commplus_port=11020)

print("Server running on port 1102 (legacy) and 11020 (S7CommPlus)")
print("Press Ctrl+C to stop")

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    server.stop()
    print("Server stopped")
