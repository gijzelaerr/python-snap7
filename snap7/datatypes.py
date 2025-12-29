"""
S7 data types and conversion utilities.

Handles S7-specific data types, endianness conversion, and address encoding.
"""

import struct
from enum import IntEnum
from typing import Tuple


class S7Area(IntEnum):
    """S7 memory area identifiers."""

    PE = 0x81  # Process Input (Peripheral Input)
    PA = 0x82  # Process Output (Peripheral Output)
    MK = 0x83  # Memory/Merkers (Flags)
    DB = 0x84  # Data Blocks
    CT = 0x1C  # Counters
    TM = 0x1D  # Timers


class S7WordLen(IntEnum):
    """S7 data word length identifiers."""

    BIT = 0x01  # Single bit
    BYTE = 0x02  # 8-bit byte
    CHAR = 0x03  # 8-bit character
    WORD = 0x04  # 16-bit word
    INT = 0x05  # 16-bit signed integer
    DWORD = 0x06  # 32-bit double word
    DINT = 0x07  # 32-bit signed integer
    REAL = 0x08  # 32-bit IEEE float
    COUNTER = 0x1C  # Counter value
    TIMER = 0x1D  # Timer value


class S7DataTypes:
    """S7 data type conversion utilities."""

    # Word length to byte size mapping
    WORD_LEN_SIZE = {
        S7WordLen.BIT: 1,  # Bit operations use 1 byte
        S7WordLen.BYTE: 1,  # 1 byte
        S7WordLen.CHAR: 1,  # 1 byte
        S7WordLen.WORD: 2,  # 2 bytes
        S7WordLen.INT: 2,  # 2 bytes
        S7WordLen.DWORD: 4,  # 4 bytes
        S7WordLen.DINT: 4,  # 4 bytes
        S7WordLen.REAL: 4,  # 4 bytes
        S7WordLen.COUNTER: 2,  # 2 bytes
        S7WordLen.TIMER: 2,  # 2 bytes
    }

    @staticmethod
    def get_size_bytes(word_len: S7WordLen, count: int = 1) -> int:
        """Get total size in bytes for given word length and count."""
        return S7DataTypes.WORD_LEN_SIZE[word_len] * count

    @staticmethod
    def encode_address(area: S7Area, db_number: int, start: int, word_len: S7WordLen, count: int) -> bytes:
        """
        Encode S7 address into parameter format.

        Returns 12-byte parameter section for read/write operations.
        """
        # Parameter format for read/write operations
        # Byte 0: Specification type (0x12 for address specification)
        # Byte 1: Length of following address specification (0x0A = 10 bytes)
        # Byte 2: Syntax ID (0x10 = S7-Any)
        # Byte 3: Transport size (word length)
        # Bytes 4-5: Count (number of items)
        # Bytes 6-7: DB number (for DB area) or 0
        # Bytes 8: Area code
        # Bytes 9-11: Start address (byte.bit format)

        # Convert start address to byte.bit format
        if word_len == S7WordLen.BIT:
            # For bit access: byte address + bit offset
            byte_addr = start // 8
            bit_addr = start % 8
            address = (byte_addr << 3) | bit_addr
        else:
            # For word access: convert to bit address
            address = start * 8

        address_bytes = struct.pack(">I", address)[1:]  # 3-byte address (big-endian)

        return struct.pack(
            ">BBBBHHB3s",
            0x12,  # Specification type
            0x0A,  # Length of address spec
            0x10,  # Syntax ID (S7-Any)
            word_len,  # Transport size
            count,  # Count
            db_number if area == S7Area.DB else 0,  # DB number
            area,  # Area code
            address_bytes,  # 3-byte address (big-endian)
        )

    @staticmethod
    def decode_s7_data(data: bytes, word_len: S7WordLen, count: int) -> list:
        """
        Decode S7 data from bytes to Python values.

        Handles Siemens big-endian byte order.
        """
        values = []
        offset = 0

        for i in range(count):
            if word_len == S7WordLen.BIT:
                # Extract single bit
                byte_val = data[offset]
                values.append(bool(byte_val))
                offset += 1

            elif word_len in [S7WordLen.BYTE, S7WordLen.CHAR]:
                # 8-bit values
                values.append(data[offset])
                offset += 1

            elif word_len in [S7WordLen.WORD, S7WordLen.COUNTER, S7WordLen.TIMER]:
                # 16-bit unsigned values (big-endian)
                value = struct.unpack(">H", data[offset : offset + 2])[0]
                values.append(value)
                offset += 2

            elif word_len == S7WordLen.INT:
                # 16-bit signed values (big-endian)
                value = struct.unpack(">h", data[offset : offset + 2])[0]
                values.append(value)
                offset += 2

            elif word_len == S7WordLen.DWORD:
                # 32-bit unsigned values (big-endian)
                value = struct.unpack(">I", data[offset : offset + 4])[0]
                values.append(value)
                offset += 4

            elif word_len == S7WordLen.DINT:
                # 32-bit signed values (big-endian)
                value = struct.unpack(">i", data[offset : offset + 4])[0]
                values.append(value)
                offset += 4

            elif word_len == S7WordLen.REAL:
                # 32-bit IEEE float (big-endian)
                value = struct.unpack(">f", data[offset : offset + 4])[0]
                values.append(value)
                offset += 4

        return values

    @staticmethod
    def encode_s7_data(values: list, word_len: S7WordLen) -> bytes:
        """
        Encode Python values to S7 data bytes.

        Handles Siemens big-endian byte order.
        """
        data = bytearray()

        for value in values:
            if word_len == S7WordLen.BIT:
                # Single bit to byte
                data.append(0x01 if value else 0x00)

            elif word_len in [S7WordLen.BYTE, S7WordLen.CHAR]:
                # 8-bit values
                data.append(int(value) & 0xFF)

            elif word_len in [S7WordLen.WORD, S7WordLen.COUNTER, S7WordLen.TIMER]:
                # 16-bit unsigned values (big-endian)
                data.extend(struct.pack(">H", int(value) & 0xFFFF))

            elif word_len == S7WordLen.INT:
                # 16-bit signed values (big-endian)
                data.extend(struct.pack(">h", int(value)))

            elif word_len == S7WordLen.DWORD:
                # 32-bit unsigned values (big-endian)
                data.extend(struct.pack(">I", int(value) & 0xFFFFFFFF))

            elif word_len == S7WordLen.DINT:
                # 32-bit signed values (big-endian)
                data.extend(struct.pack(">i", int(value)))

            elif word_len == S7WordLen.REAL:
                # 32-bit IEEE float (big-endian)
                data.extend(struct.pack(">f", float(value)))

        return bytes(data)

    @staticmethod
    def parse_address(address_str: str) -> Tuple[S7Area, int, int]:
        """
        Parse S7 address string to area, DB number, and offset.

        Examples:
        - "DB1.DBX0.0" -> (DB, 1, 0)
        - "M10.5" -> (MK, 0, 85)  # bit 5 of byte 10 = bit 85
        - "IW20" -> (PE, 0, 20)
        """
        address_str = address_str.upper().strip()

        # Data Block addresses: DB1.DBX0.0, DB1.DBW10, etc.
        if address_str.startswith("DB"):
            db_part, addr_part = address_str.split(".", 1)
            db_number = int(db_part[2:])

            if addr_part.startswith("DBX"):
                # Bit address: DBX10.5
                if "." in addr_part:
                    byte_addr, bit_addr = addr_part[3:].split(".")
                    offset = int(byte_addr) * 8 + int(bit_addr)
                else:
                    offset = int(addr_part[3:]) * 8
            elif addr_part.startswith("DBB"):
                # Byte address: DBB10
                offset = int(addr_part[3:])
            elif addr_part.startswith("DBW"):
                # Word address: DBW10
                offset = int(addr_part[3:])
            elif addr_part.startswith("DBD"):
                # Double word address: DBD10
                offset = int(addr_part[3:])
            else:
                raise ValueError(f"Invalid DB address format: {address_str}")

            return S7Area.DB, db_number, offset

        # Memory/Flag addresses: M10.5, MW20, etc.
        elif address_str.startswith("M"):
            if "." in address_str:
                # Bit address: M10.5
                byte_addr, bit_addr = address_str[1:].split(".")
                offset = int(byte_addr) * 8 + int(bit_addr)
            elif address_str.startswith("MW"):
                # Word address: MW20
                offset = int(address_str[2:])
            elif address_str.startswith("MD"):
                # Double word address: MD20
                offset = int(address_str[2:])
            else:
                # Byte address: M10
                offset = int(address_str[1:])

            return S7Area.MK, 0, offset

        # Input addresses: I0.0, IW10, etc.
        elif address_str.startswith("I"):
            if "." in address_str:
                # Bit address: I0.0
                byte_addr, bit_addr = address_str[1:].split(".")
                offset = int(byte_addr) * 8 + int(bit_addr)
            elif address_str.startswith("IW"):
                # Word address: IW10
                offset = int(address_str[2:])
            elif address_str.startswith("ID"):
                # Double word address: ID10
                offset = int(address_str[2:])
            else:
                # Byte address: I10
                offset = int(address_str[1:])

            return S7Area.PE, 0, offset

        # Output addresses: Q0.0, QW10, etc.
        elif address_str.startswith("Q"):
            if "." in address_str:
                # Bit address: Q0.0
                byte_addr, bit_addr = address_str[1:].split(".")
                offset = int(byte_addr) * 8 + int(bit_addr)
            elif address_str.startswith("QW"):
                # Word address: QW10
                offset = int(address_str[2:])
            elif address_str.startswith("QD"):
                # Double word address: QD10
                offset = int(address_str[2:])
            else:
                # Byte address: Q10
                offset = int(address_str[1:])

            return S7Area.PA, 0, offset

        else:
            raise ValueError(f"Unsupported address format: {address_str}")
