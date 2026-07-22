"""LegacyAuthenticationScheme — pre-TLS session authentication.

Entry point for S7CommPlus V1 session-key handshake on PLCs with
firmware < 4.5. Builds the 180-byte SecurityKeyEncryptedKey blob and
derives the 24-byte session key used for packet integrity (HMAC).

Manual port of ``HarpoS7.Auth.LegacyAuthenticationScheme``.
"""

from __future__ import annotations

from .blob_metadata import ENCRYPTED_BLOB_LENGTH_REAL_PLC
from .family0.authenticator import RealPlcAuthenticator
from .key_derivation import derive_session_key
from .keys import KeyFamily


def authenticate_real_plc(
    challenge: bytes,
    public_key: bytes,
    key_family: KeyFamily,
) -> tuple[bytes, bytes]:
    """Build the encrypted blob and derive the session key.

    Args:
        challenge: 20-byte PLC challenge from the CreateObject response.
        public_key: 40-byte PLC public key.
        key_family: KeyFamily.S7_1200 or KeyFamily.S7_1500.

    Returns:
        (encrypted_blob, session_key) — 180-byte blob and 24-byte key.
    """
    if key_family not in (KeyFamily.S7_1200, KeyFamily.S7_1500):
        raise ValueError(f"Only S7_1200 and S7_1500 families are supported, got {key_family.name}")

    blob = bytearray(ENCRYPTED_BLOB_LENGTH_REAL_PLC)
    bv = memoryview(blob)

    auth = RealPlcAuthenticator()
    offset = auth.write_metadata(bv, public_key, key_family)
    offset += auth.write_seed(bv[offset:], public_key)
    offset += auth.encrypt_full_blocks(bv[offset:], challenge)
    auth.encrypt_final_block(bv[offset:])

    key2 = auth.extract_key2()
    session_key = derive_session_key(key2, challenge)

    return bytes(blob), session_key
