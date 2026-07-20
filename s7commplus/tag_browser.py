"""Parse symbolic tags and block interfaces from S7CommPlus EXPLORE responses.

S7-1200/1500 PLCs answer an EXPLORE request with a zlib blob compressed
against a Siemens preset dictionary. Once decompressed with
:func:`s7commplus.blob_decompressor.decompress_blob`, the payload is clean
XML. Two shapes are handled here:

* **I/Q/M areas** -> ``<IdentContainer>`` with ``<Ident>`` entries that carry
  a direct ``<SimpleType>`` and ``<SimpleAccess>`` address (dict
  ``IntfDescTag`` / Adler-32 ``0xce9b821b``). Parsed into :class:`Tag`.

* **Data blocks / FBs** -> ``<BlockInterface>`` with ``<Member>`` entries whose
  data type is a *reference* (``RID="0x0200_00XX"``) into the Siemens
  SoftDataType table, not an inline string (dict ``DebugInfo_IntfDesc`` /
  Adler-32 ``0x66052b13``). Parsed into :class:`Member`.

Validated end-to-end against a live S7-1200 G2 (FW V4.1): I/Q/M tags and an
optimized DB (``Data_block_1``, 11 members, names + Bool/Int/Real types).
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
import zlib
from dataclasses import dataclass, field

from .blob_decompressor import decompress_blob

# ---------------------------------------------------------------------------
# I/Q/M symbolic tags (<IdentContainer>)
# ---------------------------------------------------------------------------

# EXPLORE relation IDs per area (S7-1200 V3 / FW V4.x).
AREA_RID = {"I": 80, "Q": 81, "M": 82}

# <SimpleAccess Range="..."> -> TIA area letter.
_RANGE_LETTER = {"Input": "I", "Output": "Q", "Memory": "M"}
# <SimpleAccess Width="..."> -> TIA address suffix for non-bit widths.
_WIDTH_SUFFIX = {"Byte": "B", "Word": "W", "DWord": "D", "LWord": "L"}


@dataclass
class Tag:
    """A symbolic I/Q/M tag resolved from an EXPLORE response."""

    name: str
    data_type: str  # <SimpleType>, e.g. Bool / Byte / Word / DWord
    address: str  # TIA syntax, e.g. %I0.0 / %MB100 / %MW102
    lid: int
    byte_offset: int
    bit_offset: int | None


def _address(rng: str, width: str, byte_no: int, bit_no: int | None) -> str:
    letter = _RANGE_LETTER.get(rng, "?")
    if width == "Bit":
        return f"%{letter}{byte_no}.{bit_no or 0}"
    return f"%{letter}{_WIDTH_SUFFIX.get(width, '')}{byte_no}"


def parse_ident_container(xml_text: str) -> list[Tag]:
    """Parse a decompressed ``<IdentContainer>`` document into :class:`Tag`s."""
    tags: list[Tag] = []
    for ident in ET.fromstring(xml_text).findall("Ident"):
        acc = ident.find("./Access/SimpleAccess")
        if acc is None:
            continue  # only SimpleAccess idents carry a direct I/Q/M address
        byte_no = int(acc.get("ByteNumber", "0"))
        bit_raw = acc.get("BitNumber")
        bit_no = int(bit_raw) if bit_raw is not None else None
        tags.append(
            Tag(
                name=ident.get("Name", ""),
                data_type=ident.findtext("SimpleType", default=""),
                address=_address(acc.get("Range", ""), acc.get("Width", ""), byte_no, bit_no),
                lid=int(ident.get("LID", "0")),
                byte_offset=byte_no,
                bit_offset=bit_no,
            )
        )
    return tags


def tags_from_explore(explore_payload: bytes) -> list[Tag]:
    """Decompress a raw I/Q/M EXPLORE payload and parse its symbolic tags.

    Returns an empty list if the payload contains no preset-dict zlib stream.
    """
    pos = _find_preset_stream(explore_payload, _IDENT_ADLER)
    if pos is None:
        return []
    return parse_ident_container(decompress_blob(explore_payload, offset=pos))


# ---------------------------------------------------------------------------
# Data-block / FB interfaces (<BlockInterface>)
# ---------------------------------------------------------------------------

# Adler-32 of the ``IntfDescTag`` preset dict (I/Q/M symbols).
_IDENT_ADLER = 0xCE9B821B
# Adler-32 of interface-description preset dicts. ``DebugInfo_IntfDesc`` carries
# the optimized (symbolic-access) block interface; ``IntfDesc`` the standard one.
_INTFDESC_ADLERS = (0x66052B13, 0x4B8416F0)

# Siemens SoftDataType ids, from thomas-v2/S7CommPlusDriver Core/Softdatatype.cs
# (LGPL-3.0). A <Member> type is a RID of the form 0x0200_00XX where XX is the
# SoftDataType id below.
SOFTDATATYPE = {
    0: "Void",
    1: "Bool",
    2: "Byte",
    3: "Char",
    4: "Word",
    5: "Int",
    6: "DWord",
    7: "DInt",
    8: "Real",
    9: "Date",
    10: "TimeOfDay",
    11: "Time",
    12: "S5Time",
    13: "S5Count",
    14: "DateAndTime",
    15: "InternetTime",
    16: "Array",
    17: "Struct",
    18: "EndStruct",
    19: "String",
    20: "Pointer",
    21: "MultiFB",
    22: "Any",
    23: "BlockFB",
    24: "BlockFC",
    25: "BlockDB",
    26: "BlockSDB",
    28: "Counter",
    29: "Timer",
    30: "IEC_Counter",
    31: "IEC_Timer",
    37: "BlockUDT",
    40: "BBool",
    48: "LReal",
    49: "ULInt",
    50: "LInt",
    51: "LWord",
    52: "USInt",
    53: "UInt",
    54: "UDInt",
    55: "SInt",
    61: "WChar",
    62: "WString",
    63: "Variant",
    64: "LTime",
    65: "LTimeOfDay",
    66: "LDT",
    67: "DTL",
}


@dataclass
class Member:
    """A single variable inside a data block or FB/OB interface."""

    name: str
    data_type: str  # readable type: SoftDataType name or the inline complex type
    lid: int
    offset: int  # StdO: standard (non-optimized) byte offset
    rid: int  # raw type RID
    section: str = ""  # Input/Output/InOut/Static/Temp/Constant (FB/OB); "" for a DB
    fields: list[Member] = field(default_factory=list)  # sub-members for a UDT/Struct type


def _member_type(member: ET.Element) -> str:
    """Resolve a ``<Member>``'s data type to a readable name.

    Complex members (arrays, UDTs, strings, structs) already carry a ready-made
    ``Type`` attribute (e.g. ``Array[0..5] of IEC_TIMER``). Scalar elementary
    members carry only a RID of the form ``0x0200_00XX`` whose low byte is a
    Siemens SoftDataType id. (Arrays use ``0x0201_00XX``, hence the explicit
    ``Type``; the raw RID stays available on :attr:`Member.rid`.)
    """
    explicit = member.get("Type")
    if explicit:
        return explicit
    try:
        rid = int(member.get("RID", "0") or "0", 16)
    except ValueError:
        return ""
    if (rid & 0xFFFF0000) == 0x02000000:
        return SOFTDATATYPE.get(rid & 0xFFFF, f"SoftType#{rid & 0xFFFF}")
    return f"0x{rid:08X}"


def parse_block_interface(xml_text: str) -> list[Member]:
    """Parse a decompressed ``<BlockInterface>`` document into :class:`Member`s.

    Works for DB, FB, OB and UDT interfaces. The block's own variables come from
    its primary ``<Part>`` — directly under ``<Payload><Root>`` for a flat
    DB/UDT, or from the ``<Part Kind="*Section">`` entries for an FB/OB. Members
    are returned in declaration order, each tagged with its section
    (Input/Output/... for FB/OB; empty for DB/UDT).

    When a member is of a UDT (or other structured type), the interface embeds
    that type's definition under the primary part's ``<SubParts>``; the member's
    ``SubPartIndex`` selects it. Such members are expanded recursively into
    :attr:`Member.fields`. Library types (e.g. ``IEC_TIMER``) are referenced but
    not inlined, so they expand to no fields.
    """
    root = ET.fromstring(xml_text)
    primary = root.find("Part")  # first top-level Part = the block's own source
    if primary is None:
        return []
    return _parse_source_part(primary)


def _parse_source_part(part: ET.Element) -> list[Member]:
    """Parse one source ``<Part>`` (DBSource/BlockSource/DataTypeSource)."""
    sub_el = part.find("SubParts")
    subparts = list(sub_el) if sub_el is not None else []  # index-addressable

    members: list[Member] = []
    # Flat DB/UDT: variables are direct <Member> children of <Payload><Root>.
    root_el = part.find("./Payload/Root")
    if root_el is not None:
        for m in root_el.findall("Member"):
            if m.get("RID") is not None:
                members.append(_build_member(m, "", subparts))
    # FB/OB: variables live in the <Part Kind="*Section"> entries of <SubParts>.
    for sp in subparts:
        kind = sp.get("Kind", "")
        if not kind.endswith("Section"):
            continue
        section = kind[: -len("Section")]
        for m in sp.findall("./Payload/Member/Member"):
            if m.get("RID") is not None:
                members.append(_build_member(m, section, subparts))
    return members


def _build_member(m: ET.Element, section: str, subparts: list) -> Member:
    """Build a :class:`Member`, expanding a structured type via ``SubPartIndex``."""
    member = Member(
        name=m.get("Name", ""),
        data_type=_member_type(m),
        lid=int(m.get("LID", "0")),
        offset=int(m.get("StdO", "0")),
        rid=int(m.get("RID", "0") or "0", 16),
        section=section,
    )
    spi = m.get("SubPartIndex")
    if spi is not None:
        idx = int(spi)
        # Only an inlined type definition (a *Source part) carries sub-members;
        # a *Section index or a library reference expands to nothing.
        if 0 <= idx < len(subparts) and subparts[idx].get("Kind", "").endswith("Source"):
            member.fields = _parse_source_part(subparts[idx])
    return member


def block_interface_from_explore(explore_payload: bytes) -> list[Member]:
    """Decompress a block EXPLORE payload and parse its interface members.

    The EXPLORE response for a block RID bundles several preset-dict streams
    (IdentES, interface, comments, ...). This targets the interface dictionary
    specifically rather than taking the first stream. Returns an empty list if
    no interface stream is present.
    """
    for adler in _INTFDESC_ADLERS:
        pos = _find_preset_stream(explore_payload, adler)
        if pos is not None:
            return parse_block_interface(decompress_blob(explore_payload, offset=pos))
    return []


# ---------------------------------------------------------------------------
# shared helpers
# ---------------------------------------------------------------------------


def _find_preset_stream(data: bytes, adler: int) -> int | None:
    """Return the offset of the first preset-dict zlib stream matching ``adler``.

    A block EXPLORE response contains multiple ``78 xx`` FDICT streams; callers
    need the one for a specific dictionary, not merely the first.
    """
    i = 0
    end = len(data) - 6
    while i < end:
        if data[i] == 0x78 and (data[i + 1] & 0x20) and int.from_bytes(data[i + 2 : i + 6], "big") == adler:
            return i
        i += 1
    return None


@dataclass
class DataBlock:
    """A data block advertised in the PlcContentInfo listing."""

    name: str
    number: int
    rid: int


def datablocks_from_explore(wildcard_payload: bytes) -> list[DataBlock]:
    """Parse the DB list from a ``0x8A11FFFF`` wildcard EXPLORE response.

    PlcContentInfo is a *standard* zlib stream (``78 da``) embedded in a larger
    BLOB, so it is raw-inflated (the Adler-32 trailer would fail on the trailing
    bytes). Returns only ``Type="DB"`` blocks.
    """
    pos = wildcard_payload.find(b"\x78\xda")
    if pos < 0:
        return []
    try:
        xml_bytes = zlib.decompressobj(wbits=-15).decompress(wildcard_payload[pos + 2 :])
    except zlib.error:
        return []
    dbs: list[DataBlock] = []
    for entity in ET.fromstring(xml_bytes.decode("utf-8")).findall('.//Entity[@Id="Block"]'):
        header = entity.find("Header")
        if header is None or header.get("Type") != "DB":
            continue
        try:
            dbs.append(
                DataBlock(
                    name=header.get("Name", ""),
                    number=int(header.get("Number", "0")),
                    rid=int(entity.get("Rid", "0")),
                )
            )
        except ValueError:
            continue
    return dbs
