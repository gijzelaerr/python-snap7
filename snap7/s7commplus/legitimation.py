"""S7CommPlus PLC password authentication (legitimation).

Supports two authentication modes:
- Legacy: SHA-1 password hash XORed with challenge (older firmware)
- New: AES-256-CBC encrypted credentials with TLS-derived key (newer firmware)

Firmware version determines which mode is used:
- S7-1500: FW >= 3.01 = new, FW 2.09-2.99 = legacy
- S7-1200: FW >= 4.07 = new, FW 4.03-4.06 = legacy

Note: The "new" mode requires the ``cryptography`` package for AES-256-CBC.
Install with ``pip install cryptography``. The legacy mode uses only stdlib.
"""

import hashlib
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def derive_legitimation_key(oms_secret: bytes) -> bytes:
    """Derive AES-256 key from TLS OMS exporter secret.

    Args:
        oms_secret: 32-byte OMS exporter secret from TLS session

    Returns:
        32-byte AES-256 key
    """
    return hashlib.sha256(oms_secret).digest()


def build_legacy_response(password: str, challenge: bytes) -> bytes:
    """Build legacy legitimation response (SHA-1 XOR).

    Args:
        password: PLC password
        challenge: 20-byte challenge from PLC

    Returns:
        Response bytes (SHA-1 hash XORed with challenge)
    """
    password_hash = hashlib.sha1(password.encode("utf-8")).digest()  # noqa: S324
    return bytes(a ^ b for a, b in zip(password_hash, challenge[:20]))


def build_new_response(
    password: str,
    challenge: bytes,
    oms_secret: bytes,
    username: str = "",
) -> bytes:
    """Build new legitimation response (AES-256-CBC encrypted).

    Requires the ``cryptography`` package.

    Args:
        password: PLC password
        challenge: Challenge from PLC (first 16 bytes used as IV)
        oms_secret: 32-byte OMS exporter secret
        username: Optional username (empty string for legacy-style new auth)

    Returns:
        AES-256-CBC encrypted response

    Raises:
        NotImplementedError: If ``cryptography`` is not installed
    """
    try:
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
        from cryptography.hazmat.primitives import padding
    except ImportError:
        raise NotImplementedError(
            "AES-256-CBC legitimation requires the 'cryptography' package. Install with: pip install python-snap7[s7commplus]"
        )

    key = derive_legitimation_key(oms_secret)
    iv = bytes(challenge[:16])

    payload = _build_legitimation_payload(password, username)

    padder = padding.PKCS7(128).padder()
    padded = padder.update(payload) + padder.finalize()

    cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
    encryptor = cipher.encryptor()
    result: bytes = encryptor.update(padded) + encryptor.finalize()
    return result


def _build_legitimation_payload(password: str, username: str = "") -> bytes:
    """Build the legitimation payload structure.

    The payload is a serialized ValueStruct with:
    - 40401: LegitimationType (1=legacy, 2=new)
    - 40402: Username (UTF-8 blob)
    - 40403: Password or password hash (SHA-1)
    """
    from .vlq import encode_uint32_vlq
    from .protocol import DataType

    result = bytearray()

    if username:
        legit_type = 2
        password_data = password.encode("utf-8")
    else:
        legit_type = 1
        password_data = hashlib.sha1(password.encode("utf-8")).digest()  # noqa: S324

    username_data = username.encode("utf-8")

    # Struct with 3 elements
    result += bytes([0x00, DataType.STRUCT])
    result += encode_uint32_vlq(3)

    # Element 1: LegitimationType
    result += bytes([0x00, DataType.UDINT])
    result += encode_uint32_vlq(legit_type)

    # Element 2: Username blob
    result += bytes([0x00, DataType.BLOB])
    result += encode_uint32_vlq(len(username_data))
    result += username_data

    # Element 3: Password blob
    result += bytes([0x00, DataType.BLOB])
    result += encode_uint32_vlq(len(password_data))
    result += password_data

    return bytes(result)


class LegitimationState:
    """Tracks legitimation state for a connection."""

    def __init__(self, oms_secret: Optional[bytes] = None) -> None:
        self._oms_key: Optional[bytes] = None
        if oms_secret:
            self._oms_key = derive_legitimation_key(oms_secret)
        self._authenticated = False

    @property
    def authenticated(self) -> bool:
        return self._authenticated

    def mark_authenticated(self) -> None:
        self._authenticated = True

    def rotate_key(self) -> None:
        """Rotate the OMS-derived key (called after each legitimation)."""
        if self._oms_key:
            self._oms_key = hashlib.sha256(self._oms_key).digest()
