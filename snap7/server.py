"""
Snap7 server used for mimicking a siemens 7 server.
"""
import logging
import re
import time
import ctypes
from typing import Tuple, Optional, Callable, Any

import snap7
import snap7.types
from snap7.common import check_error, load_library, ipv4

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
        """
        Create a fake S7 server. set log to false if you want to disable
        event logging to python logging.
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

    def event_text(self, event: snap7.types.SrvEvent) -> str:
        """Returns a textual explanation of a given event object

        :param event: an PSrvEvent struct object
        :returns: the error string
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
        """
        create the server.
        """
        logger.info("creating server")
        self.library.Srv_Create.restype = snap7.types.S7Object
        self.pointer = snap7.types.S7Object(self.library.Srv_Create())

    @error_wrap
    def register_area(self, area_code: int, index: int, userdata):
        """Shares a memory area with the server. That memory block will be
        visible by the clients.
        """
        size = ctypes.sizeof(userdata)
        logger.info(f"registering area {area_code}, index {index}, size {size}")
        size = ctypes.sizeof(userdata)
        return self.library.Srv_RegisterArea(self.pointer, area_code, index, ctypes.byref(userdata), size)

    @error_wrap
    def set_events_callback(self, call_back: Callable[..., Any]) -> int:
        """Sets the user callback that the Server object has to call when an
        event is created.
        """
        logger.info("setting event callback")
        callback_wrap: Callable[..., Any] = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.POINTER(snap7.types.SrvEvent), ctypes.c_int)

        def wrapper(usrptr: Optional[ctypes.c_void_p], pevent: snap7.types.SrvEvent, size: int) -> int:
            """
            Wraps python function into a ctypes function

            :param usrptr: not used
            :param pevent: pointer to snap7 event struct
            :param size:
            :returns: should return an int
            """
            logger.info(f"callback event: {self.event_text(pevent.contents)}")
            call_back(pevent.contents)
            return 0

        self._callback = callback_wrap(wrapper)
        usrPtr = ctypes.c_void_p()
        return self.library.Srv_SetEventsCallback(self.pointer, self._callback, usrPtr)

    @error_wrap
    def set_read_events_callback(self, call_back: Callable[..., Any]):
        """
        Sets the user callback that the Server object has to call when a Read
        event is created.

        :param call_back: a callback function that accepts a pevent argument.
        """
        logger.info("setting read event callback")
        callback_wrapper: Callable[..., Any] = ctypes.CFUNCTYPE(None, ctypes.c_void_p,
                                                                ctypes.POINTER(snap7.types.SrvEvent),
                                                                ctypes.c_int)

        def wrapper(usrptr: Optional[ctypes.c_void_p], pevent: snap7.types.SrvEvent, size: int) -> int:
            """
            Wraps python function into a ctypes function

            :param usrptr: not used
            :param pevent: pointer to snap7 event struct
            :param size:
            :returns: should return an int
            """
            logger.info(f"callback event: {self.event_text(pevent.contents)}")
            call_back(pevent.contents)
            return 0

        self._read_callback = callback_wrapper(wrapper)
        return self.library.Srv_SetReadEventsCallback(self.pointer,
                                                      self._read_callback)

    def _set_log_callback(self):
        """Sets a callback that logs the events
        """
        logger.debug("setting up event logger")

        def log_callback(event):
            logger.info(f"callback event: {self.event_text(event)}")

        self.set_events_callback(log_callback)

    @error_wrap
    def start(self, tcpport: int = 102):
        """
        start the server.
        """
        if tcpport != 102:
            logger.info(f"setting server TCP port to {tcpport}")
            self.set_param(snap7.types.LocalPort, tcpport)
        logger.info(f"starting server on 0.0.0.0:{tcpport}")
        return self.library.Srv_Start(self.pointer)

    @error_wrap
    def stop(self):
        """
        stop the server.
        """
        logger.info("stopping server")
        return self.library.Srv_Stop(self.pointer)

    def destroy(self):
        """
        destroy the server.
        """
        logger.info("destroying server")
        if self.library:
            self.library.Srv_Destroy(ctypes.byref(self.pointer))

    def get_status(self) -> Tuple[str, str, int]:
        """Reads the server status, the Virtual CPU status and the number of
        the clients connected.

        :returns: server status, cpu status, client count
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
            snap7.types.server_statuses[server_status.value],
            snap7.types.cpu_statuses[cpu_status.value],
            clients_count.value
        )

    @error_wrap
    def unregister_area(self, area_code: int, index: int):
        """'Unshares' a memory area previously shared with Srv_RegisterArea().
        That memory block will be no longer visible by the clients.
        """
        return self.library.Srv_UnregisterArea(self.pointer, area_code, index)

    @error_wrap
    def unlock_area(self, code: int, index: int):
        """Unlocks a previously locked shared memory area.
        """
        logger.debug(f"unlocking area code {code} index {index}")
        return self.library.Srv_UnlockArea(self.pointer, code, index)

    @error_wrap
    def lock_area(self, code: int, index: int):
        """Locks a shared memory area.
        """
        logger.debug(f"locking area code {code} index {index}")
        return self.library.Srv_LockArea(self.pointer, code, index)

    @error_wrap
    def start_to(self, ip: str, tcpport: int = 102):
        """
        start server on a specific interface.
        """
        if tcpport != 102:
            logger.info(f"setting server TCP port to {tcpport}")
            self.set_param(snap7.types.LocalPort, tcpport)
        if not re.match(ipv4, ip):
            raise ValueError(f"{ip} is invalid ipv4")
        logger.info(f"starting server to {ip}:102")
        return self.library.Srv_StartTo(self.pointer, ip)

    @error_wrap
    def set_param(self, number: int, value: int):
        """Sets an internal Server object parameter.
        """
        logger.debug(f"setting param number {number} to {value}")
        return self.library.Srv_SetParam(self.pointer, number,
                                         ctypes.byref(ctypes.c_int(value)))

    @error_wrap
    def set_mask(self, kind: int, mask: int):
        """Writes the specified filter mask.
        """
        logger.debug(f"setting mask kind {kind} to {mask}")
        return self.library.Srv_SetMask(self.pointer, kind, mask)

    @error_wrap
    def set_cpu_status(self, status: int):
        """Sets the Virtual CPU status.
        """
        if status not in snap7.types.cpu_statuses:
            raise ValueError(f"The cpu state ({status}) is invalid")
        logger.debug(f"setting cpu status to {status}")
        return self.library.Srv_SetCpuStatus(self.pointer, status)

    def pick_event(self) -> Optional[snap7.types.SrvEvent]:
        """Extracts an event (if available) from the Events queue.
        """
        logger.debug("checking event queue")
        event = snap7.types.SrvEvent()
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
        """
        logger.debug(f"retreiving param number {number}")
        value = ctypes.c_int()
        code = self.library.Srv_GetParam(self.pointer, number,
                                         ctypes.byref(value))
        check_error(code)
        return value.value

    def get_mask(self, kind: int) -> ctypes.c_uint32:
        """Reads the specified filter mask.
        """
        logger.debug(f"retrieving mask kind {kind}")
        mask = snap7.types.longword()
        code = self.library.Srv_GetMask(self.pointer, kind, ctypes.byref(mask))
        check_error(code)
        return mask

    @error_wrap
    def clear_events(self) -> int:
        """Empties the Event queue.
        """
        logger.debug("clearing event queue")
        return self.library.Srv_ClearEvents(self.pointer)


def mainloop(tcpport: int = 1102):
    server = snap7.server.Server()
    size = 100
    DBdata = (snap7.types.wordlen_to_ctypes[snap7.types.WordLen.Byte.value] * size)()
    PAdata = (snap7.types.wordlen_to_ctypes[snap7.types.WordLen.Byte.value] * size)()
    TMdata = (snap7.types.wordlen_to_ctypes[snap7.types.WordLen.Byte.value] * size)()
    CTdata = (snap7.types.wordlen_to_ctypes[snap7.types.WordLen.Byte.value] * size)()
    server.register_area(snap7.types.srvAreaDB, 1, DBdata)
    server.register_area(snap7.types.srvAreaPA, 1, PAdata)
    server.register_area(snap7.types.srvAreaTM, 1, TMdata)
    server.register_area(snap7.types.srvAreaCT, 1, CTdata)

    DBdata = (snap7.types.wordlen_to_ctypes[snap7.types.WordLen.Byte.value] * 2)
    db_data = [
        128*0 + 64*0 + 32*0 + 16*0 + 8*0 + 4*0 + 2*0 + 1,
        100,
    ]
    DBdata = DBdata(*db_data)
    server.register_area(snap7.types.srvAreaDB, 0, DBdata)


    server.start(tcpport=tcpport)
    while True:
        while True:
            event = server.pick_event()
            if event:
                logger.info(server.event_text(event))
            else:
                break
        time.sleep(1)
