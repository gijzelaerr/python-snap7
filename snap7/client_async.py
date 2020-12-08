"""
Snap7 async client used for connection to a siemens7 server.
"""
import asyncio
import logging
from ctypes import byref

from snap7.common import check_error
from .client import Client

logger = logging.getLogger(__name__)


def error_wrap(func):
    """Parses a s7 error code returned the decorated function."""
    async def f(*args, **kw):
        code = await func(*args, **kw)
        check_error(code, context="client")

    return f


class ClientAsync(Client):
    """
    This class expands the Client class with asyncio features for async s7comm requests.
    """

    def __init__(self):
        super().__init__()
        self.as_check = None

    async def wait_loop(self, operation):
        """
        This loop checks if an answer received from an async request.
        :return:
        """
        while self.check_as_completion(byref(operation)):
            await asyncio.sleep(0)
