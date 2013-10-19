import ctypes
import logging
import re
from decorator import decorator
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

ipv4 = "^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])$"


def check_error(code):
    errors = error_parse(code, client=False)
    if errors:
        for error in errors:
            logging.error(error)
        raise Exception(", ".join(errors))


def error_wrap(func):
    def f(func, *args, **kw):
        code = func(*args, **kw)
        check_error(code)
    return decorator(f, func)


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


class SrvEvent(ctypes.Structure):
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
        return "<event time: %s sender: %s code: %s retcode: %s param1: " \
               "%s param2:%s param3: %s param4: %s>" % (
                                                        self.EvtTime,
                                                        self.EvtSender,
                                                        self.EvtCode,
                                                        self.EvtRetCode,
                                                        self.EvtParam1,
                                                        self.EvtParam2,
                                                        self.EvtParam3,
                                                        self.EvtParam4)


CALLBACK = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_void_p,
                            ctypes.POINTER(SrvEvent), ctypes.c_uint)


def error_text(error):
    """Returns a textual explanation of a given error number

    :param error: a error integer
    :returns: the erorr string
    """
    logger.debug("error text for %s" % hex(error))
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
    logger.debug("error text for %s" % hex(event.EvtCode))
    len_ = 1024
    text_type = ctypes.c_char * len_
    text = text_type()
    error = clib.Srv_EventText(ctypes.byref(event), ctypes.byref(text), len_)
    check_error(error)
    return text.value


class Server(object):
    def __init__(self):
        logger.info("creating server")
        self.pointer = S7Object(clib.Srv_Create())
        #self._set_log_callback()

    @error_wrap
    def register_area(self, area_code, index, userdata):
        """Shares a memory area with the server. That memory block will be
        visible by the clients.
        """
        logger.info("registering area")
        size = ctypes.sizeof(userdata)
        return clib.Srv_RegisterArea(self.pointer, area_code, index,
                                     ctypes.byref(userdata), size)

    @error_wrap
    def set_events_callback(self, call_back):
        """Sets the user callback that the Server object has to call when an
        event is created.
        """
        logger.info("setting event callback")
        raise NotImplementedError
        def wrap_callback(usrptr, pevent, size):
            """ Wraps python function into a ctypes function
            :param usrptr: not used
            :param pevent: a snap7 event struct
            :param size:
            :returns: should return an int
            """
            # TODO: call the actual callback function. Somehow we can't access
            # objects in the scope of this object...
            logger.info("callback event: " + event_text(pevent.contents))
            return 0

        return clib.Srv_SetEventsCallback(self.pointer, CALLBACK(wrap_callback))

    @error_wrap
    def _set_log_callback(self):
        """Sets a callback that logs the events
        """
        logger.debug("setting up event logger")
        raise NotImplementedError
        def wrap_callback(usrptr, pevent, size):
            logger.info("callback event: " + event_text(pevent.contents))
            return 0
        return clib.Srv_SetEventsCallback(self.pointer, CALLBACK(wrap_callback))

    @error_wrap
    def start(self):
        logger.info("starting server on 0.0.0.0:102")
        return clib.Srv_Start(self.pointer)

    @error_wrap
    def stop(self):
        logger.info("stopping server")
        return clib.Srv_Stop(self.pointer)

    @error_wrap
    def destroy(self):
        logger.info("destroying server")
        return clib.Srv_Destroy(ctypes.byref(self.pointer))

    def get_status(self):
        """Reads the server status, the Virtual CPU status and the number of
        the clients connected.

        :returns: server status, cpu status, client count
        """
        logger.debug("get server status")
        server_status = ctypes.c_int()
        cpu_status = ctypes.c_int()
        clients_count = ctypes.c_int()
        error = (clib.Srv_GetStatus(self.pointer, ctypes.byref(server_status),
                                    ctypes.byref(cpu_status),
                                    ctypes.byref(clients_count)))
        check_error(error)
        logger.debug("status server %s cpu %s clients %s" % (server_status.value,
                     cpu_status.value, clients_count.value))
        return server_statuses[server_status.value],\
               cpu_statuses[cpu_status.value],\
               clients_count.value

    @error_wrap
    def unregister_area(self, area_code, index):
        """'Unshares' a memory area previously shared with Srv_RegisterArea().
        That memory block will be no longer visible by the clients.
        """
        return clib.Srv_UnregisterArea(self.pointer, area_code, index)

    @error_wrap
    def unlock_area(self,  code, index):
        """Unlocks a previously locked shared memory area.
        """
        logging.debug("unlocking area code %s index %s" % (code, index))
        return clib.Srv_UnlockArea(self.pointer, code, index)

    @error_wrap
    def lock_area(self,  code, index):
        """Locks a shared memory area.
        """
        logging.debug("locking area code %s index %s" % (code, index))
        return clib.Srv_UnlockArea(self.pointer, code, index)

    @error_wrap
    def start_to(self, ip):
        assert re.match(ipv4, ip), '%s is invalid ipv4' % ip
        logger.info("starting server to %s:102" % ip)
        return clib.Srv_Start(self.pointer, ip)

    @error_wrap
    def set_param(self, number, value):
        """Sets an internal Server object parameter.
        """
        logger.debug("setting param number %s to %s" % (number, value))
        return clib.Srv_SetParam(self.pointer, number,
                                 ctypes.byref(ctypes.c_int(value)))

    @error_wrap
    def set_mask(self, kind, mask):
        """Writes the specified filter mask.
        """
        logger.debug("setting mask kind %s to %s" % (kind, mask))
        return clib.Srv_SetMask(self.pointer, kind, mask)

    @error_wrap
    def set_cpu_status(self, status):
        """Sets the Virtual CPU status.
        """
        assert status in cpu_statuses, 'unknown cpu state %s' % status
        logger.debug("setting cpu status to %s" % status)
        return clib.Srv_SetCpuStatus(self.pointer, status)

    def pick_event(self):
        """Extracts an event (if available) from the Events queue.
        """
        logger.debug("checking event queue")
        event = SrvEvent()
        ready = ctypes.c_int32()
        code = clib.Srv_PickEvent(self.pointer, ctypes.byref(event),
                              ctypes.byref(ready))
        check_error(code)
        if ready:
            logger.debug("one event ready: %s" % event)
            return event
        logger.debug("no events ready")

    def get_param(self, number):
        """Reads an internal Server object parameter.

        int Srv_GetParam(S7Object Server, int ParamNumber, void *pValue);
        """
        logger.debug("retreiving param number %s" % number)
        value = ctypes.c_int()
        code = clib.Srv_GetParam(self.pointer, number, ctypes.byref(value))
        check_error(code)
        return value.value

    def get_mask(self, kind):
        """Reads the specified filter mask.
        """
        logger.debug("retrieving mask kind %s" % kind)
        mask = longword()
        code = clib.Srv_GetMask(self.pointer, kind, ctypes.byref(mask))
        check_error(code)
        return mask

    @error_wrap
    def clear_events(self):
        """Empties the Event queue.
        """
        logger.debug("clearing event queue")
        return clib.Srv_ClearEvents(self.pointer)
