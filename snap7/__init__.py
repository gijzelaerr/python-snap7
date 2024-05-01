"""
The Snap7 Python library.
"""

from importlib.metadata import version, PackageNotFoundError

from . import client
from . import common
from . import error
from . import logo
from . import server
from . import types
from . import util

__all__ = ["client", "common", "error", "logo", "server", "types", "util"]

try:
    __version__ = version("python-snap7")
except PackageNotFoundError:
    __version__ = "0.0rc0"
