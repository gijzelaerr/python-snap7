"""Custom CTR-mode block cipher used to encrypt the SessionKey blob's
random seed and challenge.

This is **not** standard AES-CTR. HarpoS7 layers a proprietary 128-bit
transform (``HarpoHash``) on top of AES-128-ECB to produce both
ciphertext and a running integrity MAC in a single pass:

- Init derives a 4 KB working table from ``AES-ECB(key, 0)`` and folds
  the IV into a 16-byte counter through ``HarpoHash`` rounds.
- EncryptCtr increments the counter, AES-encrypts it to produce a
  keystream block, XORs that with plaintext to make ciphertext, and
  feeds the ciphertext into a running ``HarpoHash`` accumulator.

Ported from HarpoS7 (MIT) — ``HarpoS7.Aes.HarpoAesCtr``. CalculateChecksum
is intentionally deferred to a follow-up slice; this slice covers the
``Init`` + ``EncryptCtr`` paths exercised by ``TestInit`` and
``TestEncrypt2Times`` upstream.
"""

from __future__ import annotations

from .harpo_aes import AES_BLOCK_SIZE, HarpoAes
from .harpo_hash import generate_lookup_table, hash_block

_LUT_SIZE = 4096


class HarpoAesCtr(HarpoAes):
    """Stateful CTR-mode primitive bound to a 16-byte AES key.

    Lifecycle:

    1. ``HarpoAesCtr(key)`` — construct.
    2. ``init(iv)`` — set up working table + counter from an
       IV. Must be a multiple of 16 bytes (12-byte and short-tail
       paths are upstream NotImplementedException, mirrored here).
    3. ``encrypt_ctr(plaintext)`` — call as many times as needed.
    """

    def __init__(self, key: bytes) -> None:
        super().__init__(key)
        # The four 16-byte slots HarpoS7 names as `_counter`,
        # `_aes2`, `_aes3`, `_aes4` plus `_iv_extension` at slot 5.
        # Slot 4 is the seed buffer used during Init only.
        self._counter = bytearray(AES_BLOCK_SIZE)
        self._aes2 = bytearray(AES_BLOCK_SIZE)
        self._aes3 = bytearray(AES_BLOCK_SIZE)  # MAC accumulator
        self._aes4 = bytearray(AES_BLOCK_SIZE)  # seed scratch
        self._iv_extension = bytearray(AES_BLOCK_SIZE)
        self._lut = bytearray(_LUT_SIZE)
        self._var1 = 0  # bytes encrypted in current pre-init region
        self._var2 = 0  # total bytes encrypted post-init

    @property
    def counter(self) -> bytes:
        """Internal counter state — exposed for vector-test parity."""
        return bytes(self._counter)

    def init(self, iv: bytes) -> None:
        """Set up the working table and counter from an IV.

        Mirrors HarpoS7's ``Init``. The IV must be a non-zero
        multiple of 16 bytes; 12-byte and partial-tail paths are
        ``NotImplementedException`` upstream and ``NotImplementedError``
        here — they're not exercised by the SessionKey handshake.

        Args:
            iv: IV bytes; length must be a multiple of 16.

        Raises:
            NotImplementedError: For IV lengths upstream rejects.
            ValueError: For empty IV.
        """
        if len(iv) == 0:
            raise ValueError("iv must not be empty")
        if len(iv) == 0xC:
            raise NotImplementedError("12-byte IV path not implemented")
        if len(iv) % AES_BLOCK_SIZE != 0:
            raise NotImplementedError("non-multiple-of-16 IV tail not implemented")

        # 1. AES-ECB encrypt 16 zero bytes — produces the seed used
        #    to drive the working-table generation.
        for i in range(AES_BLOCK_SIZE):
            self._aes4[i] = 0
        encrypted_zero = self.encrypt_ecb(bytes(self._aes4))
        for i in range(AES_BLOCK_SIZE):
            self._aes4[i] = encrypted_zero[i]

        # 2. Generate working LUT from that seed.
        self._lut[:] = generate_lookup_table(bytes(self._aes4))

        # 3. XOR + hash each 16-byte chunk of IV into _iv_extension.
        for i in range(AES_BLOCK_SIZE):
            self._iv_extension[i] = 0
        for chunk_start in range(0, len(iv), AES_BLOCK_SIZE):
            chunk = iv[chunk_start : chunk_start + AES_BLOCK_SIZE]
            for i in range(AES_BLOCK_SIZE):
                self._iv_extension[i] ^= chunk[i]
            self._iv_extension[:] = hash_block(bytes(self._iv_extension), bytes(self._lut))

        # 4. XOR the IV bit-length and a derived high-bits byte into
        #    fixed positions, then hash one more time.
        iv_bit_len = len(iv) << 3
        self._iv_extension[0xF] ^= iv_bit_len & 0xFF
        self._iv_extension[0xE] ^= (iv_bit_len >> 8) & 0xFF
        self._iv_extension[0xD] ^= (iv_bit_len >> 16) & 0xFF
        self._iv_extension[0xC] ^= (iv_bit_len >> 24) & 0xFF
        self._iv_extension[0xB] ^= (len(iv) >> 29) & 0xFF

        self._iv_extension[:] = hash_block(bytes(self._iv_extension), bytes(self._lut))

        # 6. Counter starts as a copy of the finalised IV extension.
        self._counter[:] = self._iv_extension

        # 7. Reset the MAC accumulator and byte counters.
        for i in range(AES_BLOCK_SIZE):
            self._aes3[i] = 0
        self._var1 = 0
        self._var2 = 0

    def _increment_counter(self) -> None:
        """Increment counter bytes 0xD..0xF only.

        Mirrors HarpoS7's behaviour: the upper 13 bytes are treated
        as a fixed nonce; only the bottom three bytes act as a counter.
        """
        v2 = 0x10
        while v2 >= 0xD + 1:
            v2 -= 1
            self._counter[v2] = (self._counter[v2] + 1) & 0xFF
            if self._counter[v2] != 0:
                break

    def encrypt_ctr(self, plaintext: bytes) -> bytes:
        """Encrypt arbitrarily-sized plaintext, accumulating the MAC.

        Output length matches input length. Multiple calls accumulate
        into the same MAC and counter — call ``init`` again to reset.

        Args:
            plaintext: Bytes to encrypt; any length, including zero.

        Returns:
            Ciphertext, same length as plaintext.
        """
        out = bytearray(len(plaintext))

        # Position within the current 16-byte keystream block —
        # bytes 0..(v1-1) of _aes2 have already been consumed.
        v1 = self._var2 & 0xF

        # If we previously encrypted 1..15 bytes of a block but
        # haven't yet hashed it, do that now (only on a re-entry
        # where _var2 == 0 but _var1 has unaligned tail bytes).
        if self._var2 == 0 and self._var1 != 0 and (self._var1 & 0xF) != 0:
            self._aes3[:] = hash_block(bytes(self._aes3), bytes(self._lut))

        v4 = 0  # bytes processed of plaintext
        # Finish the partial block we started in a previous call.
        if v1 != 0:
            if len(plaintext) != 0:
                while True:
                    if v1 > 0xF:
                        break
                    v3 = (self._aes2[v1] ^ plaintext[v4]) & 0xFF
                    out[v4] = v3
                    self._aes3[v1] ^= v3
                    v1 += 1
                    v4 += 1
                    if v4 >= len(plaintext):
                        break
            if v1 == 0x10:
                self._aes3[:] = hash_block(bytes(self._aes3), bytes(self._lut))
                v1 = 0

        # Process whole 16-byte blocks.
        while v4 + AES_BLOCK_SIZE <= len(plaintext):
            self._increment_counter()
            self._aes2[:] = self.encrypt_ecb(bytes(self._counter))
            for i in range(AES_BLOCK_SIZE):
                ct = (plaintext[v4 + i] ^ self._aes2[i]) & 0xFF
                out[v4 + i] = ct
                self._aes3[i] ^= ct
            self._aes3[:] = hash_block(bytes(self._aes3), bytes(self._lut))
            v4 += AES_BLOCK_SIZE

        # Tail: 1..15 bytes — encrypt under a fresh counter block,
        # but defer the hash until we either get more bytes (above)
        # or the caller calls calculate_checksum (next slice).
        if v4 < len(plaintext):
            self._increment_counter()
            self._aes2[:] = self.encrypt_ecb(bytes(self._counter))
            tail_len = len(plaintext) - v4
            aes3_index = v1
            for i in range(tail_len):
                ct = (self._aes2[aes3_index] ^ plaintext[v4 + i]) & 0xFF
                out[v4 + i] = ct
                self._aes3[aes3_index] ^= ct
                aes3_index += 1
            v4 = len(plaintext)

        self._var2 += v4
        return bytes(out)
