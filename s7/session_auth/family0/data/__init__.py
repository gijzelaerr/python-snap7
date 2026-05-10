"""Vendored data tables used by the Family-0 transforms and fingerprint.

Small tables are inlined as Python literals in ``_constants.py``.
Large tables (transform12 opcode tape 244K, big-int auxiliary 18K,
fingerprint data1 3K, fingerprint data2 64K) remain as ``.bin`` files.

All data originates from HarpoS7's MIT-licensed reverse engineering
of Siemens' ``OMSp_core_managed.dll``.
"""

from __future__ import annotations

import struct

from importlib.resources import files
from typing import Final

from ._constants import (
    FP_BIG_CONTEXT_INIT_INTS,
    FP_MUTATIONS,
    FP_XOR_MAGIC_INTS,
    TRANSFORM1_DATA_INTS,
    TRANSFORM7_COUNTS_INTS,
    TRANSFORM7_DATA_HEX,
    TRANSFORM7_INDEXES_INTS,
)

_RESOURCE_BASE = files(__name__)

# -- Large binary tables (too big to inline) --

#: Driver tape for ``transform12.execute``. Each 4-byte little-endian
#: word selects an opcode (Add/Sub/Mul/Square), an output index, and
#: two input indices. 60,906 entries = 243,625 bytes.
TRANSFORM12_METADATA: Final[bytes] = (_RESOURCE_BASE / "transform12_metadata.bin").read_bytes()

#: Auxiliary big-integer constants referenced by ``transform12.execute``
#: when its source indices are ``>= 0x100``. 768 groups of 24 bytes.
TRANSFORM12_BIG_INT_DATA: Final[bytes] = (_RESOURCE_BASE / "transform12_big_int_data.bin").read_bytes()

#: Data1Collection: 20 variable-length ushort arrays (header + data).
#: Consumed in triples by the fingerprint sub-procedure.
FP_DATA1: Final[bytes] = (_RESOURCE_BASE / "fp_data1.bin").read_bytes()

#: Data2Collection: 20 variable-length ushort arrays (header + data).
#: Lookup tables consumed byte-by-byte during the sub-procedure.
FP_DATA2: Final[bytes] = (_RESOURCE_BASE / "fp_data2.bin").read_bytes()

# -- Inlined tables (from _constants.py) --

#: 192-uint constant table used by ``PreSeedTransform`` as the initial
#: work buffer fed to Monolith9.
TRANSFORM1_DATA: Final[bytes] = struct.pack(f"<{len(TRANSFORM1_DATA_INTS)}I", *TRANSFORM1_DATA_INTS)

#: 36-uint constant table shared between ``KeyDerivationTransform``
#: and ``Transform13``.
SHARED_DATA: Final[bytes] = bytes.fromhex(
    "fd6488bc75b9fcef143f43f07a40b620448635e0ef060861dcce60c6d5c678ff"
    "e14aaf01db8fe8c5f6930d7c51bae22af18edfcb691eeaf51a1dc0c1eb2fc5f4"
    "de24a7562160f3adaf17da5abae26d18dad82ec3a1ec919dbd0a2f53107b6c03"
    "34f907dc284e8912d141e2430e3952421a8ee9087bc9a6f31535dffc1cc66932"
    "74c43a478240dd1b9ee26b59fbed3087"
)

#: 256-byte constant table for Transform7 — ECC-like base point coordinates.
TRANSFORM7_DATA: Final[bytes] = bytes.fromhex(TRANSFORM7_DATA_HEX)

#: 498-int index tape for Transform7's Transform12 dispatch.
TRANSFORM7_INDEXES: Final[bytes] = struct.pack(f"<{len(TRANSFORM7_INDEXES_INTS)}i", *TRANSFORM7_INDEXES_INTS)

#: 498-int count tape for Transform7's Transform12 dispatch.
TRANSFORM7_COUNTS: Final[bytes] = struct.pack(f"<{len(TRANSFORM7_COUNTS_INTS)}i", *TRANSFORM7_COUNTS_INTS)

# -- Fingerprint tables (inlined from _constants.py) --

#: Initial 47-uint32 big context for HarpoFingerprint.
FP_BIG_CONTEXT_INIT: Final[bytes] = struct.pack(f"<{len(FP_BIG_CONTEXT_INIT_INTS)}I", *FP_BIG_CONTEXT_INIT_INTS)

#: 20 XOR magic values, one per fingerprint round.
FP_XOR_MAGIC: Final[bytes] = struct.pack(f"<{len(FP_XOR_MAGIC_INTS)}I", *FP_XOR_MAGIC_INTS)

# FP_MUTATIONS is re-exported directly from _constants (already a Python structure).
__all__ = [
    "FP_BIG_CONTEXT_INIT",
    "FP_DATA1",
    "FP_DATA2",
    "FP_MUTATIONS",
    "FP_XOR_MAGIC",
    "SHARED_DATA",
    "TRANSFORM1_DATA",
    "TRANSFORM12_BIG_INT_DATA",
    "TRANSFORM12_METADATA",
    "TRANSFORM7_COUNTS",
    "TRANSFORM7_DATA",
    "TRANSFORM7_INDEXES",
]
