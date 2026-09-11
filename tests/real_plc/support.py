"""Protocol-neutral helpers for safe real-PLC acceptance scenarios."""

from __future__ import annotations

import math
import struct
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Protocol

from s7commplus.client import S7CommPlusClient
from snap7.client import Client
from snap7.type import Area, S7DataItem, WordLen
from snap7.util import get_bool, get_byte, get_char, get_dint, get_dword, get_int, get_real, get_word

DB_SIZE = 37
OFFSET_INT1 = 0
OFFSET_INT2 = 2
OFFSET_FLOAT1 = 4
OFFSET_FLOAT2 = 8
OFFSET_BYTE1 = 12
OFFSET_BYTE2 = 13
OFFSET_WORD1 = 14
OFFSET_WORD2 = 16
OFFSET_DWORD1 = 18
OFFSET_DWORD2 = 22
OFFSET_DINT1 = 26
OFFSET_DINT2 = 30
OFFSET_CHAR1 = 34
OFFSET_CHAR2 = 35
OFFSET_BOOLS = 36

EXPECTED_INT1 = 10
EXPECTED_INT2 = 255
EXPECTED_FLOAT1 = 123.45
EXPECTED_FLOAT2 = 543.21
EXPECTED_BYTE1 = 0x0F
EXPECTED_BYTE2 = 0xF0
EXPECTED_WORD1 = 0xABCD
EXPECTED_WORD2 = 0x1234
EXPECTED_DWORD1 = 0x12345678
EXPECTED_DWORD2 = 0x89ABCDEF
EXPECTED_DINT1 = 2147483647
EXPECTED_DINT2 = 42
EXPECTED_CHAR1 = "F"
EXPECTED_CHAR2 = "-"
EXPECTED_BOOLS = (True, False, False, False, False, False, False, False)
(
    EXPECTED_BOOL0,
    EXPECTED_BOOL1,
    EXPECTED_BOOL2,
    EXPECTED_BOOL3,
    EXPECTED_BOOL4,
    EXPECTED_BOOL5,
    EXPECTED_BOOL6,
    EXPECTED_BOOL7,
) = EXPECTED_BOOLS


@dataclass(frozen=True)
class PLCConfig:
    """Connection settings; ``host`` is deliberately never reportable."""

    host: str
    port: int
    rack: int
    slot: int
    read_db: int
    write_db: int


class PLCAdapter(Protocol):
    """Small common surface used by both Gherkin and diagnostic pytest tests."""

    protocol_name: str

    def connect(self) -> None: ...

    def disconnect(self) -> None: ...

    def is_connected(self) -> bool: ...

    def read(self, db_number: int, offset: int, size: int) -> bytes: ...

    def write(self, db_number: int, offset: int, data: bytes) -> None: ...

    def read_multi(self, db_number: int, regions: Sequence[tuple[int, int]]) -> list[bytes]: ...

    def runtime_metadata(self) -> dict[str, str | int]: ...


class LegacyS7Adapter:
    protocol_name = "legacy_s7"

    def __init__(self, config: PLCConfig) -> None:
        self.config = config
        self.client = Client()

    def connect(self) -> None:
        self.client.connect(self.config.host, self.config.rack, self.config.slot, self.config.port)

    def disconnect(self) -> None:
        self.client.disconnect()

    def is_connected(self) -> bool:
        return self.client.get_connected()

    def read(self, db_number: int, offset: int, size: int) -> bytes:
        return bytes(self.client.db_read(db_number, offset, size))

    def write(self, db_number: int, offset: int, data: bytes) -> None:
        self.client.db_write(db_number, offset, bytearray(data))

    def read_multi(self, db_number: int, regions: Sequence[tuple[int, int]]) -> list[bytes]:
        from ctypes import POINTER, c_int32, c_uint8, cast, create_string_buffer, pointer

        items = (S7DataItem * len(regions))()
        buffers = []
        for item, (offset, size) in zip(items, regions):
            item.Area = c_int32(Area.DB.value)
            item.WordLen = c_int32(WordLen.Byte.value)
            item.Result = c_int32(0)
            item.DBNumber = c_int32(db_number)
            item.Start = c_int32(offset)
            item.Amount = c_int32(size)
            buffer = create_string_buffer(size)
            buffers.append(buffer)
            item.pData = cast(pointer(buffer), POINTER(c_uint8))
        result, returned = self.client.read_multi_vars(items)
        if result != 0:
            raise RuntimeError(f"legacy multi-read failed with result {result}")
        return [bytes(item.pData[:size]) for item, (_, size) in zip(returned, regions)]

    def runtime_metadata(self) -> dict[str, str | int]:
        metadata: dict[str, str | int] = {"protocol_path": self.protocol_name}
        try:
            order_code = self.client.get_order_code()
            metadata["order_code"] = order_code.Code.rstrip(b"\x00").decode("ascii", errors="replace")
            metadata["firmware"] = f"{order_code.V1}.{order_code.V2}.{order_code.V3}"
        except Exception as error:  # noqa: BLE001 - optional metadata differs by PLC family
            metadata["order_code_status"] = f"unavailable:{type(error).__name__}"
        try:
            metadata["cpu_state"] = self.client.get_cpu_state()
        except Exception as error:  # noqa: BLE001 - optional metadata differs by PLC family
            metadata["cpu_state_status"] = f"unavailable:{type(error).__name__}"
        return metadata


class S7CommPlusAdapter:
    protocol_name = "s7commplus"

    def __init__(self, config: PLCConfig) -> None:
        self.config = config
        self.client = S7CommPlusClient()

    def connect(self) -> None:
        self.client.connect(self.config.host, self.config.port, self.config.rack, self.config.slot)

    def disconnect(self) -> None:
        self.client.disconnect()

    def is_connected(self) -> bool:
        return self.client.connected

    def read(self, db_number: int, offset: int, size: int) -> bytes:
        return self.client.db_read(db_number, offset, size)

    def write(self, db_number: int, offset: int, data: bytes) -> None:
        self.client.db_write(db_number, offset, data)

    def read_multi(self, db_number: int, regions: Sequence[tuple[int, int]]) -> list[bytes]:
        return self.client.db_read_multi([(db_number, offset, size) for offset, size in regions])

    def runtime_metadata(self) -> dict[str, str | int]:
        return {
            "protocol_path": self.protocol_name,
            "protocol_version": self.client.protocol_version,
            "security_mode": "tls" if getattr(self.client._connection, "_tls_active", False) else "plain",
        }


def make_adapter(protocol_name: str, config: PLCConfig) -> PLCAdapter:
    """Create the selected client behind the shared acceptance-test surface."""
    if protocol_name == "legacy_s7":
        return LegacyS7Adapter(config)
    if protocol_name == "s7commplus":
        return S7CommPlusAdapter(config)
    raise ValueError(f"Unsupported PLC protocol path: {protocol_name}")


def canonical_fixture_bytes() -> bytes:
    """Return the canonical 37-byte DB image documented in ``plc_setup``."""
    return b"".join(
        (
            struct.pack(
                ">hhffBBHHIIii",
                EXPECTED_INT1,
                EXPECTED_INT2,
                EXPECTED_FLOAT1,
                EXPECTED_FLOAT2,
                EXPECTED_BYTE1,
                EXPECTED_BYTE2,
                EXPECTED_WORD1,
                EXPECTED_WORD2,
                EXPECTED_DWORD1,
                EXPECTED_DWORD2,
                EXPECTED_DINT1,
                EXPECTED_DINT2,
            ),
            EXPECTED_CHAR1.encode() + EXPECTED_CHAR2.encode() + bytes([1]),
        )
    )


def assert_canonical_fixture(data: bytes) -> None:
    """Validate every documented scalar while keeping useful assertion names."""
    data = bytes(data)
    mutable = bytearray(data)
    assert len(data) == DB_SIZE
    assert get_int(mutable, OFFSET_INT1) == EXPECTED_INT1
    assert get_int(mutable, OFFSET_INT2) == EXPECTED_INT2
    assert math.isclose(get_real(mutable, OFFSET_FLOAT1), EXPECTED_FLOAT1, abs_tol=0.001)
    assert math.isclose(get_real(mutable, OFFSET_FLOAT2), EXPECTED_FLOAT2, abs_tol=0.001)
    assert get_byte(mutable, OFFSET_BYTE1) == EXPECTED_BYTE1
    assert get_byte(mutable, OFFSET_BYTE2) == EXPECTED_BYTE2
    assert get_word(mutable, OFFSET_WORD1) == EXPECTED_WORD1
    assert get_word(mutable, OFFSET_WORD2) == EXPECTED_WORD2
    assert get_dword(mutable, OFFSET_DWORD1) == EXPECTED_DWORD1
    assert get_dword(mutable, OFFSET_DWORD2) == EXPECTED_DWORD2
    assert get_dint(mutable, OFFSET_DINT1) == EXPECTED_DINT1
    assert get_dint(mutable, OFFSET_DINT2) == EXPECTED_DINT2
    assert get_char(mutable, OFFSET_CHAR1) == EXPECTED_CHAR1
    assert get_char(mutable, OFFSET_CHAR2) == EXPECTED_CHAR2
    assert tuple(get_bool(mutable, OFFSET_BOOLS, bit) for bit in range(8)) == EXPECTED_BOOLS


WRITE_VALUES: dict[str, tuple[int, bytes, Callable[[bytes], object], object]] = {
    "INT": (0, struct.pack(">h", -1234), lambda data: get_int(bytearray(data), 0), -1234),
    "REAL": (4, struct.pack(">f", 456.75), lambda data: get_real(bytearray(data), 0), 456.75),
    "BYTE": (12, b"\xa5", lambda data: get_byte(bytearray(data), 0), 0xA5),
    "WORD": (14, struct.pack(">H", 0x5AA5), lambda data: get_word(bytearray(data), 0), 0x5AA5),
    "DWORD": (18, struct.pack(">I", 0xDEADBEEF), lambda data: get_dword(bytearray(data), 0), 0xDEADBEEF),
    "DINT": (26, struct.pack(">i", -123456789), lambda data: get_dint(bytearray(data), 0), -123456789),
    "CHAR": (34, b"X", lambda data: get_char(bytearray(data), 0), "X"),
    "BOOL": (36, b"\x81", lambda data: get_bool(bytearray(data), 0, 7), True),
}


class ScratchRestoreGuard:
    """Save, restore, and verify one scratch region; restoration is idempotent."""

    def __init__(self, adapter: PLCAdapter, db_number: int, offset: int, size: int) -> None:
        self.adapter = adapter
        self.db_number = db_number
        self.offset = offset
        self.original = adapter.read(db_number, offset, size)
        self.restored = False

    def restore(self) -> None:
        if self.restored:
            return
        self.adapter.write(self.db_number, self.offset, self.original)
        restored = self.adapter.read(self.db_number, self.offset, len(self.original))
        if restored != self.original:
            raise AssertionError("scratch DB restoration verification failed")
        self.restored = True
