"""
Snap7 async client used for connection to a siemens7 server.
"""
import asyncio
import logging
from abc import ABC
from ctypes import c_int, byref

from snap7.common import check_error
import snap7
from .client import Client
from .snap7types import buffer_type, buffer_size

logger = logging.getLogger(__name__)


def error_wrap(func):
    """Parses a s7 error code returned the decorated function."""

    def f(*args, **kw):
        code = func(*args, **kw)
        check_error(code, context="client")

    return f


class ClientAsync(Client, ABC):
    """
    This class expands the Client class with asyncio features for async s7comm requests.
    """

    def __init__(self):
        super().__init__()
        self.as_check = None

    def set_as_check_mode(self, mode):
        """
        This methods sets the mode how async answers shall be handled, like mentioned in snap7 docs:
        None - pass, like sync method without a receive check
        1 - Poll if result is available, otherwise do something else
        2 - wait_idle, do something else and then wait until an answer receives (not implemented, better use 1)
        3 - Callback a method/function if the answer receives (not implemented)
        :param mode: Mode how an async answer shall be handled
        :return:
        """
        if mode not in [None, 1, 2]:
            logger.warning(f"{mode} is not a legit mode. Has to be 1 or 2!")
            raise Warning("Invalid check mode selected for async client")
        self.as_check = mode
        logger.debug(f"Async check mode changed to {mode}")

    async def wait_loop(self):
        """
        This loop checks if an answer received from an async request.
        :return:
        """
        temp = c_int(0)
        while self._library.Cli_CheckAsCompletion(self._pointer, byref(temp)):
            await asyncio.sleep(0)

    async def as_db_read(self, db_number, start, size, timeout=1):
        """
        This is the asynchronous counterpart of Cli_DBRead with asyncio features.
        :returns: user buffer.
        """
        logger.debug(f"db_read, db_number:{db_number}, start:{start}, size:{size}")
        type_ = snap7.snap7types.wordlen_to_ctypes[snap7.snap7types.S7WLByte]
        data = (type_ * size)()
        result = (self._library.Cli_AsDBRead(self._pointer, db_number, start, size, byref(data)))
        check_error(result, context="client")
        if await self.as_check_and_wait(timeout) is False:
            return None
        return bytearray(data)

    async def as_db_write(self, db_number, start, data, timeout=1):
        """
        This is the asynchronous counterpart of Cli_DBWrite with asyncio features.
        """
        check = Client.as_db_write(self, db_number, start, data)
        if await self.as_check_and_wait(timeout) is False:
            return None
        return check

    async def as_ab_write(self, start, data, timeout=1):
        """
        This is the asynchronous counterpart of Cli_ABWrite with asyncio features.
        """
        check = Client.as_ab_write(self, start, data)
        if await self.as_check_and_wait(timeout) is False:
            return None
        return check

    async def as_ab_read(self, start, size, timeout=1):
        """
        This is the asynchronous counterpart of client.ab_read() with asyncio features.
        """
        wordlen = snap7.snap7types.S7WLByte
        type_ = snap7.snap7types.wordlen_to_ctypes[wordlen]
        data = (type_ * size)()
        logger.debug(f"ab_read: start: {start}: size {size}: ")
        result = self._library.Cli_AsABRead(self._pointer, start, size,
                                            byref(data))
        check_error(result, context="client")
        if await self.as_check_and_wait(timeout) is False:
            return None
        return bytearray(data)

    async def as_check_and_wait(self, timeout):
        """
        This method handles asynchronous asyncio requests, depending on their as_check mode.
        :param timeout: Max time the request is allowed to pending, until it will terminated.
        :return:
            - False - if Timeout happened
            - True - if request was made in time or with not implemented as_check mode
        """
        if self.as_check == 1:
            try:
                await asyncio.wait_for(self.wait_loop(), timeout)
            except asyncio.TimeoutError:
                logger.warning(f"A request was timeouted")
                return False
        elif self.as_check == 2 or self.as_check == 3:
            logger.warning("as_check mode 2 and 3 are not implemented, will continue without check")
            return True
        elif self.as_check is None:
            logger.warning("as_check is None. May containt false data - no async receive check is made")
            return True
        return True

    async def as_db_get(self, db_number, timeout=1):
        """
        This is the asynchronous counterpart of Cli_DBGet with asyncio features.
        """
        logger.debug(f"db_get db_number: {db_number}")
        _buffer = buffer_type()
        result = self._library.Cli_AsDBGet(self._pointer, db_number,
                                           byref(_buffer),
                                           byref(c_int(buffer_size)))
        check_error(result, context="client")
        if await self.as_check_and_wait(timeout) is False:
            return None
        return bytearray(_buffer)

    @error_wrap
    async def as_download(self, data, block_num=-1, timeout=1):
        """
        Downloads a DB data into the AG asynchronously.
        A whole block (including header and footer) must be available into the
        user buffer.

        :param timeout: Max time the request is allowed to pending, until it will terminated.
        :param block_num: New Block number (or -1)
        :param data: the user buffer
        """
        data = Client.as_download(self, data, block_num)
        if await self.as_check_and_wait(timeout) is False:
            return None
        return data

    async def as_read_area(self, area, dbnumber, start, size, timeout=1):
        """This is the main async function to read data from a PLC, made asycnio compatible.
        With it you can read DB, Inputs, Outputs, Merkers, Timers and Counters.

        :param timeout: max time waiting for response, 1 Second default
        :param area: chosen memory_area
        :param dbnumber: The DB number, only used when area= S7AreaDB
        :param start: offset to start writing
        :param size: number of units to read
        """
        wordlen, data = self._as_read_area_prepare(area, size)
        logger.debug(f"reading area: {area} dbnumber: {dbnumber} start: {start}: amount {size}: wordlen: {wordlen}")
        result = self._library.Cli_AsReadArea(self._pointer, area, dbnumber, start, size, wordlen, byref(data))
        check_error(result, context="client")
        if await self.as_check_and_wait(timeout) is False:
            return None
        return bytearray(data)

    async def as_write_area(self, area, dbnumber, start, data, timeout=1):
        """This is the main async function to write data into a PLC, made asycnio compatible. It's the
        complementary function of Cli_ReadArea(), the parameters and their
        meanings are the same. The only difference is that the data is
        transferred from the buffer pointed by pUsrData into PLC.

        :param timeout: max time waiting for response, 1 Second default
        :param area: chosen memory_area
        :param dbnumber: The DB number, only used when area= S7AreaDB
        :param start: offset to start writing
        :param data: a bytearray containing the payload
        """
        check = Client.as_write_area(self, area, dbnumber, start, data)
        if await self.as_check_and_wait(timeout) is False:
            return None
        return check
