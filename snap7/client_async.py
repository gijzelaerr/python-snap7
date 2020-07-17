"""
Snap7 async client used for connection to a siemens7 server.
"""
from ctypes import c_int, byref

import logging
import asyncio

import snap7
from snap7.common import check_error
from .client import Client

logger = logging.getLogger(__name__)


class ClientAsync(Client):
    """
    This class expands the Client class with asyncio features for async s7comm requests.
    """
    def __init__(self):
        super().__init__()
        self.as_check = None

    def set_as_check_mode(self, mode):
        """
        This methods sets the mode how async answers shall be handled, like mentioned in snap7 docs:
        None - pass, like sync method
        1 - Poll if result is available, otherwise do something else
        2 - wait_idle, do something else and then wait until an answer receives (not implemented, better use 1)
        3 - Callback a method/function if the answer receives (not implemented)
        :param mode: Mode how an async answer shall be handled
        :return:
        """
        if mode not in [None, 1, 2, 3]:
            logger.warning(f"{mode} is not a legit mode. Has to be None, 1, 2 or 3")
        else:
            self.as_check = mode
            logger.debug(f"Async check mode changed to {mode}")

    async def async_wait_loop(self):
        """
        This loop checks if an answer received from an async request.
        :return:
        """
        temp = c_int(0)
        while self.library.Cli_CheckAsCompletion(self.pointer, byref(temp)):
            await asyncio.sleep(0)

    async def as_db_read(self, db_number, start, size, timeout=1):
        """
        This is the asynchronous counterpart of Cli_DBRead with asyncio features.
        :returns: user buffer.
        """
        logger.debug(f"db_read, db_number:{db_number}, start:{start}, size:{size}")

        type_ = snap7.snap7types.wordlen_to_ctypes[snap7.snap7types.S7WLByte]
        data = (type_ * size)()
        result = (self.library.Cli_AsDBRead(self.pointer, db_number, start, size, byref(data)))
        if self.as_check == 1:
            try:
                await asyncio.wait_for(self.async_wait_loop(), timeout)
            except asyncio.TimeoutError:
                logger.warning(f"Request timeouted - db_nummer:{db_number}, start:{start}, size:{size}")
                return None
        elif self.as_check == 2 or self.as_check == 3:
            logger.warning("Not implemented feature, will continue without check")
        check_error(result, context="client")
        return bytearray(data)
