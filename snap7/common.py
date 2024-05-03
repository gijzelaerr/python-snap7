import sys
import logging
import pathlib
import platform
from pathlib import Path
from ctypes import c_char
from typing import Any, Literal, Optional
from ctypes.util import find_library
from functools import cache

if platform.system() == "Windows":
    from ctypes import windll as cdll  # type: ignore
else:
    from ctypes import cdll

logger = logging.getLogger(__name__)

# regexp for checking if an ipv4 address is valid.
ipv4 = r"^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])$"


def _raise_error():
    error = f"""can't find snap7 shared library.

This probably means you are installing python-snap7 from source. When no binary wheel is found for you architecture, pip
install falls back on a source install. For this to work, you need to manually install the snap7 library, which python-snap7
uses under the hood.

The shortest path to success is to try to get a binary wheel working. Probably you are running on an unsupported
platform or python version. You are running:

machine: {platform.machine()}
system: {platform.system()}
python version: {platform.python_version()}
"""
    logger.error(error)
    raise RuntimeError(error)


def _find_locally(fname: str = "snap7") -> Optional[str]:
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


def _find_in_package() -> Optional[str]:
    """Find the `snap7.dll` file according to the os used.

    Returns:
        Full path to the `snap7.dll` file.
    """
    basedir = pathlib.Path(__file__).parent.absolute()
    if sys.platform == "darwin":
        lib = "libsnap7.dylib"
    elif sys.platform == "win32":
        lib = "snap7.dll"
    else:
        lib = "libsnap7.so"
    full_path = basedir.joinpath("lib", lib)
    if Path.exists(full_path) and Path.is_file(full_path):
        return str(full_path)
    return None


@cache
def load_library(lib_location: Optional[str] = None) -> Any:
    """Loads the `snap7.dll` library.
    Returns:
        cdll: a ctypes cdll object with the snap7 shared library loaded.
    """
    if not lib_location:
        lib_location = _find_in_package() or find_library("snap7") or _find_locally("snap7")

    if not lib_location:
        _raise_error()

    return cdll.LoadLibrary(lib_location)


Context = Literal["client", "server", "partner"]


@cache
def check_error(code: int, context: Context = "client") -> None:
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


def error_text(error, context: Context = "client") -> bytes:
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
    map_ = {"client": library.Cli_ErrorText, "server": library.Srv_ErrorText, "partner": library.Par_ErrorText}
    map_[context](error, text, len_)
    return text.value
