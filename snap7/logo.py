"""
Snap7 client used for connection to a Siemens LOGO 7/8 server.

Pure Python implementation without C library dependency.
"""

import re
import struct
import logging
from typing import Optional

from .type import WordLen, Area
from .client import Client

logger = logging.getLogger(__name__)


def parse_address(vm_address: str) -> tuple[int, WordLen]:
    """
    Parse VM address string to start address and word length.

    Args:
        vm_address: Logo VM address (e.g. "V10", "VW20", "V10.3")

    Returns:
        Tuple of (start_address, word_length)
    """
    logger.debug(f"read, vm_address:{vm_address}")
    if re.match(r"V[0-9]{1,4}\.[0-7]", vm_address):
        logger.info(f"read, Bit address: {vm_address}")
        address = vm_address[1:].split(".")
        # transform string to int
        address_byte = int(address[0])
        address_bit = int(address[1])
        start = (address_byte * 8) + address_bit
        return start, WordLen.Bit
    elif re.match("V[0-9]+", vm_address):
        # byte value
        logger.info(f"Byte address: {vm_address}")
        start = int(vm_address[1:])
        return start, WordLen.Byte
    elif re.match("VW[0-9]+", vm_address):
        # byte value
        logger.info(f"Word address: {vm_address}")
        start = int(vm_address[2:])
        return start, WordLen.Word
    elif re.match("VD[0-9]+", vm_address):
        # byte value
        logger.info(f"DWord address: {vm_address}")
        start = int(vm_address[2:])
        return start, WordLen.DWord
    else:
        raise ValueError("Unknown address format")


class Logo(Client):
    """
    A snap7 Siemens Logo client.

    There are two main comfort functions available: :func:`Logo.read` and :func:`Logo.write`.
    This function offers high-level access to the VM addresses of the Siemens Logo just use the form:

    Notes:
        V10.3 for bit values
        V10 for the complete byte
        VW12 for a word (used for analog values)
        For more information see examples for Siemens Logo 7 and 8
    """

    def __init__(self, **kwargs):
        """
        Initialize Logo client.

        Args:
            **kwargs: Ignored. Kept for backwards compatibility.
        """
        super().__init__(**kwargs)
        self._logo_tsap_snap7: Optional[int] = None
        self._logo_tsap_logo: Optional[int] = None

    def connect(self, ip_address: str, tsap_snap7: int, tsap_logo: int, tcp_port: int = 102) -> "Logo":
        """Connect to a Siemens LOGO server.

        Notes:
            Howto setup Logo communication configuration see: https://snap7.sourceforge.net/logo.html

        Args:
            ip_address: IP ip_address of server
            tsap_snap7: TSAP SNAP7 Client (e.g. 10.00 = 0x1000)
            tsap_logo: TSAP Logo Server (e.g. 20.00 = 0x2000)
            tcp_port: TCP port of server

        Returns:
            The snap7 Logo instance
        """
        logger.info(f"connecting to {ip_address}:{tcp_port} tsap_snap7 {tsap_snap7} tsap_logo {tsap_logo}")

        # Store TSAP values for connection
        self._logo_tsap_snap7 = tsap_snap7
        self._logo_tsap_logo = tsap_logo

        # Set connection parameters
        self.local_tsap = tsap_snap7
        self.remote_tsap = tsap_logo
        self.host = ip_address
        self.port = tcp_port

        # Connect using parent Client implementation
        # For Logo, rack and slot are not used in the standard way
        # but we still need to establish the connection
        super().connect(ip_address, 0, 0, tcp_port)

        return self

    def read(self, vm_address: str) -> int:
        """Reads from VM addresses of Siemens Logo.

        Examples:
            read("V40") / read("VW64") / read("V10.2")

        Args:
            vm_address: of Logo memory (e.g. V30.1, VW32, V24)

        Returns:
            integer
        """
        db_number = 1
        logger.debug(f"read, vm_address:{vm_address}")
        start, wordlen = parse_address(vm_address)

        # Determine size based on word length
        if wordlen == WordLen.Bit:
            size = 1
        elif wordlen == WordLen.Byte:
            size = 1
        elif wordlen == WordLen.Word:
            size = 2
        elif wordlen == WordLen.DWord:
            size = 4
        else:
            size = 1

        logger.debug(f"start:{start}, wordlen:{wordlen.name}={wordlen}, size:{size}")

        # For bit access, we need to handle start address differently
        if wordlen == WordLen.Bit:
            # For Logo, bit access uses byte.bit notation converted to bit offset
            # Read the byte containing the bit
            byte_addr = start // 8
            bit_offset = start % 8
            data = self.read_area(Area.DB, db_number, byte_addr, 1)
            # Extract the bit
            result = (data[0] >> bit_offset) & 0x01
        else:
            # Read the appropriate number of bytes
            data = self.read_area(Area.DB, db_number, start, size)

            # Convert to integer based on word length
            if wordlen == WordLen.Byte:
                result = struct.unpack_from(">B", data)[0]
            elif wordlen == WordLen.Word:
                result = struct.unpack_from(">h", data)[0]
            elif wordlen == WordLen.DWord:
                result = struct.unpack_from(">l", data)[0]
            else:
                result = data[0]

        return result

    def write(self, vm_address: str, value: int) -> int:
        """Writes to VM addresses of Siemens Logo.

        Args:
            vm_address: write offset
            value: integer

        Returns:
            0 on success

        Examples:
            >>> Logo().write("VW10", 200) or Logo().write("V10.3", 1)
        """
        db_number = 1
        start, wordlen = parse_address(vm_address)

        logger.debug(f"write, vm_address:{vm_address} value:{value}")

        if wordlen == WordLen.Bit:
            # For bit access, read-modify-write
            byte_addr = start // 8
            bit_offset = start % 8

            # Read the current byte
            current = self.read_area(Area.DB, db_number, byte_addr, 1)
            byte_val = current[0]

            # Modify the bit
            if value > 0:
                byte_val |= 1 << bit_offset  # Set bit
            else:
                byte_val &= ~(1 << bit_offset)  # Clear bit

            # Write back
            data = bytearray([byte_val])
            self.write_area(Area.DB, db_number, byte_addr, data)

        elif wordlen == WordLen.Byte:
            data = bytearray(struct.pack(">B", value))
            self.write_area(Area.DB, db_number, start, data)

        elif wordlen == WordLen.Word:
            data = bytearray(struct.pack(">h", value))
            self.write_area(Area.DB, db_number, start, data)

        elif wordlen == WordLen.DWord:
            data = bytearray(struct.pack(">l", value))
            self.write_area(Area.DB, db_number, start, data)

        else:
            raise ValueError(f"Unknown wordlen {wordlen}")

        return 0
