"""
Snap7 client used for connection to a siemens LOGO 7/8 server.
"""
import re
import struct
import logging
from ctypes import byref, c_int, c_int32, c_uint16, c_void_p

from .types import WordLen, S7Object, param_types
from .types import RemotePort, Areas, wordlen_to_ctypes
from .common import ipv4, check_error, load_library

logger = logging.getLogger(__name__)


class Logo:
    """
    A snap7 Siemens Logo client:
    There are two main comfort functions available :func:`Logo.read` and :func:`Logo.write`.
    This functions realize a high level access to the VM addresses of the Siemens Logo just use the form:

    Notes:
        V10.3 for bit values
        V10 for the complete byte
        VW12 for a word (used for analog values)
        For more information see examples for Siemens Logo 7 and 8
    """

    def __init__(self):
        """Creates a new instance of :obj:`Logo`"""
        self.pointer = None
        self.library = load_library()
        self.create()

    def __del__(self):
        self.destroy()

    def create(self):
        """Create a SNAP7 client."""
        logger.info("creating snap7 client")
        self.library.Cli_Create.restype = c_void_p
        self.pointer = S7Object(self.library.Cli_Create())

    def destroy(self) -> int:
        """Destroy a client.

        Returns:
            Error code from snap7 library.

        """
        logger.info("destroying snap7 client")
        return self.library.Cli_Destroy(byref(self.pointer))

    def disconnect(self) -> int:
        """Disconnect a client.

        Returns:
            Error code from snap7 library.
        """
        logger.info("disconnecting snap7 client")
        result = self.library.Cli_Disconnect(self.pointer)
        check_error(result, context="client")
        return result

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
        self.set_param(RemotePort, tcpport)
        self.set_connection_params(ip_address, tsap_snap7, tsap_logo)
        result = self.library.Cli_Connect(self.pointer)
        check_error(result, context="client")
        return result

    def read(self, vm_address: str):
        """Reads from VM addresses of Siemens Logo. Examples: read("V40") / read("VW64") / read("V10.2")

        Args:
            vm_address: of Logo memory (e.g. V30.1, VW32, V24)

        Returns:
            integer
        """
        area = Areas.DB
        db_number = 1
        size = 1
        start = 0
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

        type_ = wordlen_to_ctypes[wordlen.value]
        data = (type_ * size)()

        logger.debug(f"start:{start}, wordlen:{wordlen.name}={wordlen.value}, data-length:{len(data)}")

        result = self.library.Cli_ReadArea(self.pointer, area.value, db_number, start,
                                           size, wordlen.value, byref(data))
        check_error(result, context="client")
        # transform result to int value
        if wordlen == WordLen.Bit:
            return data[0]
        if wordlen == WordLen.Byte:
            return struct.unpack_from(">B", data)[0]
        if wordlen == WordLen.Word:
            return struct.unpack_from(">h", data)[0]
        if wordlen == WordLen.DWord:
            return struct.unpack_from(">l", data)[0]

    def write(self, vm_address: str, value: int) -> int:
        """Writes to VM addresses of Siemens Logo.

        Args:
            vm_address: write offset
            value: integer

        Examples:
            >>> write("VW10", 200) or write("V10.3", 1)
        """
        area = Areas.DB
        db_number = 1
        start = 0
        amount = 1
        wordlen: WordLen
        data = bytearray(0)
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
            type_ = wordlen_to_ctypes[WordLen.Byte.value]
        else:
            type_ = wordlen_to_ctypes[wordlen.value]

        cdata = (type_ * amount).from_buffer_copy(data)

        logger.debug(f"write, vm_address:{vm_address} value:{value}")

        result = self.library.Cli_WriteArea(self.pointer, area.value, db_number, start, amount, wordlen.value, byref(cdata))
        check_error(result, context="client")
        return result

    def db_read(self, db_number: int, start: int, size: int) -> bytearray:
        """This is a lean function of Cli_ReadArea() to read PLC DB.

        Args:
            db_number: for Logo only DB=1
            start: start address for Logo7 0..951 / Logo8 0..1469
            size: in bytes

        Returns:
            Array of bytes
        """
        logger.debug(f"db_read, db_number:{db_number}, start:{start}, size:{size}")

        type_ = wordlen_to_ctypes[WordLen.Byte.value]
        data = (type_ * size)()
        result = (self.library.Cli_DBRead(
            self.pointer, db_number, start, size,
            byref(data)))
        check_error(result, context="client")
        return bytearray(data)

    def db_write(self, db_number: int, start: int, data: bytearray) -> int:
        """Writes to a DB object.

        Args:
            db_number: for Logo only DB=1
            start: start address for Logo7 0..951 / Logo8 0..1469
            data: bytearray

        Returns:
            Error code from snap7 library.
        """
        wordlen = WordLen.Byte
        type_ = wordlen_to_ctypes[wordlen.value]
        size = len(data)
        cdata = (type_ * size).from_buffer_copy(data)
        logger.debug(f"db_write db_number:{db_number} start:{start} size:{size} data:{data}")
        result = self.library.Cli_DBWrite(self.pointer, db_number, start, size, byref(cdata))
        check_error(result, context="client")
        return result

    def set_connection_params(self, ip_address: str, tsap_snap7: int, tsap_logo: int):
        """Sets internally (IP, LocalTSAP, RemoteTSAP) Coordinates.

        Notes:
            This function must be called just before Cli_Connect().

        Args:
            ip_address: IP ip_address of server
            tsap_snap7: TSAP SNAP7 Client (e.g. 10.00 = 0x1000)
            tsap_logo: TSAP Logo Server (e.g. 20.00 = 0x2000)

        Raises:
            :obj:`ValueError`: if the `ip_address` is not an IPV4.
            :obj:`ValueError`: if the snap7 error code is diferent from 0.
        """
        if not re.match(ipv4, ip_address):
            raise ValueError(f"{ip_address} is invalid ipv4")
        result = self.library.Cli_SetConnectionParams(self.pointer, ip_address.encode(),
                                                      c_uint16(tsap_snap7),
                                                      c_uint16(tsap_logo))
        if result != 0:
            raise ValueError("The parameter was invalid")

    def set_connection_type(self, connection_type: int):
        """Sets the connection resource type, i.e the way in which the Clients
            connects to a PLC.

        Args:
            connection_type: 1 for PG, 2 for OP, 3 to 10 for S7 Basic

        Raises:
            :obj:`ValueError`: if the snap7 error code is diferent from 0.
        """
        result = self.library.Cli_SetConnectionType(self.pointer,
                                                    c_uint16(connection_type))
        if result != 0:
            raise ValueError("The parameter was invalid")

    def get_connected(self) -> bool:
        """Returns the connection status

        Notes:
            This function has a bug, that returns `True` when the connection
                is lost. This comes from the original `snap7 library`.

        Returns:
            True if connected.
        """
        connected = c_int32()
        result = self.library.Cli_GetConnected(self.pointer, byref(connected))
        check_error(result, context="client")
        return bool(connected)

    def set_param(self, number: int, value):
        """Sets an internal Server object parameter.

        Args:
            number: Parameter type number
            value: Parameter value

        Returns:
            Error code from snap7 library.
        """
        logger.debug(f"setting param number {number} to {value}")
        type_ = param_types[number]
        result = self.library.Cli_SetParam(self.pointer, number, byref(type_(value)))
        check_error(result, context="client")
        return result

    def get_param(self, number) -> int:
        """Reads an internal Logo object parameter.

        Args:
            number: Parameter type number

        Returns:
            Parameter value
        """
        logger.debug(f"retreiving param number {number}")
        type_ = param_types[number]
        value = type_()
        code = self.library.Cli_GetParam(self.pointer, c_int(number),
                                         byref(value))
        check_error(code)
        return value.value
