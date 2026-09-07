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
import struct
from typing import Optional

from .protocol import DataType, Ids, LegitimationType
from .vlq import decode_uint32_vlq, encode_uint32_vlq

logger = logging.getLogger(__name__)


def _parse_paom_string(version_string: str) -> Optional[tuple[str, int]]:
    """Read the device series and firmware number out of a ServerSessionVersion PAOM string.

    A PAOM string is `<paom id>;<order number>;<firmware>`. Only the leading digit
    of the model number selects the series, and the firmware is compared as
    `major * 100 + minor`, so those are what this returns.

    ```python
    _parse_paom_string("1;6ES7 512-1CK01-0AB0;V2.9")  # ("5", 209)
    ```

    The reference does this with one pattern over the whole string,
    `^[^;]*;[^;]*[17]\\s?(\\d{3}).*;[VS](\\d{1,2}\\.\\d+)$`, which this matches except
    that it also tolerates more than one space in front of the model number.

    :param version_string: PAOM string from `extract_session_version_string`.
    :return: The series digit and firmware number, or None when either is unreadable.

    Reference: thomas-v2/S7CommPlusDriver/Legitimation/Legitimation.cs
    """
    fields = version_string.split(";")
    if len(fields) < 3:
        return None

    # The model number ends the order number, behind a vendor prefix whose last
    # digit is 1 or 7: "6ES7 512-1CK01-0AB0" -> prefix "6ES7", model "512".
    order_number = fields[1].split("-")[0].rstrip()
    model, prefix = order_number[-3:], order_number[:-3].rstrip()
    if len(model) != 3 or not model.isdecimal() or prefix[-1:] not in ("1", "7"):
        return None

    firmware = fields[-1]
    if firmware[:1].upper() not in ("V", "S"):
        return None
    major, dot, minor = firmware[1:].partition(".")
    if not dot or not (1 <= len(major) <= 2) or not major.isdecimal() or not minor.isdecimal():
        return None

    return model[0], int(major) * 100 + int(minor)


def extract_session_version_string(raw: bytes) -> Optional[str]:
    """Extract the device PAOM string from a raw ServerSessionVersion value.

    The value is the typed ServerSessionVersion captured from the CreateObject
    response. Element `Ids.SESSION_VERSION_SYSTEM_PAOM_STRING` holds the device
    identity and firmware version as a WString.

    ```python
    version = extract_session_version_string(connection.server_session_version)
    # '1;6ES7 512-1CK01-0AB0;V2.9'
    ```

    :param raw: Raw typed ServerSessionVersion value (flags + datatype + struct data).
    :return: The PAOM string, or None when the element is absent or undecodable.
    """
    needle = encode_uint32_vlq(Ids.SESSION_VERSION_SYSTEM_PAOM_STRING)
    search_from = 0
    while True:
        index = raw.find(needle, search_from)
        if index < 0:
            return None
        search_from = index + 1
        # [VLQ key][flags][datatype][VLQ length][utf-8 bytes]
        length_at = index + len(needle) + 2
        if length_at > len(raw) or raw[length_at - 1] != DataType.WSTRING:
            continue
        try:
            length, consumed = decode_uint32_vlq(raw, length_at)
        except ValueError:
            continue
        start = length_at + consumed
        if start + length > len(raw):
            continue
        try:
            return raw[start : start + length].decode("utf-8")
        except UnicodeDecodeError:
            continue


def decide_legitimation_mode(version_string: str) -> Optional[LegitimationType]:
    """Decide legacy (SHA-1 XOR) vs new (AES-256-CBC) legitimation from the firmware.

    ```python
    decide_legitimation_mode("1;6ES7 512-1CK01-0AB0;V2.9")  # LegitimationType.LEGACY
    ```

    :param version_string: PAOM string from `extract_session_version_string`.
    :return: The mode to use, or None when the device or firmware does not
        support legitimation at all.

    Reference: thomas-v2/S7CommPlusDriver/Legitimation/Legitimation.cs
    """
    parsed = _parse_paom_string(version_string)
    if parsed is None:
        logger.warning(f"Could not extract the firmware version from {version_string!r}")
        return None
    series, firmware = parsed

    if series == "5":  # S7-1500
        if firmware < 209:
            return None
        return LegitimationType.LEGACY if firmware < 301 else LegitimationType.NEW
    if "50-0XB0" in version_string.upper() and series == "2":  # S7-1200 G2
        return LegitimationType.NEW
    if series == "2":  # S7-1200
        if firmware < 403:
            return None
        return LegitimationType.LEGACY if firmware < 407 else LegitimationType.NEW
    if series == "6":  # S7-1507S software controller
        if firmware < 2109:
            return None
        return LegitimationType.LEGACY
    return None


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
    """Build the plaintext payload that new-mode legitimation encrypts.

    An empty username selects legacy-style credentials, where the password travels as its SHA-1 hash.

    Reference: thomas-v2/S7CommPlusDriver/Legitimation/Legitimation.cs
    """
    if username:
        legitimation_type = LegitimationType.NEW
        password_data = password.encode("utf-8")
    else:
        legitimation_type = LegitimationType.LEGACY
        password_data = hashlib.sha1(password.encode("utf-8")).digest()  # noqa: S324

    # Struct with 3 elements
    result = bytearray()
    result += bytes([0x00, DataType.STRUCT])
    result += struct.pack(">I", Ids.LEGITIMATION_PAYLOAD_STRUCT)

    # Element 1: LegitimationType
    result += encode_uint32_vlq(Ids.LEGITIMATION_PAYLOAD_TYPE)
    result += bytes([0x00, DataType.UDINT]) + encode_uint32_vlq(legitimation_type)

    # Element 2: Username blob
    result += encode_uint32_vlq(Ids.LEGITIMATION_PAYLOAD_USERNAME)
    username_data = username.encode("utf-8")
    result += bytes([0x00, DataType.BLOB])
    result += encode_uint32_vlq(len(username_data))
    result += username_data

    # Element 3: Password blob
    result += encode_uint32_vlq(Ids.LEGITIMATION_PAYLOAD_PASSWORD)
    result += bytes([0x00, DataType.BLOB])
    result += encode_uint32_vlq(len(password_data))
    result += password_data

    result += bytes([0x00])  # list terminator
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
