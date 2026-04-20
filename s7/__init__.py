"""Unified S7 communication library.

Provides protocol-agnostic access to Siemens S7 PLCs with automatic
protocol discovery (S7CommPlus vs legacy S7).

Usage::

    from s7 import Client

    client = Client()
    client.connect("192.168.1.10", 0, 1)
    data = client.db_read(1, 0, 4)
"""

from .client import Client
from .async_client import AsyncClient
from .server import Server
from .partner import Partner, PartnerStatus
from ._protocol import Protocol

from snap7.type import Area, Block, WordLen, SrvEvent, SrvArea
from snap7.util.db import Row, DB
from snap7.tags import Tag, load_csv, load_json, load_tia_xml, from_browse

__all__ = [
    "Client",
    "AsyncClient",
    "Server",
    "Partner",
    "PartnerStatus",
    "Protocol",
    "Area",
    "Block",
    "WordLen",
    "SrvEvent",
    "SrvArea",
    "Row",
    "DB",
    "Tag",
    "load_csv",
    "load_json",
    "load_tia_xml",
    "from_browse",
]
