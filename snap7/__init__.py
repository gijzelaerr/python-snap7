"""
The Snap7 Python library.
"""

from importlib.metadata import version, PackageNotFoundError

from .client import Client
from .server import Server
from .logo import Logo
from .partner import Partner
from .util.db import Row, DB
from .type import Area, Block, WordLen, SrvEvent, SrvArea

__all__ = ["Client", "Server", "Logo", "Partner", "Row", "DB", "Area", "Block", "WordLen", "SrvEvent", "SrvArea"]

try:
    __version__ = version("python-snap7")
except PackageNotFoundError:
    __version__ = "0.0rc0"
