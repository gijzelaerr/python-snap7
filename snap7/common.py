from ctypes import c_char
from ctypes import cdll
from ctypes.util import find_library
import logging

logger = logging.getLogger(__name__)


def load_lib():
    lib_location = find_library('snap7')
    if not lib_location:
        msg = "can't find snap7 library. If installed, try running ldconfig"
        raise Exception(msg)
    return cdll.LoadLibrary(lib_location)

clib = load_lib()

def check_error(code, client=True):
    if code:
        error = error_text(code, client)
        logger.error(error)
        raise Exception(error)


def error_text(error, client):
    """Returns a textual explanation of a given error number

    :param error: an error integer
    :returns: the error string
    """
    logger.debug("error text for %s" % hex(error))
    len_ = 1024
    text_type = c_char * len_
    text = text_type()
    if client:
        clib.Cli_ErrorText(error, text, len_)
    else:
        clib.Srv_ErrorText(error, text, len_)
    return text.value