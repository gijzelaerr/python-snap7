"""LegitimateScheme — solve the post-auth legitimation challenge.

After the SessionKey handshake, V1-initial PLCs require a second
cryptographic exchange before they unlock data operations. The PLC
sends a DEADBEEF-prefixed challenge blob; we solve it by running
a second RealPlcAuthenticator round with keys derived from the
session key and password hash.

Manual port of ``HarpoS7.Auth.LegitimateScheme``.
"""

from __future__ import annotations

import hashlib
import struct

from .family0.authenticator import RealPlcAuthenticator
from .key_derivation import derive_legitimation_challenge_key
from .keys import KeyFamily
from .utils import derive_key_id

DEADBEEF = 0xDEADBEEF
BEEF_FRAGMENT_METADATA_LENGTH = 12
BEEF_SEED_METADATA_LENGTH = 0x40
OUTPUT_BLOB_LENGTH_REAL_PLC = 180 + 68  # 248 bytes


def _write_fragment_metadata(buf: bytearray, offset: int, index: int, length: int) -> None:
    struct.pack_into("<III", buf, offset, DEADBEEF, index, length)


def _write_seed_beef_metadata(
    buf: bytearray,
    public_key: bytes,
    family: KeyFamily,
    symmetric_key: bytes,
) -> None:
    struct.pack_into("<I", buf, 0, DEADBEEF)

    seed_frag_len = BEEF_SEED_METADATA_LENGTH + 0x3C  # 60 = encrypted seed length for real PLCs
    struct.pack_into("<I", buf, 4, seed_frag_len)
    struct.pack_into("<I", buf, 8, 1)
    struct.pack_into("<I", buf, 12, 2)
    buf[0x15] = 0x04

    pub_key_id = derive_key_id(public_key)
    buf[0x1C : 0x1C + 8] = pub_key_id

    from .blob_metadata import get_public_key_flags

    struct.pack_into("<I", buf, 0x24, get_public_key_flags(family))
    struct.pack_into("<I", buf, 0x28, 0)

    sym_key_id = derive_key_id(symmetric_key)
    buf[0x2C : 0x2C + 8] = sym_key_id

    struct.pack_into("<I", buf, 0x34, 1)  # symmetric key flags for legitimation (always 1 for real PLCs)
    struct.pack_into("<I", buf, 0x38, 0)

    struct.pack_into("<I", buf, 0x3C, 0x3C)  # encrypted seed length


def solve_legitimate_challenge_real_plc(
    challenge: bytes,
    public_key: bytes,
    family: KeyFamily,
    session_key: bytes,
    password: str = "",
) -> bytes:
    password_hash = hashlib.sha1(password.encode("utf-8")).digest()

    challenge_key = derive_legitimation_challenge_key(session_key)

    key2 = password_hash + challenge[:20]

    blob = bytearray(OUTPUT_BLOB_LENGTH_REAL_PLC)

    _write_seed_beef_metadata(blob, public_key, family, challenge_key)

    offset = BEEF_SEED_METADATA_LENGTH
    auth = RealPlcAuthenticator(key1=challenge_key, key2=key2)
    offset += auth.write_seed(memoryview(blob)[offset:], public_key)

    _write_fragment_metadata(blob, offset, 0, 0x10 + 0x30)
    offset += BEEF_FRAGMENT_METADATA_LENGTH

    zero_challenge = bytes(20)
    offset += auth.encrypt_full_blocks(memoryview(blob)[offset:], zero_challenge)

    leftover = auth.key2_leftover_length
    _write_fragment_metadata(blob, offset, 1, leftover + 16)
    offset += BEEF_FRAGMENT_METADATA_LENGTH
    offset += auth.encrypt_final_block(memoryview(blob)[offset:])

    _write_fragment_metadata(blob, offset, 2, 0)

    return bytes(blob)
