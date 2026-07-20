"""Tests for the symbolic tag browser.

The fixture is a real preset-dictionary EXPLORE blob captured from a live
S7-1200 G2 (FW V4.1) M area, compressed against the shipped ``IntfDescTag``
dictionary (Adler-32 ``0xce9b821b``). Decompressing it exercises the full
path: find_and_decompress -> clean XML -> Tag parsing.
"""

import base64

from s7commplus.tag_browser import Tag, parse_ident_container, tags_from_explore

# Live S7-1200 G2 (FW V4.1) EXPLORE response for the M area, from the zlib
# header onward: b"\x78\x7d" + dict-adler(0xce9b821b) + raw deflate.
_M_AREA_BLOB = base64.b64decode(
    "eH3Om4Ibs7GvyM1RKEstKs7MzwNmJj1gMZCal5yfkpmXbqtUWpKma6Fkb2eDrgs5AHJTi7JTi2hVgOG"
    "MSCNiii8sgQEPChQ/lABjMQloHHZPGBqi+QKokhJfIBdfBkguBzuAHKeXg1MAVqejlWCgtEI1pxthL3t"
    "JcnoKHrejFWEuVHW8CfEZCE+aAaZnHI43o1XKN1BC84kFyWkfvRgAACgQWbajk3JAFAIAOJgAAAJ4fe"
    "JynqGzsa/IzVEoSy0qBgoAvatnoKSQmpecn5KZl26rVFqSpmuhZI/NBiLNBwAy/SHEAKKiogAAAAA="
)


def test_parse_ident_container_addresses():
    xml = (
        '<IdentContainer>'
        '<Ident Name="input_1" Scope="Global" LID="10"><SimpleType>Bool</SimpleType>'
        '<Access SubClass="SimpleAccess"><SimpleAccess BitNumber="0" ByteNumber="0"'
        ' Width="Bit" Range="Input" /></Access></Ident>'
        '<Ident Name="mtag_word" Scope="Global" LID="13"><SimpleType>Word</SimpleType>'
        '<Access SubClass="SimpleAccess"><SimpleAccess ByteNumber="102"'
        ' Width="Word" Range="Memory" /></Access></Ident>'
        '</IdentContainer>'
    )
    tags = parse_ident_container(xml)
    assert tags == [
        Tag("input_1", "Bool", "%I0.0", 10, 0, 0),
        Tag("mtag_word", "Word", "%MW102", 13, 102, None),
    ]


def test_tags_from_live_g2_m_area():
    tags = tags_from_explore(_M_AREA_BLOB)
    got = {t.name: (t.data_type, t.address) for t in tags}
    assert got == {
        "merker_1": ("Bool", "%M0.2"),
        "mtag_byte": ("Byte", "%MB100"),
        "mtag_word": ("Word", "%MW102"),
        "mtag_dword": ("DWord", "%MD104"),
        "mtag_bool": ("Bool", "%M108.0"),
    }


def test_tags_from_explore_no_stream_returns_empty():
    assert tags_from_explore(b"no zlib stream here") == []
