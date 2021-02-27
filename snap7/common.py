import logging
import platform
from ctypes import c_char
from ctypes.util import find_library
from typing import Optional

from snap7.exceptions import Snap7Exception

if platform.system() == 'Windows':
    from ctypes import windll as cdll  # type: ignore
else:
    from ctypes import cdll

logger = logging.getLogger(__name__)

# regexp for checking if an ipv4 address is valid.
ipv4 = r"^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])$"


class ADict(dict):
    """
    Accessing dict keys like an attribute.
    """
    __getattr__ = dict.__getitem__
    __setattr__ = dict.__setitem__


class Snap7Library:
    """
    Snap7 loader and encapsulator. We make this a singleton to make
    sure the library is loaded only once.
    """
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = object.__new__(cls)
            cls._instance.lib_location = None
            cls._instance.cdll = None
        return cls._instance

    def __init__(self, lib_location: Optional[str] = None):
        if self.cdll:
            return
        self.lib_location = lib_location or self.lib_location or find_library('snap7')
        if not self.lib_location:
            msg = "can't find snap7 library. If installed, try running ldconfig"
            raise Snap7Exception(msg)
        self.cdll = cdll.LoadLibrary(self.lib_location)


def load_library(lib_location: Optional[str] = None):
    """
    :returns: a ctypes cdll object with the snap7 shared library loaded.
    """
    return Snap7Library(lib_location).cdll


def check_error(code: int, context: str = "client"):
    """
    check if the error code is set. If so, a Python log message is generated
    and an error is raised.
    """
    if code and code != 1:
        error = error_text(code, context)
        logger.error(error)
        raise Snap7Exception(error)


def error_text(error, context: str = "client") -> bytes:
    """Returns a textual explanation of a given error number

    :param error: an error integer
    :param context: server, client or partner
    :returns: the error string
    """
    if context not in ("client", "server", "partner"):
        raise TypeError(f"Unkown context {context} used, should be either client, server or partner")
    logger.debug(f"error text for {hex(error)}")
    len_ = 1024
    text_type = c_char * len_
    text = text_type()
    library = load_library()
    if context == "client":
        library.Cli_ErrorText(error, text, len_)
    elif context == "server":
        library.Srv_ErrorText(error, text, len_)
    elif context == "partner":
        library.Par_ErrorText(error, text, len_)
    return text.value
