"""
Snap7 async client used for connection to a siemens7 server.
"""
import asyncio
import logging
from ctypes import c_int, byref

from snap7.common import check_error
import snap7
from .client import Client
from .types import buffer_type, buffer_size

logger = logging.getLogger(__name__)


def error_wrap(func):
    """Parses a s7 error code returned the decorated function."""

    if asyncio.iscoroutinefunction(func):
        async def f(*args, **kw):
            code = await func(*args, **kw)
            check_error(code, context="client")

    else:
        def f(*args, **kw):
            code = func(*args, **kw)
            check_error(code, context="client")

    return f


class ClientAsync(Client):
    """
    This class expands the Client class with asyncio features for async s7comm requests.
    """

    def __init__(self):
        super().__init__()
        self.as_check = None

    async def wait_loop(self):
        """
        This loop checks if an answer received from an async request.
        :return:
        """
        temp = c_int(0)
        while Client.check_as_completion(self._pointer, byref(temp)):
            await asyncio.sleep(0)
