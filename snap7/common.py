from ctypes import c_char
from ctypes import cdll
from ctypes.util import find_library
import logging
from snap7.exceptions import Snap7Exception

logger = logging.getLogger(__name__)

# regexp for checking if an ipv4 address is valid.
ipv4 = "^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])$"


class Snap7Library(object):
    """
    Snap7 loader and encapsulator. We make this a singleton to make
    sure the library is loaded only once.
    """
    _instance = None
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(Snap7Library, cls).__new__(cls, *args,
                                                             **kwargs)
        return cls._instance

    def __init__(self):
        lib_location = find_library('snap7')
        if not lib_location:
            msg = "can't find snap7 library. If installed, try running ldconfig"
            raise Snap7Exception(msg)
        self.cdll = cdll.LoadLibrary(lib_location)


def load_library():
    """
    :returns: a ctypes cdll object iwth the snap7 shared library loaded.
    """
    return Snap7Library().cdll


def check_error(code, context="client"):
    """
    check if the error code is set. If so, a Python log message is generated
    and an error is raised.
    """
    if code:
        error = error_text(code, context)
        logger.error(error)
        raise Snap7Exception(error)


def error_text(error, context="client"):
    """Returns a textual explanation of a given error number

    :param error: an error integer
    :param context: server, client or partner
    :returns: the error string
    """
    assert context in ("client", "server", "partner")
    logger.debug("error text for %s" % hex(error))
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