"""
Snap7 client used for connection to a siemens LOGO 7/8 server.
"""
import re
from ctypes import c_int, byref, c_uint16, c_int32
from ctypes import c_void_p

import logging
import struct

import snap7
from snap7 import snap7types
from snap7.snap7types import S7Object
from snap7.snap7types import param_types

from snap7.common import check_error, load_library, ipv4
from snap7.snap7exceptions import Snap7Exception

logger = logging.getLogger(__name__)

# error_wrap decorator removed. Reason: The sphinx documentation generator can not handle decorators.
# There is a workaround available for the function name, but the parameters are not printed in the documentation.

class Logo(object):
    """
    A snap7 Siemens Logo client: There are two main comfort functions available :func:`Logo.read` and :func:`Logo.write`. 
    This functions realize a high level access to the VM addresses of the Siemens Logo just use the form:
    
    * V10.3 for bit values
    * V10 for the complete byte
    * VW12 for a word (used for analog values)
    
    For more information see examples for Siemens Logo 7 and 8  
    """
    def __init__(self):
        self.pointer = False
        self.library = load_library()
        self.create()

    def __del__(self):
        self.destroy()
        
    def create(self):
        """
        create a SNAP7 client.
        """
        logger.info("creating snap7 client")
        self.library.Cli_Create.restype = c_void_p
        self.pointer = S7Object(self.library.Cli_Create())

    def destroy(self):
        """
        destroy a client.
        """
        logger.info("destroying snap7 client")
        return self.library.Cli_Destroy(byref(self.pointer))

    def disconnect(self):
        """
        disconnect a client.
        """
        logger.info("disconnecting snap7 client")
        result = self.library.Cli_Disconnect(self.pointer)
        check_error(result, context="client") 
        return result

    def connect(self, ip_address, tsap_snap7, tsap_logo, tcpport=102):
        """
        Connect to a Siemens LOGO server. Howto setup Logo communication configuration see: http://snap7.sourceforge.net/logo.html

        :param ip_address: IP ip_address of server
        :param tsap_snap7: TSAP SNAP7 Client (e.g. 10.00 = 0x1000)
        :param tsap_logo: TSAP Logo Server (e.g. 20.00 = 0x2000)
        """
        logger.info("connecting to %s:%s tsap_snap7 %s tsap_logo %s" % (ip_address, tcpport,
                                                             tsap_snap7, tsap_logo))
        # special handling for Siemens Logo
        # 1st set connection params
        # 2nd connect without any parameters
        self.set_param(snap7.snap7types.RemotePort, tcpport)
        self.set_connection_params(ip_address, tsap_snap7, tsap_logo)
        result = self.library.Cli_Connect(self.pointer)
        check_error(result, context="client") 
        return result

    def read(self, vm_address):
        """
        Reads from VM addresses of Siemens Logo. Examples: read("V40") / read("VW64") / read("V10.2") 
        
        :param vm_address: of Logo memory (e.g. V30.1, VW32, V24)
        :returns: integer
        """
        area = snap7types.S7AreaDB
        db_number = 1
        size = 1
        start = 0
        wordlen = 0
        logger.debug("read, vm_address:%s" % (vm_address))
        if re.match("V[0-9]{1,4}\.[0-7]{1}", vm_address):
            ## bit value
            logger.info("read, Bit address: " + vm_address)
            address = vm_address[1:].split(".")
            # transform string to int
            address_byte = int(address[0])
            address_bit = int(address[1])
            start = (address_byte*8)+address_bit
            wordlen = snap7types.S7WLBit
        elif re.match("V[0-9]+", vm_address):
            ## byte value
            logger.info("Byte address: " + vm_address)
            start = int(vm_address[1:])
            wordlen = snap7types.S7WLByte
        elif re.match("VW[0-9]+", vm_address):
            ## byte value
            logger.info("Word address: " + vm_address)
            start = int(vm_address[2:])
            wordlen = snap7types.S7WLWord
        elif re.match("VD[0-9]+", vm_address):
            ## byte value
            logger.info("DWord address: " + vm_address)
            start = int(vm_address[2:])
            wordlen = snap7types.S7WLDWord
        else:
            logger.info("Unknown address format")
            return 0
             
        type_ = snap7.snap7types.wordlen_to_ctypes[wordlen]
        data = (type_ * size)()

        logger.debug("start:%s, wordlen:%s, data-length:%s" % (start, wordlen, len(data)) )

        result = self.library.Cli_ReadArea(self.pointer, area, db_number, start,
                                           size, wordlen, byref(data))
        check_error(result, context="client")
        # transform result to int value
        if wordlen == snap7types.S7WLBit:
            return(data)[0]
        if wordlen == snap7types.S7WLByte:
            return struct.unpack_from(">B", data)[0]
        if wordlen == snap7types.S7WLWord:
            return struct.unpack_from(">h", data)[0]
        if wordlen == snap7types.S7WLDWord:
            return struct.unpack_from(">l", data)[0]

    def write (self, vm_address, value):
        """
        Writes to VM addresses of Siemens Logo.
        Example: write("VW10", 200) or write("V10.3", 1)

        :param vm_address: write offset
        :param value: integer
        """
        area = snap7types.S7AreaDB
        db_number = 1
        start = 0
        amount = 1
        wordlen = 0
        data = bytearray(0)
        logger.debug("write, vm_address:%s, value:%s" %
                     (vm_address, value))
        if re.match("^V[0-9]{1,4}\.[0-7]{1}$", vm_address):
            ## bit value
            logger.info("read, Bit address: " + vm_address)
            address = vm_address[1:].split(".")
            # transform string to int
            address_byte = int(address[0])
            address_bit = int(address[1])
            start = (address_byte*8)+address_bit
            wordlen = snap7types.S7WLBit
            if value > 0:
                data = bytearray([1])    
            else:
                data = bytearray([0])
        elif re.match("^V[0-9]+$", vm_address):
            ## byte value
            logger.info("Byte address: " + vm_address)
            start = int(vm_address[1:])
            wordlen = snap7types.S7WLByte
            data = bytearray(struct.pack(">B", value))
        elif re.match("^VW[0-9]+$", vm_address):
            ## byte value
            logger.info("Word address: " + vm_address)
            start = int(vm_address[2:])
            wordlen = snap7types.S7WLWord
            data = bytearray(struct.pack(">h", value))
        elif re.match("^VD[0-9]+$", vm_address):
            ## byte value
            logger.info("DWord address: " + vm_address)
            start = int(vm_address[2:])
            wordlen = snap7types.S7WLDWord
            data = bytearray(struct.pack(">l", value))
        else:
            logger.info("write, Unknown address format: " + vm_address)
            return 1
        
        if wordlen == snap7types.S7WLBit:
            type_ = snap7.snap7types.wordlen_to_ctypes[snap7types.S7WLByte]
        else:
            type_ = snap7.snap7types.wordlen_to_ctypes[wordlen]
        
        cdata = (type_ * amount).from_buffer_copy(data)

        logger.debug("write, vm_address:%s value:%s" % (vm_address, value))

        result = self.library.Cli_WriteArea(self.pointer, area, db_number, start,
                                          amount, wordlen, byref(cdata))
        check_error(result, context="client")
        return result

    def db_read(self, db_number, start, size):
        """
        This is a lean function of Cli_ReadArea() to read PLC DB.

        :param db_number: for Logo only DB=1
        :param start: start address for Logo7 0..951 / Logo8 0..1469
        :param size: in bytes
        :returns: array of bytes
        """
        logger.debug("db_read, db_number:%s, start:%s, size:%s" %
                     (db_number, start, size))

        type_ = snap7.snap7types.wordlen_to_ctypes[snap7.snap7types.S7WLByte]
        data = (type_ * size)()
        result = (self.library.Cli_DBRead(
            self.pointer, db_number, start, size,
            byref(data)))
        check_error(result, context="client")
        return bytearray(data)

    def db_write(self, db_number, start, data):
        """
        Writes to a DB object.

        :param db_number: for Logo only DB=1
        :param start: start address for Logo7 0..951 / Logo8 0..1469
        :param data: bytearray
        """
        wordlen = snap7.snap7types.S7WLByte
        type_ = snap7.snap7types.wordlen_to_ctypes[wordlen]
        size = len(data)
        cdata = (type_ * size).from_buffer_copy(data)
        logger.debug("db_write db_number:%s start:%s size:%s data:%s" %
                     (db_number, start, size, data))
        result = self.library.Cli_DBWrite(self.pointer, db_number, start, size,
                                        byref(cdata))
        check_error(result, context="client") 
        return result

    def set_connection_params(self, ip_address, tsap_snap7, tsap_logo):
        """
        Sets internally (IP, LocalTSAP, RemoteTSAP) Coordinates.
        This function must be called just before Cli_Connect().

        :param ip_address: IP ip_address of server
        :param tsap_snap7: TSAP SNAP7 Client (e.g. 10.00 = 0x1000)
        :param tsap_logo: TSAP Logo Server (e.g. 20.00 = 0x2000)
        """
        assert re.match(ipv4, ip_address), '%s is invalid ipv4' % ip_address
        result = self.library.Cli_SetConnectionParams(self.pointer, ip_address.encode(),
                                                      c_uint16(tsap_snap7),
                                                      c_uint16(tsap_logo))
        if result != 0:
            raise Snap7Exception("The parameter was invalid")

    def set_connection_type(self, connection_type):
        """
        Sets the connection resource type, i.e the way in which the Clients
        connects to a PLC.

        :param connection_type: 1 for PG, 2 for OP, 3 to 10 for S7 Basic
        """
        result = self.library.Cli_SetConnectionType(self.pointer,
                                                    c_uint16(connection_type))
        if result != 0:
            raise Snap7Exception("The parameter was invalid")

    def get_connected(self):
        """
        Returns the connection status

        :returns: a boolean that indicates if connected.
        """
        connected = c_int32()
        result = self.library.Cli_GetConnected(self.pointer, byref(connected))
        check_error(result, context="client")
        return bool(connected)

    def set_param(self, number, value):
        """Sets an internal Server object parameter.
        
        :param number: Parameter type number
        :param value: Parameter value
        """
        logger.debug("setting param number %s to %s" % (number, value))
        type_ = param_types[number]
        result = self.library.Cli_SetParam(self.pointer, number,
                                         byref(type_(value)))
        check_error(result, context="client") 
        return result

    def get_param(self, number):
        """Reads an internal Logo object parameter.
        
        :param number: Parameter type number
        :returns: Parameter value
        """
        logger.debug("retreiving param number %s" % number)
        type_ = param_types[number]
        value = type_()
        code = self.library.Cli_GetParam(self.pointer, c_int(number),
                                         byref(value))
        check_error(code)
        return value.value

