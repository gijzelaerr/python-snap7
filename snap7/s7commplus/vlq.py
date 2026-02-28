"""
Variable-Length Quantity (VLQ) encoding for S7CommPlus.

S7CommPlus uses VLQ encoding for integer values in the protocol framing.
This is similar to MIDI VLQ or protobuf varints, with some S7-specific
variations for signed values and 64-bit special handling.

Encoding scheme:
    - Each byte uses 7 data bits + 1 continuation bit (MSB)
    - continuation bit = 1 means more bytes follow
    - continuation bit = 0 means this is the last byte
    - Big-endian byte order (most significant group first)
    - Signed values use bit 6 of the first byte as a sign flag

64-bit special case:
    - 8 bytes of 7-bit groups = 56 bits, which is less than 64
    - The 9th byte uses all 8 bits (no continuation flag)
    - This avoids needing a 10th byte

Reference: thomas-v2/S7CommPlusDriver/Core/S7p.cs
"""

def encode_uint32_vlq(value: int) -> bytes:
    """Encode an unsigned 32-bit integer as VLQ.

    Args:
        value: Unsigned integer (0 to 2^32-1)

    Returns:
        VLQ-encoded bytes (1-5 bytes)
    """
    if value < 0 or value > 0xFFFFFFFF:
        raise ValueError(f"Value out of range for uint32 VLQ: {value}")

    result = bytearray()

    # Find the highest non-zero 7-bit group
    num_groups = 1
    for i in range(4, 0, -1):
        if value & (0x7F << (i * 7)):
            num_groups = i + 1
            break

    # Encode each group, MSB first
    for i in range(num_groups - 1, -1, -1):
        group = (value >> (i * 7)) & 0x7F
        if i > 0:
            group |= 0x80  # Set continuation bit
        result.append(group)

    return bytes(result)


def decode_uint32_vlq(data: bytes, offset: int = 0) -> tuple[int, int]:
    """Decode a VLQ-encoded unsigned 32-bit integer.

    Args:
        data: Buffer containing VLQ data
        offset: Starting position in buffer

    Returns:
        Tuple of (decoded_value, bytes_consumed)
    """
    value = 0
    consumed = 0

    for _ in range(5):  # Max 5 bytes for 32-bit
        if offset + consumed >= len(data):
            raise ValueError("Unexpected end of VLQ data")

        octet = data[offset + consumed]
        consumed += 1

        value = (value << 7) | (octet & 0x7F)

        if not (octet & 0x80):  # No continuation bit
            break

    return value, consumed


def encode_int32_vlq(value: int) -> bytes:
    """Encode a signed 32-bit integer as VLQ.

    Signed VLQ uses bit 6 of the first byte as a sign indicator.
    Negative values are encoded in a compact two's-complement-like form.

    Args:
        value: Signed integer (-2^31 to 2^31-1)

    Returns:
        VLQ-encoded bytes (1-5 bytes)
    """
    if value < -0x80000000 or value > 0x7FFFFFFF:
        raise ValueError(f"Value out of range for int32 VLQ: {value}")

    result = bytearray()

    if value == -0x80000000:
        abs_v = 0x80000000
    else:
        abs_v = abs(value)

    b = [0] * 5
    b[0] = value & 0x7F
    length = 1

    for i in range(1, 5):
        if abs_v >= 0x40:
            length += 1
            abs_v >>= 7
            value >>= 7
            b[i] = ((value & 0x7F) + 0x80) & 0xFF
        else:
            break

    # Emit in reverse order (big-endian)
    for i in range(length - 1, -1, -1):
        result.append(b[i])

    return bytes(result)


def decode_int32_vlq(data: bytes, offset: int = 0) -> tuple[int, int]:
    """Decode a VLQ-encoded signed 32-bit integer.

    Args:
        data: Buffer containing VLQ data
        offset: Starting position in buffer

    Returns:
        Tuple of (decoded_value, bytes_consumed)
    """
    value = 0
    consumed = 0

    for counter in range(1, 6):  # Max 5 bytes for 32-bit
        if offset + consumed >= len(data):
            raise ValueError("Unexpected end of VLQ data")

        octet = data[offset + consumed]
        consumed += 1

        if counter == 1 and (octet & 0x40):  # Check sign bit
            octet &= 0xBF
            value = -64  # Pre-load with one's complement
        else:
            value <<= 7

        value += octet & 0x7F

        if not (octet & 0x80):  # No continuation bit
            break

    return value, consumed


def encode_uint64_vlq(value: int) -> bytes:
    """Encode an unsigned 64-bit integer as VLQ.

    64-bit VLQ has special handling: since 8 groups of 7 bits = 56 bits < 64,
    the 9th byte uses all 8 bits (no continuation flag).

    Args:
        value: Unsigned integer (0 to 2^64-1)

    Returns:
        VLQ-encoded bytes (1-9 bytes)
    """
    if value < 0 or value > 0xFFFFFFFFFFFFFFFF:
        raise ValueError(f"Value out of range for uint64 VLQ: {value}")

    special = value > 0x00FFFFFFFFFFFFFF

    b = [0] * 9
    if special:
        b[0] = value & 0xFF
    else:
        b[0] = value & 0x7F

    length = 1
    for i in range(1, 9):
        if value >= 0x80:
            length += 1
            if i == 1 and special:
                value >>= 8
            else:
                value >>= 7
            b[i] = ((value & 0x7F) + 0x80) & 0xFF
        else:
            break

    if special and length == 8:
        length += 1
        b[8] = 0x80

    # Emit in reverse order
    result = bytearray()
    for i in range(length - 1, -1, -1):
        result.append(b[i])

    return bytes(result)


def decode_uint64_vlq(data: bytes, offset: int = 0) -> tuple[int, int]:
    """Decode a VLQ-encoded unsigned 64-bit integer.

    Args:
        data: Buffer containing VLQ data
        offset: Starting position in buffer

    Returns:
        Tuple of (decoded_value, bytes_consumed)
    """
    value = 0
    consumed = 0
    cont = 0

    for counter in range(1, 9):  # Max 8 groups of 7 bits
        if offset + consumed >= len(data):
            raise ValueError("Unexpected end of VLQ data")

        octet = data[offset + consumed]
        consumed += 1

        value = (value << 7) | (octet & 0x7F)
        cont = octet & 0x80

        if not cont:
            break

    if cont:
        # 9th byte: all 8 bits are data (special 64-bit handling)
        if offset + consumed >= len(data):
            raise ValueError("Unexpected end of VLQ data")

        octet = data[offset + consumed]
        consumed += 1
        value = (value << 8) | octet

    return value, consumed


def encode_int64_vlq(value: int) -> bytes:
    """Encode a signed 64-bit integer as VLQ.

    Args:
        value: Signed integer (-2^63 to 2^63-1)

    Returns:
        VLQ-encoded bytes (1-9 bytes)
    """
    if value < -0x8000000000000000 or value > 0x7FFFFFFFFFFFFFFF:
        raise ValueError(f"Value out of range for int64 VLQ: {value}")

    if value == -0x8000000000000000:
        abs_v = 0x8000000000000000
    else:
        abs_v = abs(value)

    special = abs_v > 0x007FFFFFFFFFFFFF

    b = [0] * 9
    if special:
        b[0] = value & 0xFF
    else:
        b[0] = value & 0x7F

    length = 1
    for i in range(1, 9):
        if abs_v >= 0x40:
            length += 1
            if i == 1 and special:
                abs_v >>= 8
                value >>= 8
            else:
                abs_v >>= 7
                value >>= 7
            b[i] = ((value & 0x7F) + 0x80) & 0xFF
        else:
            break

    if special and length == 8:
        length += 1
        b[8] = 0x80 if value >= 0 else 0xFF

    # Emit in reverse order
    result = bytearray()
    for i in range(length - 1, -1, -1):
        result.append(b[i])

    return bytes(result)


def decode_int64_vlq(data: bytes, offset: int = 0) -> tuple[int, int]:
    """Decode a VLQ-encoded signed 64-bit integer.

    Args:
        data: Buffer containing VLQ data
        offset: Starting position in buffer

    Returns:
        Tuple of (decoded_value, bytes_consumed)
    """
    value = 0
    consumed = 0
    cont = 0

    for counter in range(1, 9):  # Max 8 groups of 7 bits
        if offset + consumed >= len(data):
            raise ValueError("Unexpected end of VLQ data")

        octet = data[offset + consumed]
        consumed += 1

        if counter == 1 and (octet & 0x40):  # Check sign bit
            octet &= 0xBF
            value = -64  # Pre-load with one's complement
        else:
            value <<= 7

        cont = octet & 0x80
        value += octet & 0x7F

        if not cont:
            break

    if cont:
        # 9th byte: all 8 bits are data
        if offset + consumed >= len(data):
            raise ValueError("Unexpected end of VLQ data")

        octet = data[offset + consumed]
        consumed += 1
        value = (value << 8) | octet

    return value, consumed
