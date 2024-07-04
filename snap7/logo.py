"""
Snap7 client used for connection to a siemens LOGO 7/8 server.
"""

import re
import struct
import logging
from ctypes import byref

from .type import WordLen, Area, Parameter

from .error import check_error, error_wrap
from snap7.client import Client

logger = logging.getLogger(__name__)


class Logo(Client):
    """
    A snap7 Siemens Logo client:
    There are two main comfort functions available :func:`Logo.read` and :func:`Logo.write`.
    This function offers high-level access to the VM addresses of the Siemens Logo just use the form:

    Notes:
        V10.3 for bit values
        V10 for the complete byte
        VW12 for a word (used for analog values)
        For more information see examples for Siemens Logo 7 and 8
    """

    @error_wrap(context="client")
    def connect(self, ip_address: str, tsap_snap7: int, tsap_logo: int, tcpport: int = 102) -> int:
        """Connect to a Siemens LOGO server.

        Notes:
            Howto setup Logo communication configuration see: https://snap7.sourceforge.net/logo.html

        Args:
            ip_address: IP ip_address of server
            tsap_snap7: TSAP SNAP7 Client (e.g. 10.00 = 0x1000)
            tsap_logo: TSAP Logo Server (e.g. 20.00 = 0x2000)

        Returns:
            Error code from snap7 library.
        """
        logger.info(f"connecting to {ip_address}:{tcpport} tsap_snap7 {tsap_snap7} tsap_logo {tsap_logo}")
        # special handling for Siemens Logo
        # 1st set connection params
        # 2nd connect without any parameters
        self.set_param(Parameter.RemotePort, tcpport)
        self.set_connection_params(ip_address, tsap_snap7, tsap_logo)
        return self._lib.Cli_Connect(self._s7_client)

    def read(self, vm_address: str) -> int:
        """Reads from VM addresses of Siemens Logo. Examples: read("V40") / read("VW64") / read("V10.2")

        Args:
            vm_address: of Logo memory (e.g. V30.1, VW32, V24)

        Returns:
            integer
        """
        area = Area.DB
        db_number = 1
        size = 1
        wordlen: WordLen
        logger.debug(f"read, vm_address:{vm_address}")
        if re.match(r"V[0-9]{1,4}\.[0-7]", vm_address):
            # bit value
            logger.info(f"read, Bit address: {vm_address}")
            address = vm_address[1:].split(".")
            # transform string to int
            address_byte = int(address[0])
            address_bit = int(address[1])
            start = (address_byte * 8) + address_bit
            wordlen = WordLen.Bit
        elif re.match("V[0-9]+", vm_address):
            # byte value
            logger.info(f"Byte address: {vm_address}")
            start = int(vm_address[1:])
            wordlen = WordLen.Byte
        elif re.match("VW[0-9]+", vm_address):
            # byte value
            logger.info(f"Word address: {vm_address}")
            start = int(vm_address[2:])
            wordlen = WordLen.Word
        elif re.match("VD[0-9]+", vm_address):
            # byte value
            logger.info(f"DWord address: {vm_address}")
            start = int(vm_address[2:])
            wordlen = WordLen.DWord
        else:
            logger.info("Unknown address format")
            return 0

        type_ = wordlen.ctype
        data = (type_ * size)()

        logger.debug(f"start:{start}, wordlen:{wordlen.name}={wordlen}, data-length:{len(data)}")

        result = self._lib.Cli_ReadArea(self._s7_client, area, db_number, start, size, wordlen, byref(data))
        check_error(result, context="client")
        # transform result to int value
        if wordlen == WordLen.Bit:
            result = int(data[0])
        if wordlen == WordLen.Byte:
            result = struct.unpack_from(">B", data)[0]
        if wordlen == WordLen.Word:
            result = struct.unpack_from(">h", data)[0]
        if wordlen == WordLen.DWord:
            result = struct.unpack_from(">l", data)[0]
        return result

    def write(self, vm_address: str, value: int) -> int:
        """Writes to VM addresses of Siemens Logo.

        Args:
            vm_address: write offset
            value: integer

        Examples:
            >>> Logo().write("VW10", 200) or Logo().write("V10.3", 1)
        """
        area = Area.DB
        db_number = 1
        amount = 1
        wordlen: WordLen
        logger.debug(f"write, vm_address:{vm_address}, value:{value}")
        if re.match(r"^V[0-9]{1,4}\.[0-7]$", vm_address):
            # bit value
            logger.info(f"read, Bit address: {vm_address}")
            address = vm_address[1:].split(".")
            # transform string to int
            address_byte = int(address[0])
            address_bit = int(address[1])
            start = (address_byte * 8) + address_bit
            wordlen = WordLen.Bit
            if value > 0:
                data = bytearray([1])
            else:
                data = bytearray([0])
        elif re.match("^V[0-9]+$", vm_address):
            # byte value
            logger.info(f"Byte address: {vm_address}")
            start = int(vm_address[1:])
            wordlen = WordLen.Byte
            data = bytearray(struct.pack(">B", value))
        elif re.match("^VW[0-9]+$", vm_address):
            # byte value
            logger.info(f"Word address: {vm_address}")
            start = int(vm_address[2:])
            wordlen = WordLen.Word
            data = bytearray(struct.pack(">h", value))
        elif re.match("^VD[0-9]+$", vm_address):
            # byte value
            logger.info(f"DWord address: {vm_address}")
            start = int(vm_address[2:])
            wordlen = WordLen.DWord
            data = bytearray(struct.pack(">l", value))
        else:
            logger.info(f"write, Unknown address format: {vm_address}")
            return 1

        if wordlen == WordLen.Bit:
            type_ = WordLen.Byte.ctype
        else:
            type_ = wordlen.ctype

        cdata = (type_ * amount).from_buffer_copy(data)

        logger.debug(f"write, vm_address:{vm_address} value:{value}")

        result = self._lib.Cli_WriteArea(self._s7_client, area, db_number, start, amount, wordlen, byref(cdata))
        check_error(result, context="client")
        return result
