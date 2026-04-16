"""Multi-client stress tests.

Verify that multiple clients hitting the same server simultaneously
don't cause cross-talk, data corruption, or crashes.
"""

import random
import struct
import threading
import time
from ctypes import c_char

import pytest

from snap7.client import Client
from snap7.server import Server
from snap7.type import SrvArea

STRESS_PORT = random.randint(20000, 30000)


@pytest.fixture(scope="module")
def stress_server():  # type: ignore[no-untyped-def]
    """Start a server with multiple DBs for stress testing."""
    srv = Server()
    for db_num in range(1, 6):
        data = bytearray(256)
        array = (c_char * 256).from_buffer(data)
        srv.register_area(SrvArea.DB, db_num, array)
    srv.start(tcp_port=STRESS_PORT)
    time.sleep(0.2)
    yield srv
    srv.stop()


class TestMultiClientConcurrency:
    """Multiple clients reading/writing simultaneously."""

    def test_concurrent_reads(self, stress_server: Server) -> None:
        """4 clients reading different DBs simultaneously should not interfere."""
        results: dict[int, bytearray] = {}
        errors: list[Exception] = []

        def read_db(db_num: int) -> None:
            try:
                client = Client()
                client.connect("127.0.0.1", 0, 0, STRESS_PORT)
                for _ in range(10):
                    data = client.db_read(db_num, 0, 4)
                    results[db_num] = data
                client.disconnect()
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=read_db, args=(i,)) for i in range(1, 5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        assert not errors, f"Errors during concurrent reads: {errors}"
        assert len(results) == 4

    def test_concurrent_write_read(self, stress_server: Server) -> None:
        """Writer and reader on same DB should not corrupt data."""
        errors: list[Exception] = []
        stop = threading.Event()

        def writer() -> None:
            try:
                client = Client()
                client.connect("127.0.0.1", 0, 0, STRESS_PORT)
                for i in range(20):
                    if stop.is_set():
                        break
                    client.db_write(1, 0, bytearray(struct.pack(">I", i)))
                    time.sleep(0.01)
                client.disconnect()
            except Exception as e:
                errors.append(e)

        def reader() -> None:
            try:
                client = Client()
                client.connect("127.0.0.1", 0, 0, STRESS_PORT)
                for _ in range(20):
                    if stop.is_set():
                        break
                    data = client.db_read(1, 0, 4)
                    # Value should always be a valid uint32
                    struct.unpack(">I", data)
                    time.sleep(0.01)
                client.disconnect()
            except Exception as e:
                errors.append(e)

        t_write = threading.Thread(target=writer)
        t_read = threading.Thread(target=reader)
        t_write.start()
        t_read.start()
        t_write.join(timeout=10)
        t_read.join(timeout=10)
        stop.set()

        assert not errors, f"Errors during concurrent write/read: {errors}"

    def test_many_short_connections(self, stress_server: Server) -> None:
        """Rapidly connecting and disconnecting should not leak resources."""
        errors: list[Exception] = []

        def connect_disconnect() -> None:
            try:
                for _ in range(5):
                    client = Client()
                    client.connect("127.0.0.1", 0, 0, STRESS_PORT)
                    client.db_read(1, 0, 4)
                    client.disconnect()
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=connect_disconnect) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=15)

        assert not errors, f"Errors during rapid connect/disconnect: {errors}"
