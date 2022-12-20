"""
Snap7 server used for mimicking a siemens 7 server.
"""
import re
import time
import ctypes
import struct
import logging
from typing import Any, Tuple, Callable, Optional

from ..common import ipv4, check_error, load_library
from ..types import SrvEvent, LocalPort, cpu_statuses, server_statuses
from ..types import longword, wordlen_to_ctypes, WordLen, S7Object
from ..types import srvAreaDB, srvAreaPA, srvAreaTM, srvAreaCT

logger = logging.getLogger(__name__)


def error_wrap(func):
    """Parses a s7 error code returned the decorated function."""
    def f(*args, **kw):
        code = func(*args, **kw)
        check_error(code, context="server")

    return f


class Server:
    """
    A fake S7 server.
    """

    def __init__(self, log: bool = True):
        """Create a fake S7 server. set log to false if you want to disable
            event logging to python logging.

        Args:
            log: `True` for enabling the event logging. Optinoal.
        """
        self._read_callback = None
        self._callback = Optional[Callable[..., Any]]
        self.pointer = None
        self.library = load_library()
        self.create()
        if log:
            self._set_log_callback()

    def __del__(self):
        self.destroy()

    def event_text(self, event: SrvEvent) -> str:
        """Returns a textual explanation of a given event object

        Args:
            event: an PSrvEvent struct object

        Returns:
            The error string
        """
        logger.debug(f"error text for {hex(event.EvtCode)}")
        len_ = 1024
        text_type = ctypes.c_char * len_
        text = text_type()
        error = self.library.Srv_EventText(ctypes.byref(event),
                                           ctypes.byref(text), len_)
        check_error(error)
        return text.value.decode('ascii')

    def create(self):
        """Create the server.
        """
        logger.info("creating server")
        self.library.Srv_Create.restype = S7Object
        self.pointer = S7Object(self.library.Srv_Create())

    @error_wrap
    def register_area(self, area_code: int, index: int, userdata):
        """Shares a memory area with the server. That memory block will be
            visible by the clients.

        Args:
            area_code: memory area to register.
            index: number of area to write.
            userdata: buffer with the data to write.

        Returns:
            Error code from snap7 library.
        """
        size = ctypes.sizeof(userdata)
        logger.info(f"registering area {area_code}, index {index}, size {size}")
        return self.library.Srv_RegisterArea(self.pointer, area_code, index, ctypes.byref(userdata), size)

    @error_wrap
    def set_events_callback(self, call_back: Callable[..., Any]) -> int:
        """Sets the user callback that the Server object has to call when an
            event is created.
        """
        logger.info("setting event callback")
        callback_wrap: Callable[..., Any] = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.POINTER(SrvEvent), ctypes.c_int)

        def wrapper(usrptr: Optional[ctypes.c_void_p], pevent: SrvEvent, size: int) -> int:
            """Wraps python function into a ctypes function

            Args:
                usrptr: not used
                pevent: pointer to snap7 event struct
                size:

            Returns:
                Should return an int
            """
            logger.info(f"callback event: {self.event_text(pevent.contents)}")
            call_back(pevent.contents)
            return 0

        self._callback = callback_wrap(wrapper)
        usrPtr = ctypes.c_void_p()
        return self.library.Srv_SetEventsCallback(self.pointer, self._callback, usrPtr)

    @error_wrap
    def set_read_events_callback(self, call_back: Callable[..., Any]):
        """Sets the user callback that the Server object has to call when a Read
            event is created.

        Args:
            call_back: a callback function that accepts a pevent argument.
        """
        logger.info("setting read event callback")
        callback_wrapper: Callable[..., Any] = ctypes.CFUNCTYPE(None, ctypes.c_void_p,
                                                                ctypes.POINTER(SrvEvent),
                                                                ctypes.c_int)

        def wrapper(usrptr: Optional[ctypes.c_void_p], pevent: SrvEvent, size: int) -> int:
            """Wraps python function into a ctypes function

            Args:
                usrptr: not used
                pevent: pointer to snap7 event struct
                size:

            Returns:
                Should return an int
            """
            logger.info(f"callback event: {self.event_text(pevent.contents)}")
            call_back(pevent.contents)
            return 0

        self._read_callback = callback_wrapper(wrapper)
        return self.library.Srv_SetReadEventsCallback(self.pointer,
                                                      self._read_callback)

    def _set_log_callback(self):
        """Sets a callback that logs the events"""
        logger.debug("setting up event logger")

        def log_callback(event):
            logger.info(f"callback event: {self.event_text(event)}")

        self.set_events_callback(log_callback)

    @error_wrap
    def start(self, tcpport: int = 102):
        """Starts the server.

        Args:
            tcpport: port that the server will listen. Optional.
        """
        if tcpport != 102:
            logger.info(f"setting server TCP port to {tcpport}")
            self.set_param(LocalPort, tcpport)
        logger.info(f"starting server on 0.0.0.0:{tcpport}")
        return self.library.Srv_Start(self.pointer)

    @error_wrap
    def stop(self):
        """Stop the server."""
        logger.info("stopping server")
        return self.library.Srv_Stop(self.pointer)

    def destroy(self):
        """Destroy the server."""
        logger.info("destroying server")
        if self.library:
            self.library.Srv_Destroy(ctypes.byref(self.pointer))

    def get_status(self) -> Tuple[str, str, int]:
        """Reads the server status, the Virtual CPU status and the number of
            the clients connected.

        Returns:
            Server status, cpu status, client count
        """
        logger.debug("get server status")
        server_status = ctypes.c_int()
        cpu_status = ctypes.c_int()
        clients_count = ctypes.c_int()
        error = self.library.Srv_GetStatus(self.pointer, ctypes.byref(server_status),
                                           ctypes.byref(cpu_status),
                                           ctypes.byref(clients_count))
        check_error(error)
        logger.debug(f"status server {server_status.value} cpu {cpu_status.value} clients {clients_count.value}")
        return (
            server_statuses[server_status.value],
            cpu_statuses[cpu_status.value],
            clients_count.value
        )

    @error_wrap
    def unregister_area(self, area_code: int, index: int):
        """'Unshares' a memory area previously shared with Srv_RegisterArea().

        Notes:
            That memory block will be no longer visible by the clients.

        Args:
            area_code: memory area.
            index: number of the memory area.

        Returns:
            Error code from snap7 library.
        """
        return self.library.Srv_UnregisterArea(self.pointer, area_code, index)

    @error_wrap
    def unlock_area(self, code: int, index: int):
        """Unlocks a previously locked shared memory area.

        Args:
            code: memory area.
            index: number of the memory area.

        Returns:
            Error code from snap7 library.
        """
        logger.debug(f"unlocking area code {code} index {index}")
        return self.library.Srv_UnlockArea(self.pointer, code, index)

    @error_wrap
    def lock_area(self, code: int, index: int):
        """Locks a shared memory area.

        Args:
            code: memory area.
            index: number of the memory area.

        Returns:
            Error code from snap7 library.
        """
        logger.debug(f"locking area code {code} index {index}")
        return self.library.Srv_LockArea(self.pointer, code, index)

    @error_wrap
    def start_to(self, ip: str, tcpport: int = 102):
        """Start server on a specific interface.

        Args:
            ip: IPV4 address where the server is located.
            tcpport: port that the server will listening.

        Raises:
            :obj:`ValueError`: if the `ivp4` is not a valid IPV4
        """
        if tcpport != 102:
            logger.info(f"setting server TCP port to {tcpport}")
            self.set_param(LocalPort, tcpport)
        if not re.match(ipv4, ip):
            raise ValueError(f"{ip} is invalid ipv4")
        logger.info(f"starting server to {ip}:102")
        return self.library.Srv_StartTo(self.pointer, ip.encode())

    @error_wrap
    def set_param(self, number: int, value: int):
        """Sets an internal Server object parameter.

        Args:
            number: number of the parameter.
            value: value to be set.

        Returns:
            Error code from snap7 library.
        """
        logger.debug(f"setting param number {number} to {value}")
        return self.library.Srv_SetParam(self.pointer, number,
                                         ctypes.byref(ctypes.c_int(value)))

    @error_wrap
    def set_mask(self, kind: int, mask: int):
        """Writes the specified filter mask.

        Args:
            kind:
            mask:

        Returns:
            Error code from snap7 library.
        """
        logger.debug(f"setting mask kind {kind} to {mask}")
        return self.library.Srv_SetMask(self.pointer, kind, mask)

    @error_wrap
    def set_cpu_status(self, status: int):
        """Sets the Virtual CPU status.

        Args:
            status: :obj:`cpu_statuses` object type.

        Returns:
            Error code from snap7 library.

        Raises:
            :obj:`ValueError`: if `status` is not in :obj:`cpu_statuses`.
        """
        if status not in cpu_statuses:
            raise ValueError(f"The cpu state ({status}) is invalid")
        logger.debug(f"setting cpu status to {status}")
        return self.library.Srv_SetCpuStatus(self.pointer, status)

    def pick_event(self) -> Optional[SrvEvent]:
        """Extracts an event (if available) from the Events queue.

        Returns:
            Server event.
        """
        logger.debug("checking event queue")
        event = SrvEvent()
        ready = ctypes.c_int32()
        code = self.library.Srv_PickEvent(self.pointer, ctypes.byref(event),
                                          ctypes.byref(ready))
        check_error(code)
        if ready:
            logger.debug(f"one event ready: {event}")
            return event
        logger.debug("no events ready")
        return None

    def get_param(self, number) -> int:
        """Reads an internal Server object parameter.

        Args:
            number: number of the parameter to be set.

        Returns:
            Value of the parameter.
        """
        logger.debug(f"retreiving param number {number}")
        value = ctypes.c_int()
        code = self.library.Srv_GetParam(self.pointer, number,
                                         ctypes.byref(value))
        check_error(code)
        return value.value

    def get_mask(self, kind: int) -> ctypes.c_uint32:
        """Reads the specified filter mask.

        Args:
            kind:

        Returns:
            Mask
        """
        logger.debug(f"retrieving mask kind {kind}")
        mask = longword()
        code = self.library.Srv_GetMask(self.pointer, kind, ctypes.byref(mask))
        check_error(code)
        return mask

    @error_wrap
    def clear_events(self) -> int:
        """Empties the Event queue.

        Returns:
            Error code from snap7 library.
        """
        logger.debug("clearing event queue")
        return self.library.Srv_ClearEvents(self.pointer)


def mainloop(tcpport: int = 1102, init_standard_values: bool = False):
    """Init a fake Snap7 server with some default values.

    Args:
        tcpport: port that the server will listen.
        init_standard_values: if `True` will init some defaults values to be read on DB0.
    """

    server = Server()
    size = 100
    DBdata = (wordlen_to_ctypes[WordLen.Byte.value] * size)()
    PAdata = (wordlen_to_ctypes[WordLen.Byte.value] * size)()
    TMdata = (wordlen_to_ctypes[WordLen.Byte.value] * size)()
    CTdata = (wordlen_to_ctypes[WordLen.Byte.value] * size)()
    server.register_area(srvAreaDB, 1, DBdata)
    server.register_area(srvAreaPA, 1, PAdata)
    server.register_area(srvAreaTM, 1, TMdata)
    server.register_area(srvAreaCT, 1, CTdata)

    if init_standard_values:
        ba = _init_standard_values()
        DBdata = wordlen_to_ctypes[WordLen.Byte.value] * len(ba)
        DBdata = DBdata.from_buffer(ba)
        server.register_area(srvAreaDB, 0, DBdata)

    server.start(tcpport=tcpport)
    while True:
        while True:
            event = server.pick_event()
            if event:
                logger.info(server.event_text(event))
            else:
                break
        time.sleep(1)


def _init_standard_values() -> bytearray:
    ''' Standard values
    * Boolean
    BYTE    BIT     VALUE
    0       0       True
    0       1       False
    0       2       True
    0       3       False
    0       4       True
    0       5       False
    0       6       True
    0       7       False

    * Small int
    BYTE    VALUE
    10      -128
    11      0
    12      100
    13      127

    * Unsigned small int
    BYTE    VALUE
    20      0
    21      255

    * Int
    BYTE    VALUE
    30      -32768
    32      -1234
    34      0
    36      1234
    38      32767

    * Double int
    BYTE    VALUE
    40      -2147483648
    44      -32768
    48      0
    52      32767
    56      2147483647

    * Real
    BYTE    VALUE
    60      -3.402823e38
    64      -3.402823e12
    68      -175494351e-38
    72      -1.175494351e-12
    76      0.0
    80      1.175494351e-38
    84      1.175494351e-12
    88      3.402823466e12
    92      3.402823466e38

    * String
    BYTE    VALUE
    100     254|37|the brown fox jumps over the lazy dog

    * Word
    BYTE    VALUE
    400     \x00\x00
    404     \x12\x34
    408     \xAB\xCD
    412     \xFF\xFF

    * Double Word
    BYTE    VALUE
    500     \x00\x00\x00\x00
    508     \x12\x34\x56\x78
    516     \x12\x34\xAB\xCD
    524     \xFF\xFF\xFF\xFF
    '''

    ba = bytearray(1000)
    # 1. Bool 1 byte
    ba[0] = 0b10101010

    # 2. Small int 1 byte
    ba[10:10 + 1] = struct.pack(">b", -128)
    ba[11:11 + 1] = struct.pack(">b", 0)
    ba[12:12 + 1] = struct.pack(">b", 100)
    ba[13:13 + 1] = struct.pack(">b", 127)

    # 3. Unsigned small int 1 byte
    ba[20:20 + 1] = struct.pack("B", 0)
    ba[21:21 + 1] = struct.pack("B", 255)

    # 4. Int 2 bytes
    ba[30:30 + 2] = struct.pack(">h", -32768)
    ba[32:32 + 2] = struct.pack(">h", -1234)
    ba[34:34 + 2] = struct.pack(">h", 0)
    ba[36:36 + 2] = struct.pack(">h", 1234)
    ba[38:38 + 2] = struct.pack(">h", 32767)

    # 5. DInt 4 bytes
    ba[40:40 + 4] = struct.pack(">i", -2147483648)
    ba[44:44 + 4] = struct.pack(">i", -32768)
    ba[48:48 + 4] = struct.pack(">i", 0)
    ba[52:52 + 4] = struct.pack(">i", 32767)
    ba[56:56 + 4] = struct.pack(">i", 2147483647)

    # 6. Real 4 bytes
    ba[60:60 + 4] = struct.pack(">f", -3.402823e38)
    ba[64:64 + 4] = struct.pack(">f", -3.402823e12)
    ba[68:68 + 4] = struct.pack(">f", -175494351e-38)
    ba[72:72 + 4] = struct.pack(">f", -1.175494351e-12)
    ba[76:76 + 4] = struct.pack(">f", 0.0)
    ba[80:80 + 4] = struct.pack(">f", 1.175494351e-38)
    ba[84:84 + 4] = struct.pack(">f", 1.175494351e-12)
    ba[88:88 + 4] = struct.pack(">f", 3.402823466e12)
    ba[92:92 + 4] = struct.pack(">f", 3.402823466e38)

    # 7. String 1 byte per char
    string = "the brown fox jumps over the lazy dog"  # len = 37
    ba[100] = 254
    ba[101] = len(string)
    for letter, i in zip(string, range(102, 102 + len(string) + 1)):
        ba[i] = ord(letter)

    # 8. WORD 4 bytes
    ba[400:400 + 4] = b"\x00\x00"
    ba[404:404 + 4] = b"\x12\x34"
    ba[408:408 + 4] = b"\xAB\xCD"
    ba[412:412 + 4] = b"\xFF\xFF"

    # # 9 DWORD 8 bytes
    ba[500:500 + 8] = b"\x00\x00\x00\x00"
    ba[508:508 + 8] = b"\x12\x34\x56\x78"
    ba[516:516 + 8] = b"\x12\x34\xAB\xCD"
    ba[524:524 + 8] = b"\xFF\xFF\xFF\xFF"

    return ba
