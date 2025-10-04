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

# Native Python client (no external dependencies)
try:
    from .low_level.s7_client import S7Client as NativeClient
    _native_available = True
except ImportError:
    NativeClient = None
    _native_available = False

__all__ = ["Client", "Server", "Logo", "Partner", "Row", "DB", "Area", "Block", "WordLen", "SrvEvent", "SrvArea"]

# Add native client to exports if available
if _native_available:
    __all__.append("NativeClient")

try:
    __version__ = version("python-snap7")
except PackageNotFoundError:
    __version__ = "0.0rc0"
