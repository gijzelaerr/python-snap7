"""Symbolic addressing example — read/write by tag name.

Usage:
    python example/s7_symbols.py 192.168.1.10
"""

import sys
from s7 import Client, SymbolTable

address = sys.argv[1] if len(sys.argv) > 1 else "192.168.1.10"

# Define symbols (or use SymbolTable.from_csv("tags.csv"))
symbols = SymbolTable(
    {
        "Motor1.Speed": {"db": 1, "offset": 0, "type": "REAL"},
        "Motor1.Running": {"db": 1, "offset": 4, "bit": 0, "type": "BOOL"},
        "SetPoint": {"db": 1, "offset": 6, "type": "INT"},
    }
)

client = Client()
client.connect(address, 0, 1)

# Read by name
speed = symbols.read(client, "Motor1.Speed")
running = symbols.read(client, "Motor1.Running")
print(f"Speed: {speed!r}, Running: {running!r}")

# Write by name
symbols.write(client, "SetPoint", 1500)

# Batch read (uses optimizer when available)
values = symbols.read_many(client, ["Motor1.Speed", "SetPoint"])
print(f"Batch: {values}")

client.disconnect()
