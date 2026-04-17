"""Tag-based symbolic addressing example.

Usage:
    python example/s7_symbols.py 192.168.1.10
"""

import sys

from s7 import Client, Tag

address = sys.argv[1] if len(sys.argv) > 1 else "192.168.1.10"

client = Client()
client.connect(address, 0, 1)

# Ad-hoc tag read using PLC4X-style syntax
speed = client.read_tag("DB1.DBD0:REAL")
running = client.read_tag("DB1.DBX4.0:BOOL")
print(f"Speed: {speed!r}, Running: {running!r}")

# Write a value
client.write_tag("DB1.DBW6:INT", 1500)

# Read multiple tags in one optimized request
values = client.read_tags(["DB1.DBD0:REAL", "DB1.DBW6:INT"])
print(f"Batch: {values!r}")

# Or build tags programmatically / load from file
# tags = load_csv("tags.csv")  # returns dict[str, Tag]
# value = client.read_tag(tags["Motor.Speed"])

# Tag instances are also accepted directly
temperature_tag = Tag.from_string("DB1.DBD0:REAL", name="Temperature")
temp = client.read_tag(temperature_tag)
print(f"Temperature: {temp!r}")

client.disconnect()
