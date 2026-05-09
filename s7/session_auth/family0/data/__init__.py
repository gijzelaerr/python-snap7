"""Vendored binary data tables used by the Family-0 transforms.

The two ``.bin`` files in this package are extracted verbatim from
HarpoS7's MIT-licensed sources:

- ``transform12_metadata.bin`` — ``HarpoS7.Family0.Data.Blobs.Transform12Metadata.bin``
  (243,625 bytes). Driver tape for the ``Transform12.Execute`` opcode loop.
- ``transform12_big_int_data.bin`` — extracted from
  ``HarpoS7.Family0.Data.Transform12Data.BigIntData`` (18,432 bytes).
  Auxiliary big-integer constants the Transform12 dispatcher refers
  to when its address indices land at >= ``0x100``.
"""

from __future__ import annotations

from importlib.resources import files
from typing import Final

_RESOURCE_BASE = files(__name__)

#: Driver tape for ``transform12.execute``. Each 4-byte little-endian
#: word selects an opcode (Add/Sub/Mul/Square), an output index, and
#: two input indices.
TRANSFORM12_METADATA: Final[bytes] = (_RESOURCE_BASE / "transform12_metadata.bin").read_bytes()

#: Auxiliary big-integer constants referenced by ``transform12.execute``
#: when its source indices are ``>= 0x100``. Values are 6-uint32
#: little-endian groups (24 bytes each).
TRANSFORM12_BIG_INT_DATA: Final[bytes] = (_RESOURCE_BASE / "transform12_big_int_data.bin").read_bytes()
