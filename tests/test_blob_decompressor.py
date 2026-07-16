"""Tests for the S7CommPlus blob decompressor."""

import zlib

import pytest

from s7commplus.blob_decompressor import decompress_blob, find_and_decompress
from s7commplus.zlib_dicts import ZLIB_DICTIONARIES, ZLIB_DICT_NAMES


def test_all_dictionaries_have_correct_adler32():
    for adler, data in ZLIB_DICTIONARIES.items():
        actual = zlib.adler32(data) & 0xFFFFFFFF
        assert actual == adler, f"Adler-32 mismatch for {ZLIB_DICT_NAMES.get(adler, '?')}: {actual:#x} != {adler:#x}"


def test_all_dictionaries_have_names():
    for adler in ZLIB_DICTIONARIES:
        assert adler in ZLIB_DICT_NAMES, f"Missing name for dictionary {adler:#x}"


def test_decompress_standard_blob():
    original = b"<IdentContainer><Ident Name='Tag_1' /></IdentContainer>"
    compressed = zlib.compress(original)
    result = decompress_blob(compressed)
    assert result == original.decode("utf-8")


def test_decompress_with_preset_dict():
    original = b"<IdentContainer><Ident Name='Tag_1' /></IdentContainer>"
    intfdesc_dict = ZLIB_DICTIONARIES[0xCE9B821B]

    # Compress with raw deflate (wbits=-15) + preset dictionary
    cobj = zlib.compressobj(level=6, wbits=-15, zdict=intfdesc_dict)
    raw_deflate = cobj.compress(original) + cobj.flush()
    # Build the zlib header: CMF=0x78, FLG with FDICT set, then 4-byte dict Adler-32
    header = b"\x78\x7d" + (0xCE9B821B).to_bytes(4, "big")
    blob = header + raw_deflate

    result = decompress_blob(blob)
    assert result == original.decode("utf-8")


def test_decompress_unknown_dict_raises():
    blob = b"\x78\x7d\xde\xad\xbe\xef" + b"\x00" * 10
    with pytest.raises(ValueError, match="Unknown zlib preset dictionary"):
        decompress_blob(blob)


def test_decompress_with_offset():
    original = b"<Test>data</Test>"
    compressed = zlib.compress(original)
    # 4-byte version prefix
    blob = b"\x00\x00\x00\x01" + compressed
    result = decompress_blob(blob, offset=4)
    assert result == original.decode("utf-8")


def test_find_and_decompress_standard():
    original = b"<Test>hello</Test>"
    compressed = zlib.compress(original)
    # Embed in some prefix junk
    data = b"\x00\x01\x02" + compressed
    result = find_and_decompress(data)
    assert result is not None
    assert result == original.decode("utf-8")


def test_find_and_decompress_no_stream():
    result = find_and_decompress(b"\x00\x01\x02\x03\x04\x05")
    assert result is None
