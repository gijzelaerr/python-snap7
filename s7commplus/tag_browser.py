"""Parse symbolic I/Q/M tags from decompressed S7CommPlus EXPLORE responses.

S7-1200/1500 PLCs answer an EXPLORE request for the I/Q/M areas with a
zlib blob compressed against the ``IntfDescTag`` preset dictionary
(Adler-32 ``0xce9b821b``). Once decompressed with
:func:`s7commplus.blob_decompressor.find_and_decompress`, the payload is a
clean ``<IdentContainer>`` XML document::

    <IdentContainer>
      <Ident Name="mtag_word" Scope="Global" LID="13">
        <SimpleType>Word</SimpleType>
        <Access SubClass="SimpleAccess">
          <SimpleAccess ByteNumber="102" Width="Word" Range="Memory" />
        </Access>
      </Ident>
    </IdentContainer>

This module turns that XML into :class:`Tag` records with TIA-style
addresses (``%I0.0``, ``%Q0.1``, ``%MB100``, ``%MW102``, ``%MD104``).

Validated end-to-end against a live S7-1200 G2 (FW V4.1).
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass

from .blob_decompressor import find_and_decompress

# EXPLORE relation IDs per area (S7-1200 V3 / FW V4.x).
AREA_RID = {"I": 80, "Q": 81, "M": 82}

# <SimpleAccess Range="..."> -> TIA area letter.
_RANGE_LETTER = {"Input": "I", "Output": "Q", "Memory": "M"}
# <SimpleAccess Width="..."> -> TIA address suffix for non-bit widths.
_WIDTH_SUFFIX = {"Byte": "B", "Word": "W", "DWord": "D", "LWord": "L"}


@dataclass
class Tag:
    """A symbolic PLC tag resolved from an EXPLORE response."""

    name: str
    data_type: str          # <SimpleType>, e.g. Bool / Byte / Word / DWord
    address: str            # TIA syntax, e.g. %I0.0 / %MB100 / %MW102
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
    """Decompress a raw EXPLORE payload and parse its symbolic tags.

    ``explore_payload`` is the (possibly multi-fragment) EXPLORE response for
    one area. Returns an empty list if the payload contains no preset-dict
    zlib stream.
    """
    xml_text = find_and_decompress(explore_payload)
    if not xml_text:
        return []
    return parse_ident_container(xml_text)
