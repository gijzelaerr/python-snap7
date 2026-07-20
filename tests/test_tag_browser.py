"""Tests for the symbolic tag / block-interface browser.

The I/Q/M fixture is a real preset-dictionary EXPLORE blob captured from a live
S7-1200 G2 (FW V4.1) M area (``IntfDescTag`` dict, Adler-32 ``0xce9b821b``).
The block-interface fixture is a real EXPLORE blob for an optimized DB
(``Data_block_1``) from the same PLC, exercising the ``DebugInfo_IntfDesc``
dict (Adler-32 ``0x66052b13``) and the RID -> SoftDataType mapping.
"""

import base64
import zlib

from s7commplus.tag_browser import (
    DataBlock,
    Member,
    Tag,
    block_interface_from_explore,
    datablocks_from_explore,
    parse_block_interface,
    parse_ident_container,
    tags_from_explore,
)

# Live S7-1200 G2 (FW V4.1) EXPLORE response for the M area, from the zlib
# header onward: b"\x78\x7d" + dict-adler(0xce9b821b) + raw deflate.
_M_AREA_BLOB = base64.b64decode(
    "eH3Om4Ibs7GvyM1RKEstKs7MzwNmJj1gMZCal5yfkpmXbqtUWpKma6Fkb2eDrgs5AHJTi7JTi2hVgOG"
    "MSCNiii8sgQEPChQ/lABjMQloHHZPGBqi+QKokhJfIBdfBkguBzuAHKeXg1MAVqejlWCgtEI1pxthL3t"
    "JcnoKHrejFWEuVHW8CfEZCE+aAaZnHI43o1XKN1BC84kFyWkfvRgAACgQWbajk3JAFAIAOJgAAAJ4fe"
    "JynqGzsa/IzVEoSy0qBgoAvatnoKSQmpecn5KZl26rVFqSpmuhZI/NBiLNBwAy/SHEAKKiogAAAAA="
)

# Live S7-1200 G2 EXPLORE response for optimized DB "Data_block_1" (DB25), from
# the IdentES stream onward. Contains several preset-dict streams; the parser
# must skip IdentES (0x5814b03b) and target the interface dict (0x66052b13).
_DB_INTERFACE_BLOB = base64.b64decode(
    "eH1YFLA7rZXBToQwEIZfxezdUCosECtmdRc9oAfhBRqZYJPSGrZoeHtni2ukS0+7lx6+djqdmX+m"
    "p4mgNhGbwehXK5Gj73/ECSejJKTrNCZhlJCUuP18WCvDu0/7xprcrY4mYZTF6xRtktVVHXo49fAb"
    "D488PPbwxMPTZR5cfkCdqfLCVfkbSOB7eNSDMnlMWDADbKu/ldS8eRZ7o/sRR9T9NbllgcuZ1XPJ"
    "VTvwFkr4ApnjP7VAWc37FkzBOyHHvMLpRMgTZcEMs11VDOrdYBBcCjNOphRvXNzA43Mn00nH8aZp"
    "xGRY4suxKvAgFO9Hm7IDeoEOYylBteYDmzz7LeGf/n8AgprvX6OhQEAVAKOTcAAUAIZ3mAAAAnh9"
    "ZgUrE42Y224bOQyGX8XwPWGROi+aAE1TYHvVxWLRW0NHINhsncZOEezTl5qjPVM3vUlGE/ET+YtD"
    "Snm7Mrp1YbzckNuLDrTZ9T1o2Lv7u77icbL3O4TISRhez/PD9K+m75kUz/77A881pEhrb9WUA0Mz"
    "udneffry8Y8W/T423/a4Szln8p5AIQpQpAyEEA1QwWKKTsmjHepPOyuV1xPdbHtNWWbVTj3cNPpX"
    "TjT5h9ldrohX320I+q4h9zoiEk/idlUeb7ZfiGu66NNp+MoGuvK20QfxSYmpnbUoedLdh/v3+n2T"
    "8p9nrl2s/Sa98GchijEhGw8YkwelLYE30oJ1yQWSJsla2ejPh2NLhg3DVZZaqhK5oVkHqlQCV50C"
    "4ZRxwjprq9m2PTqzyRyFpGLA6aJBZV/ABRVA+sCvtYjV0tLG5GBTVR4cEq/jLPKTRJDCCMxBoo+4"
    "tJEuVO+KBJfQgLIhQ6iSQyJHhLy2dnZpQ6FaVF6ArDlyPK6AjzlweNkEgw6VXsXD0aAK0UJIxPFE"
    "ChxPSWC1z84a61Gs1qmOs0xKDcJGVhprBC+UZc29taiVMxRXGkShCvISxiPbRG1Za68guFyCSCkI"
    "HZY2WlcKaAyw4xyP4um+mgop8/uSpE5FLm1SirypMUCKVYIKQYEzPPSBXIq2RGlrZ7Mbs+d2rtzt"
    "KLFswknYLJzP4J2roGQUEKRLQNJirlkgJ9f2rLe3xByqbfsUNI7V5lgey4ndLHtuHPvwcjoMlXUu"
    "X13if26Mvtr6ztNzGo20p5fH4/7YTpn88/C0Tw/p8ToQByCKFVHO/p2e2tFlX5/Lt/1/h+bqEqgn"
    "oBmJ7NF3TqMVV43cf5/2f326X5LcSJI0ktQVkp5ID78kGTWS9IphJkb+JcNPcZkVw46MdPh6vCLQ"
    "rDi5keSuxOVG3jN3w0P4nyt2eVN3NQbZiulPsX7E8lWs3Rf4ahrexJox5QiXwPanEfj12Dv5cGTo"
    "KVyVEe2oI8nOTbmi4qzmM18XTr9BJTFq2roe84Y7y+Z40S6+X3acqb10nWXdRbpjYTO4hqGWWDy6"
    "BPFNam5cnTeHzWEwnQduHqCneSDPno2an705s9bnA3GGIjoz6TJtGph++d0gzW13/e22jcVvNXL6"
    "R0wvkRjmt9LHv6ZSuOvuxu8WV7LbHxNPf/Kjk3JAFAEAEJgAAAJ4fTxVQ2oDAAAAAAEAo6E/QBUA"
    "o7sMQBQAo70tQBQAo70lQBQAo5NaAAEAo5NlQBQAoqKiAAAAAA=="
)


def test_parse_ident_container_addresses():
    xml = (
        "<IdentContainer>"
        '<Ident Name="input_1" Scope="Global" LID="10"><SimpleType>Bool</SimpleType>'
        '<Access SubClass="SimpleAccess"><SimpleAccess BitNumber="0" ByteNumber="0"'
        ' Width="Bit" Range="Input" /></Access></Ident>'
        '<Ident Name="mtag_word" Scope="Global" LID="13"><SimpleType>Word</SimpleType>'
        '<Access SubClass="SimpleAccess"><SimpleAccess ByteNumber="102"'
        ' Width="Word" Range="Memory" /></Access></Ident>'
        "</IdentContainer>"
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


def test_parse_block_interface_types():
    # <Member> types are RID references into the SoftDataType table; a RID
    # outside the 0x0200_00XX namespace is a complex type left as raw hex.
    xml = (
        "<BlockInterface><Part><Payload><Root>"
        '<Member ID="51" Name="flag" RID="0x02000001" StdO="0" LID="9" />'
        '<Member ID="53" Name="speed" RID="0x02000005" StdO="16" LID="12" />'
        '<Member ID="54" Name="gain" RID="0x02000008" StdO="32" LID="14" />'
        '<Member ID="60" Name="timer" RID="0x0300abcd" StdO="48" LID="20" />'
        "</Root></Payload></Part></BlockInterface>"
    )
    assert parse_block_interface(xml) == [
        Member("flag", "Bool", 9, 0, 0x02000001),
        Member("speed", "Int", 12, 16, 0x02000005),
        Member("gain", "Real", 14, 32, 0x02000008),
        Member("timer", "0x0300ABCD", 20, 48, 0x0300ABCD),
    ]


def test_parse_block_interface_fb_sections():
    # FB/OB interfaces are organized in sections; the section-header <Member>s
    # (Input/Static, no RID) must be skipped, real members tagged with their
    # section. Complex members carry a ready-made ``Type`` attribute (arrays),
    # scalar ones resolve from the RID.
    xml = (
        "<BlockInterface><Payload><Root>"
        '<Member ID="2" Name="Input" SubPartIndex="0" StdO="0" />'
        '<Member ID="5" Name="Static" SubPartIndex="3" StdO="0" />'
        "</Root></Payload>"
        "<SubParts>"
        '<Part Kind="InputSection"><Payload><Member>'
        '<Member ID="51" Name="puls_start_stop" RID="0x02000001" StdO="0" LID="9" />'
        "</Member></Payload></Part>"
        '<Part Kind="StaticSection"><Payload><Member>'
        '<Member ID="61" Name="num_step" RID="0x02000005" StdO="0" LID="19" />'
        '<Member ID="62" Name="timers" RID="0x0201001F"'
        ' Type="Array[0..5] of IEC_TIMER" StdO="16" LID="20" />'
        '<Member ID="63" Name="echo" RID="0x02010001"'
        ' Type="Array[0..2] of Bool" StdO="784" LID="21" />'
        "</Member></Payload></Part>"
        "</SubParts></BlockInterface>"
    )
    assert parse_block_interface(xml) == [
        Member("puls_start_stop", "Bool", 9, 0, 0x02000001, "Input"),
        Member("num_step", "Int", 19, 0, 0x02000005, "Static"),
        Member("timers", "Array[0..5] of IEC_TIMER", 20, 16, 0x0201001F, "Static"),
        Member("echo", "Array[0..2] of Bool", 21, 784, 0x02010001, "Static"),
    ]


def test_parse_block_interface_udt_member_and_embedded_type():
    # A member of a UDT type carries a readable ``Type`` ("MyUdt", TIA quotes)
    # and a RID in the UDT object namespace (0x91......). The interface also
    # embeds the UDT's own definition under a nested <Part Kind="DataTypeSource">;
    # those members describe the type, not the block, and must be skipped.
    xml = (
        '<BlockInterface><Part Kind="DBSource"><Payload><Root>'
        '<Member ID="51" Name="flag" RID="0x02000001" StdO="0" LID="9" />'
        '<Member ID="52" Name="valve" RID="0x91000001"'
        ' Type="&quot;MyUdt&quot;" StdO="16" LID="10" />'
        "</Root></Payload>"
        '<SubParts><Part Kind="DataTypeSource"><Payload><Root>'
        '<Member ID="60" Name="inner_field" RID="0x02000005" StdO="0" LID="1" />'
        "</Root></Payload></Part></SubParts>"
        "</Part></BlockInterface>"
    )
    assert parse_block_interface(xml) == [
        Member("flag", "Bool", 9, 0, 0x02000001, ""),
        Member("valve", '"MyUdt"', 10, 16, 0x91000001, ""),
    ]


def test_block_interface_from_live_g2_db():
    members = block_interface_from_explore(_DB_INTERFACE_BLOB)
    got = [(m.name, m.data_type) for m in members]
    assert got == [
        ("selettore_man_auto", "Bool"),
        ("puls_start_stop_ciclo", "Bool"),
        ("setpoint_freq_motore", "Int"),
        ("kp_PID", "Real"),
        ("ki_PID", "Real"),
        ("kd_PID", "Real"),
        ("cons_motore", "Bool"),
        ("retroazione_motore", "Int"),
        ("temperatura_motore", "Int"),
        ("tensione_misurata", "Real"),
        ("corrente_misurata", "Real"),
    ]


def test_datablocks_from_explore_standard_zlib():
    # PlcContentInfo is a standard zlib stream (78 da) embedded in a larger BLOB;
    # trailing bytes follow it, so decoding must raw-inflate and tolerate them.
    xml = (
        b'<?xml version="1.0" encoding="utf-8"?><PlcContentInfo>'
        b'<Entity Id="Block" Rid="2316173337"><Header Name="Data_block_1"'
        b' Number="25" Type="DB" /></Entity>'
        b'<Entity Id="Block" Rid="2316435466"><Header Name="FB_Macchina"'
        b' Number="10" Type="FB" /></Entity>'
        b"</PlcContentInfo>"
    )
    stream = zlib.compress(xml, 9)  # -> 78 da header
    assert stream[:2] == b"\x78\xda"
    payload = b"\x00\x01prefix" + stream + b"trailing-blob-bytes\xff\x00"
    assert datablocks_from_explore(payload) == [
        DataBlock("Data_block_1", 25, 2316173337),
    ]


def test_datablocks_from_explore_no_stream_returns_empty():
    assert datablocks_from_explore(b"no zlib here") == []
