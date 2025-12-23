"""
The Snap7 Python library.
"""

from importlib.metadata import version, PackageNotFoundError

from .client import Client
from snap7.clib.client import ClibClient
from .server import Server
from snap7.clib.server import ClibServer
from .logo import Logo
from .partner import Partner
from snap7.clib.partner import ClibPartner
from .util.db import Row, DB
from .type import Area, Block, WordLen, SrvEvent, SrvArea

# Pure Python implementations
try:
    from .native.wire_client import WireClient as PureClient
    from snap7.native.server import Server as PureServer
    from snap7.native.partner import Partner as PurePartner
    _PURE_PYTHON_AVAILABLE = True
except ImportError:
    _PURE_PYTHON_AVAILABLE = False
    PureClient = None  # type: ignore
    PureServer = None  # type: ignore
    PurePartner = None  # type: ignore

__all__ = [
    "Client",
    "ClibClient",
    "Server",
    "ClibServer",
    "Logo",
    "Partner",
    "ClibPartner",
    "Row",
    "DB",
    "Area",
    "Block",
    "WordLen",
    "SrvEvent",
    "SrvArea",
]

# Add pure Python implementations to exports if available
if _PURE_PYTHON_AVAILABLE:
    __all__.extend(["PureClient", "PureServer", "PurePartner"])

try:
    __version__ = version("python-snap7")
except PackageNotFoundError:
    __version__ = "0.0rc0"
