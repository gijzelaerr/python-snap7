"""Basic s7 Client example — auto-detects S7CommPlus vs legacy S7.

Usage:
    python example/s7_basic.py 192.168.1.10
"""

import sys
from s7 import Client

address = sys.argv[1] if len(sys.argv) > 1 else "192.168.1.10"

client = Client()
client.connect(address, 0, 1)

print(f"Connected via {client.protocol.value}")

# Read 4 bytes from DB1
data = client.db_read(1, 0, 4)
print(f"DB1.DBB0-3: {data.hex()}")

# Write and read back
client.db_write(1, 0, bytearray([0x01, 0x02, 0x03, 0x04]))
data = client.db_read(1, 0, 4)
print(f"After write: {data.hex()}")

client.disconnect()
