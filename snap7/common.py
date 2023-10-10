import sys
import logging
import pathlib
import platform
from pathlib import Path
from ctypes import c_char
from typing import Optional
from ctypes.util import find_library

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
    __setattr__ = dict.__setitem__  # type: ignore


class Snap7Library:
    """Snap7 loader and encapsulator. We make this a singleton to make
        sure the library is loaded only once.

    Attributes:
        lib_location: full path to the `snap7.dll` file. Optional.
    """
    _instance = None
    lib_location: Optional[str]

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = object.__new__(cls)
            cls._instance.lib_location = None
            cls._instance.cdll = None
        return cls._instance

    def __init__(self, lib_location: Optional[str] = None):
        """ Loads the snap7 library using ctypes cdll.

        Args:
            lib_location: full path to the `snap7.dll` file. Optional.

        Raises:
            RuntimeError: if `lib_location` is not found.
        """
        if self.cdll:  # type: ignore
            return
        self.lib_location = (lib_location
                             or self.lib_location
                             or find_in_package()
                             or find_library('snap7')
                             or find_locally('snap7'))
        if not self.lib_location:
            raise RuntimeError("can't find snap7 library. If installed, try running ldconfig")
        self.cdll = cdll.LoadLibrary(self.lib_location)


def load_library(lib_location: Optional[str] = None):
    """Loads the `snap7.dll` library.
    Returns:
        cdll: a ctypes cdll object with the snap7 shared library loaded.
    """
    return Snap7Library(lib_location).cdll


def check_error(code: int, context: str = "client") -> None:
    """Check if the error code is set. If so, a Python log message is generated
        and an error is raised.

    Args:
        code: error code number.
        context: context in which is called.

    Raises:
        RuntimeError: if the code exists and is different from 1.
    """
    if code and code != 1:
        error = error_text(code, context)
        logger.error(error)
        raise RuntimeError(error)


def error_text(error, context: str = "client") -> bytes:
    """Returns a textual explanation of a given error number

    Args:
        error: an error integer
        context: context in which is called from, server, client or partner

    Returns:
        The error.

    Raises:
        TypeError: if the context is not in `["client", "server", "partner"]`
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


def find_locally(fname: str = "snap7") -> Optional[str]:
    """Finds the `snap7.dll` file in the local project directory.

    Args:
        fname: file name to search for. Optional.

    Returns:
        Full path to the `snap7.dll` file.
    """
    file = pathlib.Path.cwd() / f"{fname}.dll"
    if file.exists():
        return str(file)
    return None


def find_in_package() -> Optional[str]:
    """Find the `snap7.dll` file according to the os used.

    Returns:
        Full path to the `snap7.dll` file.
    """
    basedir = pathlib.Path(__file__).parent.absolute()
    if sys.platform == "darwin":
        lib = 'libsnap7.dylib'
    elif sys.platform == "win32":
        lib = 'snap7.dll'
    else:
        lib = 'libsnap7.so'
    full_path = basedir.joinpath('lib', lib)
    if Path.exists(full_path) and Path.is_file(full_path):
        return str(full_path)
    return None
