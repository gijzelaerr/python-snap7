"""SHA-256-based key derivation helpers used by the session-auth handshake.

These functions construct the various symmetric keys and IVs the
handshake feeds into AES-CTR. None of them reach into the proprietary
"monolith" transforms, so they're implementable in pure Python with
``hashlib`` alone.

Ported from HarpoS7 (MIT) — ``HarpoS7.Keys.KeyUtilities``. The
``DeriveSessionKey`` helper from that file is intentionally **not**
ported here: it depends on ``HarpoFingerprint.FingerprintChallenge``,
which is part of the Family-0 transforms and arrives in a later slice.
"""

from __future__ import annotations

import hashlib
import struct


def derive_challenge_encryption_key(random_key: bytes) -> bytes:
    """Build the 16-byte AES-128 key used to encrypt the PLC challenge.

    Layout: ``SHA-256(random_key[:24] || 0x04030201 0x08070605 0x0C0B0A09 0x000F0E0D)[:16]``,
    where each constant is a little-endian uint32 (so the magic block
    on the wire is ``01 02 03 04 05 06 07 08 09 0A 0B 0C 0D 0E 0F 00``).

    Args:
        random_key: 24-byte symmetric key generated client-side.

    Returns:
        16 bytes — the AES-128 key for challenge encryption.

    Raises:
        ValueError: If ``random_key`` is shorter than 24 bytes.
    """
    if len(random_key) < 24:
        raise ValueError(f"random_key must be at least 24 bytes, got {len(random_key)}")

    magic = struct.pack("<IIII", 0x04030201, 0x08070605, 0x0C0B0A09, 0x000F0E0D)
    return hashlib.sha256(random_key[:24] + magic).digest()[:16]


def derive_seed_encryption_key_and_iv(a2: bytes, a3: bytes) -> bytes:
    """Build a 32-byte AES-256 key + 16-byte IV (48 bytes total) for
    encrypting the random seed.

    The KDF is a simple counter-mode SHA-256 chain:
    ``digest_n = SHA-256(reverse(a2[:32]) || a3[:64] || counter_byte)``,
    iterated with counter ∈ {0, 32}, taking the first 32 / 16 bytes
    respectively for a total of 48 bytes.

    Args:
        a2: At least 32 bytes — output of the second seed-function call
            (named ``SeedFunction2`` upstream).
        a3: At least 64 bytes — reverse of the first ``SeedFunction2`` output.

    Returns:
        48 bytes: a 32-byte AES key followed by a 16-byte IV.

    Raises:
        ValueError: If either input is too short.
    """
    if len(a2) < 32:
        raise ValueError(f"a2 must be at least 32 bytes, got {len(a2)}")
    if len(a3) < 64:
        raise ValueError(f"a3 must be at least 64 bytes, got {len(a3)}")

    a2_reversed = a2[:32][::-1]
    a3_prefix = a3[:64]

    out = bytearray(48)
    offset = 0
    while offset < 48:
        buf = a2_reversed + a3_prefix + bytes([offset])
        digest = hashlib.sha256(buf).digest()
        size = min(0x30 - offset, 0x20)
        out[offset : offset + size] = digest[:size]
        offset += 0x20
    return bytes(out)


def derive_legitimation_challenge_key(session_key: bytes) -> bytes:
    """Build the 24-byte key used to encrypt the legitimation challenge
    (password authentication after session establishment).

    Layout: ``SHA-256(session_key[:24] || b"MISTRUST")[4:28]``.

    Args:
        session_key: 24-byte session key derived from the handshake.

    Returns:
        24 bytes — the legitimation challenge key.

    Raises:
        ValueError: If ``session_key`` is shorter than 24 bytes.
    """
    if len(session_key) < 24:
        raise ValueError(f"session_key must be at least 24 bytes, got {len(session_key)}")

    digest = hashlib.sha256(session_key[:24] + b"MISTRUST").digest()
    return digest[4:28]
