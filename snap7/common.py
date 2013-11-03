from ctypes import c_char
from ctypes import cdll
from ctypes.util import find_library
import logging

logger = logging.getLogger(__name__)

ipv4 = "^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])$"


def load_lib():
    lib_location = find_library('snap7')
    if not lib_location:
        msg = "can't find snap7 library. If installed, try running ldconfig"
        raise Exception(msg)
    return cdll.LoadLibrary(lib_location)

clib = load_lib()

def check_error(code, context="client"):
    if code:
        error = error_text(code, context)
        logger.error(error)
        raise Exception(error)


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
    if context == "client":
        clib.Cli_ErrorText(error, text, len_)
    elif context == "server":
        clib.Srv_ErrorText(error, text, len_)
    elif context == "partner":
        clib.Par_ErrorText(error, text, len_)
    return text.value