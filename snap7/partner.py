"""
Snap7 code for partnering with a siemens 7 server.

This allows you to create a S7 peer to peer communication. Unlike the
client-server model, where the client makes a request and the server replies to
it, the peer to peer model sees two components with same rights, each of them
can send data asynchronously. The only difference between them is the one who
is requesting the connection.
"""

import re
import logging
from ctypes import byref, c_int, c_int32, c_uint32, c_void_p
from typing import Optional, Tuple

from .common import ipv4, load_library
from .error import check_error, error_wrap
from .protocol import Snap7CliProtocol
from .type import S7Object, word, Parameter

logger = logging.getLogger(__name__)


class Partner:
    """
    A snap7 partner.
    """

    _pointer: c_void_p

    def __init__(self, active: bool = False):
        self._library: Snap7CliProtocol = load_library()
        self.create(active)

    def __del__(self) -> None:
        self.destroy()

    def as_b_send(self) -> int:
        """
        Sends a data packet to the partner. This function is asynchronous, i.e.
        it terminates immediately, a completion method is needed to know when
        the transfer is complete.
        """
        return self._library.Par_AsBSend(self._pointer)

    def b_recv(self) -> int:
        """
        Receives a data packet from the partner. This function is
        synchronous, it waits until a packet is received or the timeout
        supplied expires.
        """
        return self._library.Par_BRecv(self._pointer)

    def b_send(self) -> int:
        """
        Sends a data packet to the partner. This function is synchronous, i.e.
        it terminates when the transfer job (send+ack) is complete.
        """
        return self._library.Par_BSend(self._pointer)

    def check_as_b_recv_completion(self) -> int:
        """
        Checks if a packed received was received.
        """
        return self._library.Par_CheckAsBRecvCompletion(self._pointer)

    def check_as_b_send_completion(self) -> Tuple[str, c_int32]:
        """
        Checks if the current asynchronous send job was completed and terminates
        immediately.
        """
        op_result = c_int32()
        result = self._library.Par_CheckAsBSendCompletion(self._pointer, byref(op_result))
        return_values = {
            0: "job complete",
            1: "job in progress",
            -2: "invalid handled supplied",
        }

        if result == -2:
            raise ValueError("The Client parameter was invalid")

        return return_values[result], op_result

    def create(self, active: bool = False) -> None:
        """
        Creates a Partner and returns its handle, which is the reference that
        you have to use every time you refer to that Partner.

        :param active: 0
        :returns: a pointer to the partner object
        """
        self._library.Par_Create.restype = S7Object  # type: ignore[attr-defined]
        self._pointer = S7Object(self._library.Par_Create(int(active)))

    def destroy(self) -> Optional[int]:
        """
        Destroy a Partner of given handle.
        Before destruction the Partner is stopped, all clients disconnected and
        all shared memory blocks released.
        """
        if self._library:
            return self._library.Par_Destroy(byref(self._pointer))
        return None

    def get_last_error(self) -> c_int32:
        """
        Returns the last job result.
        """
        error = c_int32()
        result = self._library.Par_GetLastError(self._pointer, byref(error))
        check_error(result, "partner")
        return error

    def get_param(self, parameter: Parameter) -> int:
        """
        Reads an internal Partner object parameter.
        """
        logger.debug(f"retreiving param number {parameter}")
        value = parameter.ctype()
        code = self._library.Par_GetParam(self._pointer, c_int(parameter), byref(value))
        check_error(code)
        return value.value

    def get_stats(self) -> Tuple[c_uint32, c_uint32, c_uint32, c_uint32]:
        """
        Returns some statistics.

        :returns: a tuple containing bytes send, received, send errors, recv errors
        """
        sent = c_uint32()
        recv = c_uint32()
        send_errors = c_uint32()
        recv_errors = c_uint32()
        result = self._library.Par_GetStats(self._pointer, byref(sent), byref(recv), byref(send_errors), byref(recv_errors))
        check_error(result, "partner")
        return sent, recv, send_errors, recv_errors

    def get_status(self) -> c_int32:
        """
        Returns the Partner status.
        """
        status = c_int32()
        result = self._library.Par_GetStatus(self._pointer, byref(status))
        check_error(result, "partner")
        return status

    def get_times(self) -> Tuple[c_int32, c_int32]:
        """
        Returns the last send and recv jobs execution time in milliseconds.
        """
        send_time = c_int32()
        recv_time = c_int32()
        result = self._library.Par_GetTimes(self._pointer, byref(send_time), byref(recv_time))
        check_error(result, "partner")
        return send_time, recv_time

    @error_wrap(context="partner")
    def set_param(self, parameter: Parameter, value: int) -> int:
        """Sets an internal Partner object parameter."""
        logger.debug(f"setting param number {parameter} to {value}")
        return self._library.Par_SetParam(self._pointer, c_int(parameter), byref(c_int(value)))

    def set_recv_callback(self) -> int:
        """
        Sets the user callback that the Partner object has to call when a data
        packet is incoming.
        """
        return self._library.Par_SetRecvCallback(self._pointer)

    def set_send_callback(self) -> int:
        """
        Sets the user callback that the Partner object has to call when the
        asynchronous data sent is complete.
        """
        return self._library.Par_SetSendCallback(self._pointer)

    @error_wrap(context="partner")
    def start(self) -> int:
        """
        Starts the Partner and binds it to the specified IP address and the
        IsoTCP port.
        """
        return self._library.Par_Start(self._pointer)

    @error_wrap(context="partner")
    def start_to(self, local_ip: str, remote_ip: str, local_tsap: int, remote_tsap: int) -> int:
        """
        Starts the Partner and binds it to the specified IP address and the
        IsoTCP port.

        :param local_ip: PC host IPV4 Address. "0.0.0.0" is the default adapter
        :param remote_ip: PLC IPV4 Address
        :param local_tsap: Local TSAP
        :param remote_tsap: PLC TSAP
        """

        if not re.match(ipv4, local_ip):
            raise ValueError(f"{local_ip} is invalid ipv4")
        if not re.match(ipv4, remote_ip):
            raise ValueError(f"{remote_ip} is invalid ipv4")
        logger.info(f"starting partnering from {local_ip} to {remote_ip}")
        return self._library.Par_StartTo(
            self._pointer, local_ip.encode(), remote_ip.encode(), word(local_tsap), word(remote_tsap)
        )

    def stop(self) -> int:
        """
        Stops the Partner, disconnects gracefully the remote partner.
        """
        return self._library.Par_Stop(self._pointer)

    @error_wrap(context="partner")
    def wait_as_b_send_completion(self, timeout: int = 0) -> int:
        """
        Waits until the current asynchronous send job is done or the timeout
        expires.
        """
        return self._library.Par_WaitAsBSendCompletion(self._pointer, timeout)
