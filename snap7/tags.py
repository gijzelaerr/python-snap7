"""Tag addressing for S7 PLCs.

A :class:`Tag` represents a typed value at a specific S7 address.  Tags can
be created from:

- A PLC4X-style address string: ``Tag.from_string("DB1.DBX0.0:BOOL")``
- A CSV file: :func:`load_csv`
- A JSON file: :func:`load_json`
- A TIA Portal XML export: :func:`load_tia_xml`
- A live PLC browse: ``{t.name: t for t in client.browse()}``

Reading and writing tags is done via :meth:`~snap7.client.Client.read_tag`
and :meth:`~snap7.client.Client.write_tag`.

Example::

    from s7 import Client
    from s7.tags import load_tia_xml

    client = Client()
    client.connect("192.168.1.10", 0, 1)

    # Ad-hoc tag access
    speed = client.read_tag("DB1.DBD0:REAL")

    # Named tags from a file
    tags = load_tia_xml("db1.xml")
    temperature = client.read_tag(tags["Motor.Temperature"])
"""

import csv
import io
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Union

from .type import Area

# Type name → byte size for fixed-size types
_TYPE_SIZE: dict[str, int] = {
    "BOOL": 1,
    "BYTE": 1,
    "SINT": 1,
    "USINT": 1,
    "CHAR": 1,
    "INT": 2,
    "UINT": 2,
    "WORD": 2,
    "WCHAR": 2,
    "DATE": 2,
    "DINT": 4,
    "UDINT": 4,
    "DWORD": 4,
    "REAL": 4,
    "TIME": 4,
    "TOD": 4,
    "LINT": 8,
    "ULINT": 8,
    "LWORD": 8,
    "LREAL": 8,
    "LTIME": 8,
    "LTOD": 8,
    "LDT": 8,
    "DT": 8,
    "DTL": 12,
}

# Variable-length string types: STRING[n], WSTRING[n], FSTRING[n]
_STRING_RE = re.compile(r"^(STRING|WSTRING|FSTRING)\[(\d+)]$", re.IGNORECASE)


@dataclass
class Tag:
    """A typed reference to a value in a PLC data area.

    Attributes:
        area: The S7 memory area (DB, MK, PE, PA).
        db_number: DB number (0 for non-DB areas).
        byte_offset: Start byte offset within the area.
        bit: Bit index (0-7) for BOOL tags; 0 for others.
        datatype: S7 data type name (``BOOL``, ``INT``, ``REAL``, ``STRING[20]``, ...).
        count: Array count (1 = scalar, >1 = array).
        name: Optional tag name for debugging/logging.
    """

    area: Area
    db_number: int
    byte_offset: int
    datatype: str
    bit: int = 0
    count: int = 1
    name: str = ""

    @property
    def size(self) -> int:
        """Total byte size of this tag (including array count)."""
        upper = self.datatype.upper()
        match = _STRING_RE.match(upper)
        if match:
            kind, length = match.group(1), int(match.group(2))
            if kind == "FSTRING":
                elem = length
            elif kind == "STRING":
                elem = 2 + length
            else:  # WSTRING
                elem = 4 + length * 2
        elif upper in _TYPE_SIZE:
            elem = _TYPE_SIZE[upper]
        else:
            raise ValueError(f"Unknown S7 type: {self.datatype}")
        return elem * self.count

    @classmethod
    def from_string(cls, address: str, name: str = "") -> "Tag":
        """Parse a PLC4X-style tag address string.

        Supported formats::

            DB1.DBX0.0:BOOL          # bit in data block
            DB1.DBB10:BYTE           # byte
            DB1.DBW10:INT            # word
            DB1.DBD10:REAL           # double word as real
            DB1:10:INT               # short form (DB 1, offset 10, INT)
            DB1:10:STRING[20]        # variable-length string
            DB1:10:REAL[5]           # array of 5 REALs
            M10.5:BOOL               # Merker bit
            MW20:WORD                # Merker word
            I0.0:BOOL                # input bit
            Q0.0:BOOL                # output bit

        Args:
            address: Tag address string.
            name: Optional name to store on the Tag.

        Returns:
            A parsed :class:`Tag`.

        Raises:
            ValueError: If the address format is not recognised.
        """
        raw = address.strip()
        s = raw.upper()

        # Extract type (optional array)
        if ":" not in s:
            raise ValueError(f"Tag address must include type (e.g. 'DB1.DBX0.0:BOOL'): {address}")

        # Split carefully — short form `DB1:10:INT` has two colons
        parts = s.split(":")

        count = 1
        if len(parts) == 3 and parts[0].startswith("DB"):
            # Short form: DB<n>:<offset>:<type>
            db_part, offset_part, type_part = parts
            db_number = int(db_part[2:])
            byte_offset, bit = _parse_offset(offset_part)
            datatype, count = _parse_type(type_part)
            return cls(
                area=Area.DB, db_number=db_number, byte_offset=byte_offset, bit=bit, datatype=datatype, count=count, name=name
            )

        if len(parts) != 2:
            raise ValueError(f"Invalid tag address: {address}")

        addr_str, type_part = parts
        datatype, count = _parse_type(type_part)

        # Handle leading % (optional)
        if addr_str.startswith("%"):
            addr_str = addr_str[1:]

        # Data block: DB<n>.DBX/DBB/DBW/DBD<offset>[.<bit>]
        if addr_str.startswith("DB") and "." in addr_str:
            db_part, addr_part = addr_str.split(".", 1)
            db_number = int(db_part[2:])
            byte_offset, bit = _parse_db_address(addr_part)
            return cls(
                area=Area.DB, db_number=db_number, byte_offset=byte_offset, bit=bit, datatype=datatype, count=count, name=name
            )

        # Merker (flag): M<offset>[.<bit>] or MB/MW/MD<offset>
        if addr_str.startswith("M"):
            byte_offset, bit = _parse_simple_address(addr_str[1:])
            return cls(area=Area.MK, db_number=0, byte_offset=byte_offset, bit=bit, datatype=datatype, count=count, name=name)

        # Input: I<offset>[.<bit>] or IB/IW/ID<offset>
        if addr_str.startswith("I"):
            byte_offset, bit = _parse_simple_address(addr_str[1:])
            return cls(area=Area.PE, db_number=0, byte_offset=byte_offset, bit=bit, datatype=datatype, count=count, name=name)

        # Output: Q<offset>[.<bit>] or QB/QW/QD<offset>
        if addr_str.startswith("Q"):
            byte_offset, bit = _parse_simple_address(addr_str[1:])
            return cls(area=Area.PA, db_number=0, byte_offset=byte_offset, bit=bit, datatype=datatype, count=count, name=name)

        raise ValueError(f"Unsupported tag address: {address}")


def _parse_type(type_part: str) -> tuple[str, int]:
    """Parse ``INT`` or ``INT[5]`` into (datatype, count)."""
    type_part = type_part.strip()
    if "[" in type_part and type_part.endswith("]"):
        # Could be STRING[20] (length) or INT[5] (array) — distinguish by type
        base = type_part[: type_part.index("[")]
        if base.upper() in ("STRING", "WSTRING", "FSTRING"):
            return type_part, 1  # STRING[20] is a scalar with size hint
        count = int(type_part[type_part.index("[") + 1 : -1])
        return base, count
    return type_part, 1


def _parse_offset(s: str) -> tuple[int, int]:
    """Parse ``10`` or ``10.5`` into (byte_offset, bit)."""
    if "." in s:
        b, bit = s.split(".")
        return int(b), int(bit)
    return int(s), 0


def _parse_db_address(s: str) -> tuple[int, int]:
    """Parse ``DBX10.5``, ``DBB10``, ``DBW10``, ``DBD10`` into (byte, bit)."""
    if s.startswith("DBX"):
        return _parse_offset(s[3:])
    if s.startswith(("DBB", "DBW", "DBD")):
        return int(s[3:]), 0
    raise ValueError(f"Invalid DB address: {s}")


def _parse_simple_address(s: str) -> tuple[int, int]:
    """Parse ``10.5``, ``10``, ``B10``, ``W10``, ``D10`` into (byte, bit)."""
    if s.startswith(("B", "W", "D")):
        return int(s[1:]), 0
    return _parse_offset(s)


# ---------------------------------------------------------------------------
# Loaders — all return dict[name, Tag]
# ---------------------------------------------------------------------------


def _read_source(source: Union[str, Path]) -> str:
    """Resolve *source* to text content (file path or inline)."""
    if isinstance(source, Path):
        return source.read_text()
    s = str(source)
    if "\n" in s:
        return s
    path = Path(s)
    if path.exists():
        return path.read_text()
    return s


def _make_tag(name: str, db: int, offset: str, datatype: str, bit: int = 0) -> Tag:
    """Build a Tag from dict-style fields (used by CSV/JSON loaders)."""
    byte_offset, parsed_bit = _parse_offset(str(offset))
    return Tag(
        area=Area.DB,
        db_number=int(db),
        byte_offset=byte_offset,
        bit=bit or parsed_bit,
        datatype=datatype,
        name=name,
    )


def load_csv(source: Union[str, Path]) -> dict[str, Tag]:
    """Load tags from a CSV file or string.

    Expected columns: ``tag``, ``db``, ``offset``, ``type``.
    Optional column: ``bit``.

    Args:
        source: Path to a CSV file, or inline CSV text.

    Returns:
        Dictionary mapping tag names to :class:`Tag` objects.
    """
    text = _read_source(source)
    reader = csv.DictReader(io.StringIO(text))
    tags: dict[str, Tag] = {}
    for row in reader:
        name = row["tag"].strip()
        bit_str = row.get("bit", "").strip() if row.get("bit") else ""
        bit = int(bit_str) if bit_str else 0
        tags[name] = _make_tag(name, int(row["db"]), row["offset"], row["type"], bit)
    return tags


def load_json(source: Union[str, Path]) -> dict[str, Tag]:
    """Load tags from a JSON file or string.

    Expected format: ``{"tag_name": {"db": N, "offset": M, "type": "T", "bit": B}, ...}``

    Args:
        source: Path to a JSON file, or inline JSON text.

    Returns:
        Dictionary mapping tag names to :class:`Tag` objects.
    """
    text = _read_source(source)
    data = json.loads(text)
    tags: dict[str, Tag] = {}
    for name, info in data.items():
        bit = int(info.get("bit", 0))
        tags[name] = _make_tag(name, int(info["db"]), info["offset"], info["type"], bit)
    return tags


def load_tia_xml(source: Union[str, Path]) -> dict[str, Tag]:
    """Load tags from a TIA Portal DB source XML export.

    TIA Portal exports DB definitions via right-click > "Generate source
    from blocks", producing XML with field names, offsets, and data types.

    Args:
        source: Path to an XML file exported from TIA Portal.

    Returns:
        Dictionary mapping tag names to :class:`Tag` objects.
    """
    import xml.etree.ElementTree as ET

    text = _read_source(source)
    root = ET.fromstring(text)

    # Extract DB number from attribute list
    db_number = 0
    for elem in root.iter():
        if elem.tag.endswith("AttributeList"):
            for child in elem:
                if child.tag.endswith("Number"):
                    try:
                        db_number = int(child.text or "0")
                    except ValueError:
                        pass
                    break

    # TIA type names → canonical S7 type names
    dt_map = {
        "Bool": "BOOL",
        "Byte": "BYTE",
        "Char": "CHAR",
        "Int": "INT",
        "Word": "WORD",
        "DInt": "DINT",
        "DWord": "DWORD",
        "Real": "REAL",
        "LReal": "LREAL",
        "SInt": "SINT",
        "USInt": "USINT",
        "UInt": "UINT",
        "UDInt": "UDINT",
        "String": "STRING",
        "WString": "WSTRING",
        "Date": "DATE",
        "Time": "TIME",
        "Time_Of_Day": "TOD",
        "Date_And_Time": "DT",
        "DTL": "DTL",
        "LWord": "LWORD",
        "LInt": "LINT",
        "ULInt": "ULINT",
        "LTime": "LTIME",
    }

    tags: dict[str, Tag] = {}
    for member in root.iter():
        tag_name = member.tag.rsplit("}", 1)[-1] if "}" in member.tag else member.tag
        if tag_name != "Member":
            continue
        name = member.get("Name", "")
        datatype = member.get("Datatype", "")
        offset_str = member.get("Offset", "0")
        if not name or not datatype:
            continue
        normalized = dt_map.get(datatype, datatype.upper())
        tags[name] = _make_tag(name, db_number, offset_str, normalized)

    return tags
