"""RealPlcAuthenticator — builds the 180-byte SecurityKeyEncryptedKey blob.

Orchestrates PreSeedTransform, SeedTransform, KeyDerivationTransform,
LutGenerator, ChecksumTransform, BigIntOperations, and AES-ECB to
produce the encrypted authentication blob for S7-1200/1500 PLCs.

Manual port of ``HarpoS7.Family0.Auth.RealPlcAuthenticator``.
"""

from __future__ import annotations

import os
import struct
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from ..blob_metadata import write_metadata
from ..keys import KeyFamily
from . import (
    checksum_transform,
    key_derivation_transform,
    lut_generator,
    pre_seed_transform,
    seed_transform,
)
from . import big_int_operations


class RealPlcAuthenticator:
    def __init__(
        self,
        key1: bytes | None = None,
        key2: bytes | None = None,
    ) -> None:
        # Order must match C#: key2, key1, IV (for deterministic test vectors)
        if key2 is not None:
            self._key2 = bytearray(key2)
        else:
            self._key2 = bytearray(os.urandom(24))

        self._key1 = bytearray(key1 if key1 is not None else os.urandom(24))
        self._iv = bytearray(os.urandom(16))

        self._lookup_table = bytearray(lut_generator.DESTINATION_SIZE)
        self._checksum = bytearray(16)
        self._challenge_key = bytearray(16)
        self._checksum_key = bytearray(16)
        self._encrypted_bytes = 0

    @property
    def key2_leftover_length(self) -> int:
        return len(self._key2) % 16

    def write_metadata(
        self,
        blob: bytearray,
        public_key: bytes,
        family: KeyFamily,
    ) -> int:
        if family not in (KeyFamily.S7_1200, KeyFamily.S7_1500):
            raise ValueError(f"{family.name} is not supported by this authenticator")
        return write_metadata(blob, public_key, bytes(self._key2), family)

    def write_seed(self, blob: bytearray, public_key: bytes) -> int:
        t1 = bytearray(pre_seed_transform.DESTINATION_SIZE)
        pre_seed_transform.execute(t1, bytes(self._key1))
        seed_transform.execute(blob, public_key, bytes(t1))
        offset = seed_transform.DESTINATION_SIZE

        self._derive_keys_and_lut(bytes(t1))

        checksum_transform.execute(self._checksum, bytes(self._iv), bytes(self._lookup_table))

        return offset

    def encrypt_full_blocks(self, blob: bytearray, challenge: bytes) -> int:
        offset = 0

        # Copy starting IV
        blob[offset : offset + 16] = self._iv
        offset += 16

        # Encrypt 16 bytes of challenge (skip first 2)
        ct_block = self._aes_ecb_encrypt(bytes(self._iv))
        ct_block = _xor_bytes(ct_block, challenge[2:18])
        blob[offset : offset + 16] = ct_block
        offset += 16
        self._encrypted_bytes += 16

        big_int_operations.rotate_left_31(self._iv)
        self._update_checksum(ct_block)

        # Encrypt full 16-byte blocks of key2
        for i in range(len(self._key2) // 16):
            ct_block = self._aes_ecb_encrypt(bytes(self._iv))
            ct_block = _xor_bytes(ct_block, bytes(self._key2[i * 16 : (i + 1) * 16]))
            blob[offset : offset + 16] = ct_block
            offset += 16
            self._encrypted_bytes += 16

            big_int_operations.rotate_left_31(self._iv)
            self._update_checksum(ct_block)

        return offset

    def encrypt_final_block(self, blob: bytearray) -> int:
        leftover = self.key2_leftover_length
        leftover_start = len(self._key2) - leftover

        ct_block = bytearray(self._aes_ecb_encrypt(bytes(self._iv)))
        ct_block = bytearray(
            _xor_bytes(bytes(ct_block[:leftover]), bytes(self._key2[leftover_start : leftover_start + leftover]))
        )

        blob[:leftover] = ct_block[:leftover]
        self._encrypted_bytes += leftover
        offset = leftover

        # Pad the rest of the block with zeros for checksum
        ct_padded = bytearray(16)
        ct_padded[:leftover] = ct_block[:leftover]

        self._update_checksum(bytes(ct_padded))

        # Final checksum calculation
        chk_dwords = list(struct.unpack("<4I", self._checksum))
        chk_dwords[3] ^= self._encrypted_bytes
        struct.pack_into("<4I", self._checksum, 0, *chk_dwords)

        checksum_transform.execute(self._checksum, bytes(self._checksum), bytes(self._lookup_table))

        # Encrypt checksum with checksum encryption key
        cipher = Cipher(algorithms.AES(bytes(self._checksum_key)), modes.ECB())
        enc = cipher.encryptor()
        encrypted_checksum = enc.update(bytes(self._checksum)) + enc.finalize()

        blob[offset : offset + 16] = encrypted_checksum
        offset += 16

        return offset

    def extract_key2(self) -> bytes:
        return bytes(self._key2)

    def _derive_keys_and_lut(self, t1: bytes) -> None:
        kd_buf = bytearray(key_derivation_transform.DESTINATION_SIZE)
        key_derivation_transform.execute(kd_buf, t1)

        # First 16 bytes: challenge encryption key
        self._challenge_key[:] = kd_buf[:16]

        # Next 16 bytes: checksum encryption key
        self._checksum_key[:] = kd_buf[16:32]

        # Last 16 bytes: LUT seed
        lut_generator.execute(self._lookup_table, bytes(kd_buf[32:]))

    def _aes_ecb_encrypt(self, plaintext: bytes) -> bytes:
        cipher = Cipher(algorithms.AES(bytes(self._challenge_key)), modes.ECB())
        enc = cipher.encryptor()
        return enc.update(plaintext[:16]) + enc.finalize()

    def _update_checksum(self, ct_block: bytes) -> None:
        self._checksum = bytearray(_xor_bytes(bytes(self._checksum), ct_block[:16]))
        checksum_transform.execute(self._checksum, bytes(self._checksum), bytes(self._lookup_table))


def _xor_bytes(a: bytes, b: bytes) -> bytes:
    return bytes(x ^ y for x, y in zip(a, b))
