"""Shared low-level helpers used across the session-auth subpackage.

Ported from HarpoS7 (MIT) — specifically ``HarpoS7.Utilities.Extensions.KeyExtensions``.
"""

from __future__ import annotations

import hashlib

# The fingerprint Siemens uses to identify a public or symmetric key.
# Length matches the publickeychecksum / symmetrickeychecksum fields in
# the SecurityKeyEncryptedKey blob (see Wireshark s7comm-plus dissector).
KEY_ID_LENGTH = 8

_KEY_PART_LENGTH = 24
_DERIVE_KEY_ID_MAGIC = b"DERIVE"


def derive_key_id(key: bytes) -> bytes:
    """Compute the 8-byte key fingerprint used in the encrypted key blob.

    HarpoS7 calls this ``DeriveKeyId``. It is SHA-256 over the first 24
    bytes of the key concatenated with the literal ASCII string
    ``"DERIVE"``, truncated to the first 8 bytes of the digest.

    Args:
        key: At least 24 bytes of key material — a public key or a
            session symmetric key. Only the leading 24 bytes are used;
            longer keys are silently truncated, matching upstream.

    Returns:
        8 bytes. Read as a little-endian uint64, this equals the value
        the PLC advertises in its ``ObjectVariableTypeName`` attribute
        (id 233) for that key.

    Raises:
        ValueError: If the key is shorter than 24 bytes.
    """
    if len(key) < _KEY_PART_LENGTH:
        raise ValueError(f"key must be at least {_KEY_PART_LENGTH} bytes, got {len(key)}")
    digest = hashlib.sha256(key[:_KEY_PART_LENGTH] + _DERIVE_KEY_ID_MAGIC).digest()
    return digest[:KEY_ID_LENGTH]
