"""Decompress zlib-compressed blobs from S7-1200/1500 PLCs.

S7CommPlus PLCs compress XML metadata (tag definitions, network comments,
interface descriptions, etc.) using zlib with Siemens-specific preset
dictionaries. Python's ``zlib.decompress()`` returns ``Z_NEED_DICT`` for
these blobs; this module supplies the matching dictionary.

The 19 preset dictionaries were extracted from thomas-v2/S7CommPlusDriver
(LGPL-3.0) and are stored in ``zlib_dicts.py``.

Usage::

    data = decompress_blob(compressed_bytes)
    # data is the decompressed XML string (UTF-8)
"""

import logging
import zlib

from .zlib_dicts import ZLIB_DICTIONARIES, ZLIB_DICT_NAMES

logger = logging.getLogger(__name__)


def decompress_blob(data: bytes, offset: int = 0) -> str:
    """Decompress a zlib blob, auto-supplying the preset dictionary if needed.

    Args:
        data: Raw bytes containing the zlib stream.
        offset: Starting position within ``data``. Some blobs have a
            4-byte version prefix before the zlib header.

    Returns:
        Decompressed content as a UTF-8 string.

    Raises:
        ValueError: If the zlib stream requires an unknown dictionary.
        zlib.error: On other decompression failures.
    """
    stream = data[offset:]

    # Check for preset-dictionary zlib header: CMF=0x78, FLG with FDICT bit set (bit 5)
    if len(stream) >= 6 and stream[0] == 0x78 and (stream[1] & 0x20):
        dict_adler = int.from_bytes(stream[2:6], "big")
        zdict = ZLIB_DICTIONARIES.get(dict_adler)
    else:
        # Standard zlib stream — no preset dictionary
        return zlib.decompress(stream).decode("utf-8")

    # Preset dictionary required

    if zdict is None:
        name = ZLIB_DICT_NAMES.get(dict_adler, "unknown")
        raise ValueError(
            f"Unknown zlib preset dictionary: adler32=0x{dict_adler:08x} ({name}). "
            f"Known dictionaries: {', '.join(ZLIB_DICT_NAMES.values())}"
        )

    logger.debug("Using preset dictionary: %s (0x%08x)", ZLIB_DICT_NAMES.get(dict_adler, "?"), dict_adler)

    dobj = zlib.decompressobj(wbits=-15, zdict=zdict)
    # Skip the 6-byte zlib header (2 magic + 4 dict adler)
    result = dobj.decompress(stream[6:])
    return result.decode("utf-8")


def find_and_decompress(data: bytes) -> str | None:
    """Scan raw bytes for a zlib stream with preset dictionary and decompress it.

    Searches for the ``78 7D`` magic (zlib level 6 + FDICT flag) that
    indicates a preset-dictionary stream. Falls back to ``78 01``/``78 5E``/
    ``78 9C``/``78 DA`` for standard streams.

    Args:
        data: Raw EXPLORE response payload (possibly multi-fragment).

    Returns:
        Decompressed UTF-8 string, or ``None`` if no zlib stream found.
    """
    # Preset-dictionary magic: CMF=0x78 (deflate, window=32K), FLG=0x7D (FDICT set)
    for magic in (b"\x78\x7d", b"\x78\x01", b"\x78\x5e", b"\x78\x9c", b"\x78\xda"):
        pos = data.find(magic)
        if pos >= 0:
            try:
                return decompress_blob(data, offset=pos)
            except (ValueError, zlib.error) as e:
                logger.debug("Decompression failed at offset %d: %s", pos, e)
                continue
    return None
