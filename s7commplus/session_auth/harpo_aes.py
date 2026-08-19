"""Standard AES-128-ECB primitive used by the session-key handshake.

HarpoS7's ``HarpoAes`` is a thin .NET-Framework wrapper around its
built-in AES, configured for 128-bit keys, 128-bit blocks, ECB mode,
zero padding. We mirror the API in Python via ``cryptography`` (the
standard cross-platform PyPI crypto library, already an optional
dependency of python-snap7 under the ``s7commplus`` extra).

Only ``encrypt_ecb`` is exposed: HarpoS7 uses AES purely as a building
block for ``HarpoAesCtr``, never as an encryption primitive on its own.
"""

from __future__ import annotations

#: Block and key length in bytes for the AES variant HarpoS7 uses.
AES_BLOCK_SIZE = 16
AES_KEY_LENGTH = 16


class HarpoAes:
    """AES-128-ECB context bound to a 16-byte key.

    Reusable across many ``encrypt_ecb`` calls — the underlying cipher
    object is constructed once and a fresh encryptor is created per
    block. This matches HarpoS7's pattern, where ``HarpoAesCtr``
    repeatedly encrypts the counter buffer.

    Args:
        key: Exactly 16 bytes.

    Raises:
        ValueError: If the key is not 16 bytes.
    """

    def __init__(self, key: bytes) -> None:
        if len(key) != AES_KEY_LENGTH:
            raise ValueError(f"key must be {AES_KEY_LENGTH} bytes, got {len(key)}")

        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

        self._cipher = Cipher(algorithms.AES(key), modes.ECB())

    def encrypt_ecb(self, plaintext: bytes) -> bytes:
        """Encrypt one or more 16-byte AES-ECB blocks.

        Args:
            plaintext: Multiple of 16 bytes.

        Returns:
            Ciphertext, same length as plaintext.

        Raises:
            ValueError: If plaintext length isn't a multiple of 16.
        """
        if len(plaintext) % AES_BLOCK_SIZE != 0:
            raise ValueError(f"plaintext must be a multiple of {AES_BLOCK_SIZE} bytes, got {len(plaintext)}")
        encryptor = self._cipher.encryptor()
        result: bytes = encryptor.update(plaintext) + encryptor.finalize()
        return result
