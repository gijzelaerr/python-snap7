"""
Read several variables in one call.

``read_tags`` takes address strings and returns decoded values. ``read_multi_vars``
takes a list of dicts and returns the raw bytes, for when you decode them yourself.
Both batch the reads into as few PDU exchanges as the PLC allows.

Usage:
    python example/read_multi.py 192.168.1.10
"""

import sys

from s7 import Client
from s7.type import Area
from s7.util import get_int, get_real


def main(address: str) -> None:
    client = Client()
    client.connect(address, 0, 1)
    try:
        # Decoded values, in the order of the request.
        level, setpoint, count = client.read_tags(["DB200.DBD16:REAL", "DB200.DBD12:REAL", "DB200.DBW2:INT"])
        print(f"level={level!r} setpoint={setpoint!r} count={count!r}")

        # Raw bytes: one bytearray per item, in the order of the request.
        items = [
            {"area": Area.DB, "db_number": 200, "start": 16, "size": 4},  # REAL
            {"area": Area.DB, "db_number": 200, "start": 12, "size": 4},  # REAL
            {"area": Area.DB, "db_number": 200, "start": 2, "size": 2},  # INT
        ]
        _, buffers = client.read_multi_vars(items)
        print([get_real(buffers[0], 0), get_real(buffers[1], 0), get_int(buffers[2], 0)])
    finally:
        client.disconnect()


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "192.168.1.10")
