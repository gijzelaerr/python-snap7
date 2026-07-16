"""Basic S7CommPlus client example for S7-1200/1500 PLCs.

Usage:
    python example/s7commplus_basic.py 192.168.1.10
"""

import sys
from s7commplus import Client

address = sys.argv[1] if len(sys.argv) > 1 else "192.168.1.10"

client = Client()
client.connect(address, 0, 1)

# Read 4 bytes from DB1
data = client.db_read(1, 0, 4)
print(f"DB1.DBB0-3: {data.hex()}")

# Write and read back
client.db_write(1, 0, b"\x01\x02\x03\x04")
data = client.db_read(1, 0, 4)
print(f"After write: {data.hex()}")

client.disconnect()
