"""
The snap7 package (legacy).

Pure Python implementation of the classic S7 protocol for communicating with
Siemens S7 PLCs. This package is kept for backwards compatibility. For new
projects, use the ``s7`` package instead, which supports all PLC models and
automatically selects the best protocol (S7CommPlus or legacy S7)::

    from s7 import Client

    client = Client()
    client.connect("192.168.1.10", 0, 1)
    data = client.db_read(1, 0, 4)
"""

from importlib.metadata import version, PackageNotFoundError

from .client import Client
from .async_client import AsyncClient
from .server import Server
from .partner import Partner
from .logo import Logo
from .util.db import Row, DB
from .tags import Tag, load_csv, load_json, load_tia_xml
from .type import Area, Block, WordLen, SrvEvent, SrvArea

__all__ = [
    "Client",
    "AsyncClient",
    "Server",
    "Partner",
    "Logo",
    "Row",
    "DB",
    "Tag",
    "load_csv",
    "load_json",
    "load_tia_xml",
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
