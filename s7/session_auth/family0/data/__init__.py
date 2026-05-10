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

#: 192-uint constant table used by ``PreSeedTransform`` as the initial
#: work buffer fed to Monolith9.
TRANSFORM1_DATA: Final[bytes] = (_RESOURCE_BASE / "transform1_data.bin").read_bytes()

#: 36-uint constant table shared between ``KeyDerivationTransform``
#: and ``Transform13``. Inlined from HarpoS7.Family0.Data.SharedData.
SHARED_DATA: Final[bytes] = bytes.fromhex(
    "fd6488bc75b9fcef143f43f07a40b620448635e0ef060861dcce60c6d5c678ff"
    "e14aaf01db8fe8c5f6930d7c51bae22af18edfcb691eeaf51a1dc0c1eb2fc5f4"
    "de24a7562160f3adaf17da5abae26d18dad82ec3a1ec919dbd0a2f53107b6c03"
    "34f907dc284e8912d141e2430e3952421a8ee9087bc9a6f31535dffc1cc66932"
    "74c43a478240dd1b9ee26b59fbed3087"
)

#: 256-byte constant table for Transform7.
TRANSFORM7_DATA: Final[bytes] = (_RESOURCE_BASE / "transform7_data.bin").read_bytes()

#: 498-int index tape for Transform7's Transform12 dispatch.
TRANSFORM7_INDEXES: Final[bytes] = (_RESOURCE_BASE / "transform7_indexes.bin").read_bytes()

#: 498-int count tape for Transform7's Transform12 dispatch.
TRANSFORM7_COUNTS: Final[bytes] = (_RESOURCE_BASE / "transform7_counts.bin").read_bytes()

# -- Fingerprint data tables --

#: Initial 47-uint32 big context for HarpoFingerprint.
FP_BIG_CONTEXT_INIT: Final[bytes] = (_RESOURCE_BASE / "fp_big_context_init.bin").read_bytes()

#: 20 uint32 XOR magic values for fingerprint sub-procedure.
FP_XOR_MAGIC: Final[bytes] = (_RESOURCE_BASE / "fp_xor_magic.bin").read_bytes()

#: Data1Collection: 20 variable-length ushort arrays (header + data).
FP_DATA1: Final[bytes] = (_RESOURCE_BASE / "fp_data1.bin").read_bytes()

#: Data2Collection: 20 variable-length ushort arrays (header + data).
FP_DATA2: Final[bytes] = (_RESOURCE_BASE / "fp_data2.bin").read_bytes()

#: Context mutations: 20 operation lists for ContextMutator.
FP_MUTATIONS: Final[bytes] = (_RESOURCE_BASE / "fp_mutations.bin").read_bytes()
