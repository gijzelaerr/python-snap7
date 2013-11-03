import ctypes
import logging
import re
from snap7.common import clib, check_error, ipv4
from snap7.types import S7Object

logger = logging.getLogger(__name__)

def error_wrap(func):
    """Parses a s7 error code returned the decorated function."""
    def f(*args, **kw):
        code = func(*args, **kw)
        check_error(code, context="partner")
    return f

class Partner(object):
    def __init__(self, active=False):
        self.pointer = self.create(active)

    def as_b_send(self):
        return clib.Par_AsBSend(self.pointer)

    def b_recv(self):
        return clib.Par_BRecv(self.pointer)

    def b_send(self):
        return clib.Par_BSend(self.pointer)

    def check_as_b_recv_completion(self):
        return clib.Par_CheckAsBRecvCompletion(self.pointer)

    def check_as_b_send_completion(self):
        """
        Checks if the current asynchronous send job was completed and terminates
        immediately.
        """
        op_result = ctypes.c_int32()
        result = clib.Par_CheckAsBSendCompletion(self.pointer,
                                                 ctypes.byref(op_result))
        return_values = {
            0: "job complete",
            1: "job in progress",
            -2: "invalid handled supplied",
        }
        return return_values[result], op_result

    def create(self, active=False):
        """
        Creates a Partner and returns its handle, which is the reference that
        you have to use every time you refer to that Partner.
        :param active: 0
        :returns: a pointer to the partner object
        """
        return S7Object(clib.Par_Create(int(active)))

    def destroy(self):
        return clib.Par_Destroy(ctypes.byref(self.pointer))

    def get_last_error(self):
        error = ctypes.c_int32()
        result = clib.Par_GetLastError(self.pointer, ctypes.byref(error))
        check_error(result, "partner")
        return error

    def get_param(self):
        return clib.Par_GetParam(self.pointer)

    def get_stats(self):
        """
        Returns some statistics.

        :returns: a tuple containing bytes send, received, send errors, recv errors
        """
        sent = ctypes.c_uint32()
        recv = ctypes.c_uint32()
        send_errors = ctypes.c_uint32()
        recv_errors = ctypes.c_uint32()
        result = clib.Par_GetStats(self.pointer, ctypes.byref(sent),
                                   ctypes.byref(recv),
                                   ctypes.byref(send_errors),
                                   ctypes.byref(recv_errors))
        check_error(result, "partner")
        return sent, recv, send_errors, recv_errors

    def get_status(self):
        """
        Returns the Partner status.
        """
        status = ctypes.c_int32()
        result = clib.Par_GetStatus(self.pointer, ctypes.byref(status))
        check_error(result, "partner")
        return status

    def get_times(self):
        """
        Returns the last send and recv jobs execution time in milliseconds.
        """
        send_time = ctypes.c_int32()
        recv_time = ctypes.c_int32()
        result = clib.Par_GetTimes(self.pointer, ctypes.byref(send_time),
                                   ctypes.byref(recv_time))
        check_error(result, "partner")
        return send_time, recv_time

    def set_param(self):
        return clib.Par_SetParam(self.pointer)

    def set_recv_callback(self):
        return clib.Par_SetRecvCallback(self.pointer)

    def set_send_callback(self):
        return clib.Par_SetSendCallback(self.pointer)

    @error_wrap
    def start(self):
        return clib.Par_Start(self.pointer)

    @error_wrap
    def start_to(self, ip):
        assert re.match(ipv4, ip), '%s is invalid ipv4' % ip
        logger.info("starting server to %s:102" % ip)
        return clib.Par_Start(self.pointer, ip)

    def stop(self):
        return clib.Par_Stop(self.pointer)

    def wait_as_b_send_completion(self):
        return clib.Par_WaitAsBSendCompletion(self.pointer)
