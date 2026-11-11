"""
Write several variables in one call.

``write_multi_vars`` takes a list of dicts, each with the bytes to write. The items
are written one after the other and the call raises on the first one the PLC refuses,
so earlier items stay written. Use ``write_tag`` to write a single typed value.

Usage:
    python example/write_multi.py 192.168.1.10
"""

import sys

from s7 import Client
from s7.type import Area
from s7.util import set_int, set_real


def main(address: str) -> None:
    client = Client()
    client.connect(address, 0, 1)
    try:
        int_values = [10, 20, 30, 40]
        ints = bytearray(2 * len(int_values))
        for i, value in enumerate(int_values):
            set_int(ints, 2 * i, value)

        real = bytearray(4)
        set_real(real, 0, 42.5)

        client.write_multi_vars(
            [
                {"area": Area.DB, "db_number": 1, "start": 0, "data": ints},
                {"area": Area.DB, "db_number": 1, "start": 8, "data": real},
                {"area": Area.MK, "start": 20, "data": bytearray([0x01])},
            ]
        )

        # A single typed value by address.
        client.write_tag("DB1.DBW12:INT", 1500)

        # Read everything back.
        tags = [f"DB1.DBW{2 * i}:INT" for i in range(len(int_values))] + ["DB1.DBD8:REAL", "DB1.DBW12:INT", "MB20:BYTE"]
        print(dict(zip(tags, client.read_tags(tags))))
    finally:
        client.disconnect()


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "192.168.1.10")
