"""
The Snap7 Python library.

Pure Python implementation of the S7 protocol for communicating with
Siemens S7 PLCs without requiring the native Snap7 C library.
"""

from importlib.metadata import version, PackageNotFoundError

from .client import Client
from .server import Server
from .partner import Partner
from .logo import Logo
from .util.db import Row, DB
from .type import Area, Block, WordLen, SrvEvent, SrvArea

__all__ = [
    "Client",
    "Server",
    "Partner",
    "Logo",
    "Row",
    "DB",
    "Area",
    "Block",
    "WordLen",
    "SrvEvent",
    "SrvArea",
]

try:
    __version__ = version("python-snap7")
except PackageNotFoundError:
    __version__ = "0.0rc0"
