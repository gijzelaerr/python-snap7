"""Big-integer arithmetic transforms.

Manual port of the four ``BigInt*`` Transform files in
``HarpoS7.Family0.Transforms`` plus the ``BigIntegerCompressor``
helper from ``HarpoS7.Family0.Utils``. Python's built-in ``int`` is
arbitrary-precision, so we don't need a ``BigInteger`` library — just
``int.from_bytes`` and ``int.to_bytes`` with the right signedness.
"""

from __future__ import annotations

from . import big_int_operations as _bio

#: Result is always 6 uints (24 bytes) — output of ``finalize``.
DESTINATION_SIZE = _bio.FINALIZE_DESTINATION_SIZE
#: Operands are always 6 uints (24 bytes) — input to ``prepare``.
SOURCE_SIZE = _bio.PREPARE_SOURCE_SIZE


def _prepared(buf: bytes) -> bytes:
    """Run ``prepare`` and return the 20-byte result."""
    out = bytearray(_bio.PREPARE_DESTINATION_SIZE)
    _bio.prepare(out, buf)
    return bytes(out)


def _to_int(buf: bytes) -> int:
    return int.from_bytes(buf, byteorder="little", signed=False)


def _to_bytes(value: int, length: int) -> bytes:
    """Serialise ``value`` to ``length`` little-endian bytes (unsigned)."""
    return value.to_bytes(length, byteorder="little", signed=False)


def _compress(buf: bytearray) -> tuple[bool, int]:
    """Match the upstream ``BigIntegerCompressor.Compress`` semantics.

    Returns ``(needs_more, new_length)``: ``needs_more`` is ``True``
    when the result still doesn't fit in ``FinalizeSourceSize`` bytes.
    Mutates ``buf`` in place — caller must own it.
    """
    length = len(buf)
    if length > _bio.FINALIZE_SOURCE_SIZE:
        overflow = _to_int(bytes(buf[_bio.FINALIZE_SOURCE_SIZE :]))
        compressed = _to_int(bytes(buf[: _bio.FINALIZE_SOURCE_SIZE]))
        product = overflow * 0x2F + compressed
        new_bytes = _to_bytes(product, length)
        # Trim trailing zero bytes — TryWriteBytes returns the actual
        # used length, not the buffer's full size.
        actual_length = len(new_bytes.rstrip(b"\x00")) or 1
        buf[:actual_length] = new_bytes[:actual_length]
        del buf[actual_length:]
        length = actual_length
    return length > _bio.FINALIZE_SOURCE_SIZE, length


def _final_compress(buf: bytearray) -> None:
    """Add 0x2F to the leading uint32, in place."""
    if len(buf) <= _bio.FINALIZE_SOURCE_SIZE:
        raise ValueError(f"BigInteger does not need final compression (length {len(buf)} ≤ {_bio.FINALIZE_SOURCE_SIZE})")
    leading = (_to_int(bytes(buf[:4])) + 0x2F) & 0xFFFFFFFF
    buf[:4] = leading.to_bytes(4, byteorder="little", signed=False)


def _finalize_compressed(buf: bytearray, destination: bytearray) -> None:
    """Run two compression passes plus an optional FinalCompress, then
    Finalize."""
    needs_more, length = _compress(buf)
    if needs_more:
        needs_more, length = _compress(buf[:length] if length < len(buf) else buf)
        # Trim buf to length.
        del buf[length:]
        if needs_more:
            _final_compress(buf)
    _bio.finalize(destination, bytes(buf))


def big_int_addition(destination: bytearray, source1: bytes, source2: bytes) -> None:
    """``BigIntAddition.Execute`` — destination = source1 + source2 (mod p)."""
    if len(destination) < DESTINATION_SIZE:
        raise ValueError(f"destination must be at least {DESTINATION_SIZE} bytes")
    if len(source1) < SOURCE_SIZE or len(source2) < SOURCE_SIZE:
        raise ValueError(f"each source must be at least {SOURCE_SIZE} bytes")

    a = _to_int(_prepared(source1))
    b = _to_int(_prepared(source2))
    sum_int = a + b

    length = max(1, (sum_int.bit_length() + 7) // 8)
    sum_bytes = bytearray(_to_bytes(sum_int, length))

    if length > _bio.FINALIZE_SOURCE_SIZE:
        # The C# does an in-place overflow correction on a uint32 view
        # of the leading 16 bytes only when length overruns. Mirror it.
        leading = _to_int(bytes(sum_bytes[:16]))
        # Add 0x2F to the bottom uint32, propagate carry up to uint32 #3.
        words = [
            (leading >> 0) & 0xFFFFFFFF,
            (leading >> 32) & 0xFFFFFFFF,
            (leading >> 64) & 0xFFFFFFFF,
            (leading >> 96) & 0xFFFFFFFF,
        ]
        words[0] = (words[0] + 0x2F) & 0xFFFFFFFF
        carry = 1 if words[0] < 0x2F else 0
        if carry:
            for i in range(1, 4):
                words[i] = (words[i] + carry) & 0xFFFFFFFF
                carry = 1 if words[i] < carry else 0
            if carry:
                words[0] = (words[0] + 0x5E) & 0xFFFFFFFF
        rebuilt = sum(words[i] << (32 * i) for i in range(4))
        sum_bytes[:16] = rebuilt.to_bytes(16, byteorder="little", signed=False)

    _bio.finalize(destination, bytes(sum_bytes))


def _signed_byte_count(value: int) -> int:
    """Mirror C#'s ``BigInteger.GetByteCount(isUnsigned=false)``.

    Returns the smallest byte count whose signed two's-complement
    little-endian representation fits ``value``.
    """
    if value == 0:
        return 1
    if value > 0:
        return max(1, (value.bit_length() + 8) // 8)
    return max(1, ((-value - 1).bit_length() + 8) // 8)


def big_int_subtraction(destination: bytearray, minuend: bytes, subtrahend: bytes) -> None:
    """``BigIntSubtraction.Execute`` — destination = minuend - subtrahend.

    Mirrors the upstream's quirky negative-result handling: subtract an
    extra ``0x2F`` to wrap into the field, write as signed two's-
    complement, then sign-extend with ``0xFF`` to ``FinalizeSourceSize``.
    """
    if len(destination) < DESTINATION_SIZE:
        raise ValueError(f"destination must be at least {DESTINATION_SIZE} bytes")
    if len(minuend) < SOURCE_SIZE or len(subtrahend) < SOURCE_SIZE:
        raise ValueError(f"both inputs must be at least {SOURCE_SIZE} bytes")

    a = _to_int(_prepared(minuend))
    b = _to_int(_prepared(subtrahend))
    diff = a - b
    is_negative = diff < 0
    if is_negative:
        diff -= 0x2F

    signed_count = _signed_byte_count(diff)
    buffer_size = max(signed_count, _bio.FINALIZE_SOURCE_SIZE)
    diff_bytes = bytearray(diff.to_bytes(signed_count, byteorder="little", signed=True))
    diff_bytes.extend(b"\x00" * (buffer_size - len(diff_bytes)))
    diff_length = signed_count

    if diff_length > _bio.FINALIZE_SOURCE_SIZE:
        # Upstream comment: "TODO: Examine further, trimming does the
        # job for now"
        diff_length = _bio.FINALIZE_SOURCE_SIZE
    elif diff_length < _bio.FINALIZE_SOURCE_SIZE and is_negative:
        # Sign-extend with 0xFF to FinalizeSourceSize. Upstream's
        # TODO acknowledges this is shaky.
        for i in range(diff_length, _bio.FINALIZE_SOURCE_SIZE):
            diff_bytes[i] = 0xFF
        diff_length = _bio.FINALIZE_SOURCE_SIZE

    _bio.finalize(destination, bytes(diff_bytes[:diff_length]))


def big_int_multiplication(destination: bytearray, source1: bytes, source2: bytes) -> None:
    """``BigIntMultiplication.Execute`` — destination = source1 * source2."""
    if len(destination) < DESTINATION_SIZE:
        raise ValueError(f"destination must be at least {DESTINATION_SIZE} bytes")
    if len(source1) < SOURCE_SIZE or len(source2) < SOURCE_SIZE:
        raise ValueError(f"each source must be at least {SOURCE_SIZE} bytes")

    a = _to_int(_prepared(source1))
    b = _to_int(_prepared(source2))
    product = a * b
    length = max(1, (product.bit_length() + 7) // 8)
    buf = bytearray(_to_bytes(product, length))
    _finalize_compressed(buf, destination)


def big_int_square(destination: bytearray, source: bytes) -> None:
    """``BigIntSquare.Execute`` — destination = source ** 2."""
    if len(destination) < DESTINATION_SIZE:
        raise ValueError(f"destination must be at least {DESTINATION_SIZE} bytes")
    if len(source) < SOURCE_SIZE:
        raise ValueError(f"source must be at least {SOURCE_SIZE} bytes")

    base_int = _to_int(_prepared(source))
    result = base_int * base_int
    length = max(1, (result.bit_length() + 7) // 8)
    buf = bytearray(_to_bytes(result, length))
    _finalize_compressed(buf, destination)
