import ctypes
import logging
from loadlib import clib
from snap7.types import S7Object, time_t, longword, word
from snap7.error import error_parse

logger = logging.getLogger(__name__)

# Server Area ID  (use with Register/unregister - Lock/unlock Area)
srvAreaPE = 0
srvAreaPA = 1
srvAreaMK = 2
srvAreaCT = 3
srvAreaTM = 4
srvAreaDB = 5


server_statuses = {
    0: 'SrvStopped',
    1: 'SrvRunning',
    2: 'SrvError',
}

cpu_statuses = {
    0: 'S7CpuStatusUnknown',
    4: 'S7CpuStatusStop',
    8: 'S7CpuStatusRun',
}


class PSrvEvent(ctypes.Structure):
    _fields_ = [
        ('EvtTime', time_t),
        ('EvtSender', ctypes.c_int),
        ('EvtCode', longword),
        ('EvtRetCode', word),
        ('EvtParam1', word),
        ('EvtParam2', word),
        ('EvtParam3', word),
        ('EvtParam4', word),
    ]

    def __str__(self):
        return "time: %s sender: %s code: %s retcode: %s param1: %s param2:" \
               " %s param3: %s param4: %s " % (self.EvtTime, self.EvtSender,
                                               self.EvtCode, self.EvtRetCode,
                                               self.EvtParam1, self.EvtParam2,
                                               self.EvtParam3, self.EvtParam4)


def error_wrap(code):
    errors = error_parse(code, client=False)
    if errors:
        for error in errors:
            logging.error(error)
        raise Exception(", ".join(errors))

callback_wrap = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_void_p, PSrvEvent,
                                 ctypes.c_uint)


def error_text(error):
    """Returns a textual explanation of a given error number

    :param error: a error integer
    :returns: the erorr string
    """
    logger.info("error text for %s" % hex(error))
    len_ = 1024
    text_type = ctypes.c_char * len_
    text = text_type()
    clib.Srv_ErrorText(error, text, len_)
    return text.value


def event_text(event):
    """Returns a textual explanation of a given event object

    :param event: an PSrvEvent struct object
    :returns: the error string
    """
    logger.info("event text for %s" % hex(event.EvtCode))
    len_ = 1024
    text_type = ctypes.c_char * len_
    text = text_type()
    error_wrap(clib.Srv_EventText(ctypes.byref(event), ctypes.byref(text),
                                  len_))
    #int Srv_EventText(TSrvEvent *Event, char *Text, int TextLen);
    return text.value


class Server(object):
    def __init__(self):
        logger.info("creating server")
        self.pointer = S7Object(clib.Srv_Create())

    def register_area(self, area_code, index, userdata):
        """Shares a memory area with the server. That memory block will be
        visible by the clients.
        """
        logger.info("registering area")
        size = ctypes.sizeof(userdata)
        error_wrap(clib.Srv_RegisterArea(self.pointer, area_code, index,
                                         ctypes.byref(userdata), size))

    def set_events_callback(self, call_back):
        """Sets the user callback that the Server object has to call when an
        event is created.

        The expected callback is defined as:
        typedef void (S7API *pfn_SrvCallBack) (void * usrPtr, PSrvEvent PEvent,
        int Size);
        """
        logger.info("setting event callback")

        def wrap_func(usrptr, pevent, size):
            # TODO: call the callback function
            #call_back(pevent)
            logger.info("usrptr: %s, pevent: %s, size: %s" % (usrptr, pevent,
                                                              size))
            return 0

        error_wrap(clib.Srv_SetEventsCallback(self.pointer,
                                              callback_wrap(wrap_func)))

    def start(self):
        logger.info("starting server")
        error_wrap(clib.Srv_Start(self.pointer))


    def stop(self):
        logger.info("stopping server")
        error_wrap(clib.Srv_Stop(self.pointer))

    def destroy(self):
        logger.info("destroying server")
        return clib.Srv_Destroy(ctypes.byref(self.pointer))


    def get_status(self):
        """Reads the server status, the Virtual CPU status and the number of
        the clients connected.

        :returns: server status, cpu status, client count
        """
        logger.info("get server status")
        server_status = ctypes.c_int()
        cpu_status = ctypes.c_int()
        clients_count = ctypes.c_int()
        error_wrap(clib.Srv_GetStatus(self.pointer, ctypes.byref(server_status),
                                    ctypes.byref(cpu_status),
                                    ctypes.byref(clients_count)))
        return server_statuses[server_status.value],\
               cpu_statuses[cpu_status.value],\
               clients_count.value





"""
Srv_ClearEvents
Srv_EventText
Srv_GetMask
Srv_GetParam
Srv_GetStatus
Srv_LockArea
Srv_PickEvent
Srv_RegisterArea
Srv_SetCpuStatus
Srv_SetMask
Srv_SetParam
Srv_StartTo
Srv_UnlockArea
Srv_UnregisterArea
"""

