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

# Live S7-1200 G2 EXPLORE response for DB "Data_block_1" after adding a member of
# a user UDT ("elettrovalvola"), from the interface stream onward. The blob
# bundles the DB interface and the UDT's own definition; the UDT member is
# expanded into Member.fields.
_DB_UDT_INTERFACE_BLOB = base64.b64decode(
    "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"
    "AKOTZUAUAKKiogAAAAA="
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
        '<BlockInterface><Part Kind="BlockSource"><Payload><Root>'
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
        "</SubParts></Part></BlockInterface>"
    )
    assert parse_block_interface(xml) == [
        Member("puls_start_stop", "Bool", 9, 0, 0x02000001, "Input"),
        Member("num_step", "Int", 19, 0, 0x02000005, "Static"),
        Member("timers", "Array[0..5] of IEC_TIMER", 20, 16, 0x0201001F, "Static"),
        Member("echo", "Array[0..2] of Bool", 21, 784, 0x02010001, "Static"),
    ]


def test_parse_block_interface_udt_member_expands_fields():
    # A UDT member carries a readable ``Type`` ("MyUdt", TIA quotes), a RID in
    # the UDT object namespace (0x91......) and a ``SubPartIndex`` pointing at the
    # UDT's definition embedded under <SubParts>. That definition is expanded
    # into Member.fields, not surfaced as top-level members.
    xml = (
        '<BlockInterface><Part Kind="DBSource"><Payload><Root>'
        '<Member ID="51" Name="flag" RID="0x02000001" StdO="0" LID="9" />'
        '<Member ID="52" Name="valve" RID="0x91000001" Type="&quot;MyUdt&quot;"'
        ' SubPartIndex="0" StdO="16" LID="10" />'
        "</Root></Payload>"
        '<SubParts><Part Kind="DataTypeSource"><Payload><Root>'
        '<Member ID="60" Name="open_cmd" RID="0x02000001" StdO="0" LID="1" />'
        '<Member ID="61" Name="level" RID="0x02000005" StdO="16" LID="2" />'
        "</Root></Payload></Part></SubParts>"
        "</Part></BlockInterface>"
    )
    assert parse_block_interface(xml) == [
        Member("flag", "Bool", 9, 0, 0x02000001, ""),
        Member(
            "valve",
            '"MyUdt"',
            10,
            16,
            0x91000001,
            "",
            fields=[
                Member("open_cmd", "Bool", 1, 0, 0x02000001, ""),
                Member("level", "Int", 2, 16, 0x02000005, ""),
            ],
        ),
    ]


def test_block_interface_from_live_g2_db_with_udt():
    members = block_interface_from_explore(_DB_UDT_INTERFACE_BLOB)
    # 12 top-level members; the embedded UDT definition is not surfaced flat.
    assert len(members) == 12
    valve = members[-1]
    assert (valve.name, valve.data_type, valve.rid) == (
        "elettrovalvola_1",
        '"elettrovalvola"',
        0x91000001,
    )
    assert [(f.name, f.data_type) for f in valve.fields] == [
        ("fc_apertura", "Bool"),
        ("fc_chiusura", "Bool"),
        ("stato_ev", "Int"),
        ("allarme_ev", "Int"),
        ("cons_ev", "Bool"),
        ("perc_apertura", "Real"),
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
