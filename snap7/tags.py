"""Tag addressing for S7 PLCs.

A :class:`Tag` represents a typed value at a specific S7 address.  Tags can
be created from:

- A PLC4X-style address string: ``PLC4XTag.parse("DB1.DBX0.0:BOOL")``
- A nodeS7-style address string: ``NodeS7Tag.parse("DB1,X0.0")``
- A dialect-agnostic dispatcher: ``parse_tag("DB1,R4")``
- A CSV file: :func:`load_csv`
- A JSON file: :func:`load_json`
- A TIA Portal XML export: :func:`load_tia_xml`
- A live PLC browse: ``{t.name: t for t in client.browse()}``

Two dialects are supported:

- **PLC4X / Siemens STEP7** — ``DB1.DBX0.0:BOOL``, ``DB1:10:REAL``,
  ``M10.5:BOOL``, ``MW20:WORD``. The colon-type suffix is required.
- **nodeS7 / pyS7** — ``DB1,X0.0``, ``DB1,R4``, ``M10.5``, ``IW22``.
  The comma separates DB from typecode; area shortcuts imply the type.

:func:`parse_tag` autodetects dialect from syntax markers (``,`` → nodeS7,
``:TYPE`` → PLC4X). Pass ``strict=False`` to allow bare short forms like
``M7.1`` or ``IW22`` (dispatched to the nodeS7 parser).

Example::

    from s7 import Client
    from s7.tags import parse_tag, load_tia_xml

    client = Client()
    client.connect("192.168.1.10", 0, 1)

    # Ad-hoc tag access (either dialect)
    speed = client.read_tag(parse_tag("DB1.DBD0:REAL"))
    speed = client.read_tag(parse_tag("DB1,R0"))

    # Named tags from a file
    tags = load_tia_xml("db1.xml")
    temperature = client.read_tag(tags["Motor.Temperature"])
"""

import csv
import io
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Union

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


# Area → PLC4X short prefix (used for __str__ output)
_AREA_PREFIX: dict[Area, str] = {
    Area.DB: "DB",
    Area.MK: "M",
    Area.PE: "I",
    Area.PA: "Q",
}


@dataclass
class Tag:
    """A typed reference to a value in a PLC data area.

    This is the canonical, dialect-agnostic representation used by the
    protocol layer. For parsing strings, prefer :class:`PLC4XTag`,
    :class:`NodeS7Tag`, or the :func:`parse_tag` dispatcher — each of
    those returns a subtype whose ``__str__`` round-trips to its source
    dialect.

    A Tag can address the PLC in two ways:

    1. **Byte-offset access** (classic, works on all S7 PLCs) — uses
       ``byte_offset`` and ``bit``. Supported on S7-300/400 and on
       S7-1200/1500 DBs with "Optimized block access" disabled.

    2. **Symbolic (LID-based) access** (S7CommPlus, for optimized DBs) —
       uses ``access_sequence`` (a list of LID values navigating the
       PLC's symbol tree) and optionally ``symbol_crc``. Required for
       S7-1200/1500 DBs with "Optimized block access" enabled.

    If ``access_sequence`` is set, it takes precedence over ``byte_offset``.

    Attributes:
        area: The S7 memory area (DB, MK, PE, PA).
        db_number: DB number (0 for non-DB areas).
        byte_offset: Start byte offset within the area (classic access).
        datatype: S7 data type name (``BOOL``, ``INT``, ``REAL``, ``STRING[20]``, ...).
        bit: Bit index (0-7) for BOOL tags; 0 for others.
        count: Array count (1 = scalar, >1 = array).
        name: Optional tag name for debugging/logging.
        access_sequence: LID path for S7CommPlus symbolic access (optimized DBs).
        symbol_crc: Symbol CRC for the PLC to validate layout version (0 = no check).
    """

    area: Area
    db_number: int
    byte_offset: int
    datatype: str
    bit: int = 0
    count: int = 1
    name: str = ""
    access_sequence: list[int] = field(default_factory=list)
    symbol_crc: int = 0

    @property
    def is_symbolic(self) -> bool:
        """Whether this Tag uses S7CommPlus symbolic (LID-based) access."""
        return bool(self.access_sequence)

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

    def __str__(self) -> str:
        """Render as PLC4X syntax (default dialect for bare Tags)."""
        return _render_plc4x(self)

    @classmethod
    def from_string(cls, address: str, name: str = "") -> "PLC4XTag":
        """Parse a PLC4X-style tag address string.

        Kept for backwards compatibility; equivalent to
        ``PLC4XTag.parse(address, name)``. For new code, prefer the
        explicit dialect parsers or :func:`parse_tag`.
        """
        return PLC4XTag.parse(address, name)

    @classmethod
    def from_access_string(
        cls,
        access_string: str,
        datatype: str,
        *,
        name: str = "",
        symbol_crc: int = 0,
        count: int = 1,
    ) -> "Tag":
        """Create a Tag from an S7CommPlus access string for optimized blocks.

        The access string is a dot-separated sequence of hex IDs representing
        the path through the PLC's symbol tree, e.g. ``"8A0E0001.A"`` (DB1,
        LID 0xA) for a variable in DB1 with optimized block access.

        This format is used for S7-1200/1500 DBs with "Optimized block access"
        enabled.  Byte offsets are unreliable for such blocks, so the PLC is
        addressed via the symbol tree instead.

        Args:
            access_string: Dot-separated hex IDs, e.g. ``"8A0E0001.A.1"``.
                The first ID is the AccessArea, remaining IDs are LIDs.
            datatype: S7 type name (e.g. ``"REAL"``, ``"BOOL"``, ``"INT[5]"``).
            name: Optional tag name.
            symbol_crc: Symbol CRC from the PLC (0 = no check).
            count: Array count (overridden if datatype includes ``[n]``).

        Returns:
            A :class:`Tag` configured for symbolic access.

        Raises:
            ValueError: If the access_string is not at least one hex component.
        """
        parts = access_string.strip().split(".")
        if not parts:
            raise ValueError(f"Invalid access string: {access_string}")
        ids = [int(p, 16) for p in parts]
        access_area = ids[0]
        lids = ids[1:]

        if access_area >= 0x8A0E0000:
            area = Area.DB
            db_number = access_area - 0x8A0E0000
        elif access_area == 82:  # NATIVE_THE_M_AREA_RID
            area = Area.MK
            db_number = 0
        elif access_area == 80:  # NATIVE_THE_I_AREA_RID
            area = Area.PE
            db_number = 0
        elif access_area == 81:  # NATIVE_THE_Q_AREA_RID
            area = Area.PA
            db_number = 0
        else:
            area = Area.DB
            db_number = 0

        resolved_type, parsed_count = _parse_type(datatype)
        final_count = parsed_count if parsed_count > 1 else count

        return cls(
            area=area,
            db_number=db_number,
            byte_offset=0,
            datatype=resolved_type,
            count=final_count,
            name=name,
            access_sequence=lids,
            symbol_crc=symbol_crc,
        )


@dataclass
class PLC4XTag(Tag):
    """A Tag parsed from PLC4X / Siemens STEP7 syntax.

    Example inputs accepted by :meth:`parse`:

    - ``DB1.DBX0.0:BOOL`` — DB bit
    - ``DB1.DBB10:BYTE`` — DB byte
    - ``DB1.DBW10:INT`` — DB word (signed)
    - ``DB1.DBD10:REAL`` — DB double word
    - ``DB1:10:INT`` — short form
    - ``DB1:10:STRING[20]`` — variable-length string
    - ``DB1:0:REAL[5]`` — array of 5 REALs
    - ``M10.5:BOOL``, ``MW20:WORD`` — marker bit / marker word
    - ``I0.0:BOOL``, ``Q0.0:BOOL`` — input / output bit
    - A leading ``%`` is accepted and ignored.

    The type suffix (``:TYPE``) is required. Use :class:`NodeS7Tag` for
    the shorter nodeS7 / pyS7 convention.
    """

    @classmethod
    def parse(cls, address: str, name: str = "") -> "PLC4XTag":
        """Parse a PLC4X-style tag address string.

        Raises:
            ValueError: If the address is malformed or lacks a type suffix.
        """
        raw = address.strip()
        s = raw.upper()

        if ":" not in s:
            raise ValueError(f"PLC4X tag address must include type (e.g. 'DB1.DBX0.0:BOOL'): {address}")

        parts = s.split(":")

        count = 1
        if len(parts) == 3 and parts[0].startswith("DB"):
            db_part, offset_part, type_part = parts
            db_number = int(db_part[2:])
            byte_offset, bit = _parse_offset(offset_part)
            datatype, count = _parse_type(type_part)
            return cls(
                area=Area.DB,
                db_number=db_number,
                byte_offset=byte_offset,
                bit=bit,
                datatype=datatype,
                count=count,
                name=name,
            )

        if len(parts) != 2:
            raise ValueError(f"Invalid PLC4X tag address: {address}")

        addr_str, type_part = parts
        datatype, count = _parse_type(type_part)

        if addr_str.startswith("%"):
            addr_str = addr_str[1:]

        if addr_str.startswith("DB") and "." in addr_str:
            db_part, addr_part = addr_str.split(".", 1)
            db_number = int(db_part[2:])
            byte_offset, bit = _parse_db_address(addr_part)
            return cls(
                area=Area.DB,
                db_number=db_number,
                byte_offset=byte_offset,
                bit=bit,
                datatype=datatype,
                count=count,
                name=name,
            )

        if addr_str.startswith("M"):
            byte_offset, bit = _parse_simple_address(addr_str[1:])
            return cls(area=Area.MK, db_number=0, byte_offset=byte_offset, bit=bit, datatype=datatype, count=count, name=name)

        if addr_str.startswith("I"):
            byte_offset, bit = _parse_simple_address(addr_str[1:])
            return cls(area=Area.PE, db_number=0, byte_offset=byte_offset, bit=bit, datatype=datatype, count=count, name=name)

        if addr_str.startswith("Q"):
            byte_offset, bit = _parse_simple_address(addr_str[1:])
            return cls(area=Area.PA, db_number=0, byte_offset=byte_offset, bit=bit, datatype=datatype, count=count, name=name)

        raise ValueError(f"Unsupported PLC4X tag address: {address}")

    def __str__(self) -> str:
        """Round-trip to PLC4X syntax."""
        return _render_plc4x(self)


@dataclass
class NodeS7Tag(Tag):
    """A Tag parsed from nodeS7 / pyS7 syntax.

    Example inputs accepted by :meth:`parse`:

    - ``DB1,X0.0`` — DB bit (BOOL)
    - ``DB1,B10`` — DB byte
    - ``DB1,W10`` — DB word (unsigned 16-bit)
    - ``DB1,I10`` — DB int (signed 16-bit)
    - ``DB1,DW10`` / ``DB1,DI10`` — DB dword / dint
    - ``DB1,R10`` — DB real
    - ``DB1,LR10`` — DB lreal
    - ``DB1,S10.20`` — DB string (offset 10, 20 chars)
    - ``DB1,WS10.10`` — DB wstring
    - ``M10.5`` — marker bit (bit form, type is BOOL)
    - ``MB10``, ``MW10``, ``MD10``, ``MR10`` — marker byte/word/dword/real
    - ``IW22``, ``QR24`` — input word, output real
    """

    @classmethod
    def parse(cls, address: str, name: str = "") -> "NodeS7Tag":
        """Parse a nodeS7 / pyS7 style tag address string.

        Raises:
            ValueError: If the address is malformed.
        """
        raw = address.strip()
        s = raw.upper()

        if s.startswith("%"):
            s = s[1:]

        # DB form: DB<n>,<typecode><offset>[.<bit-or-length>]
        if s.startswith("DB") and "," in s:
            match = _NODES7_DB_RE.match(s)
            if not match:
                raise ValueError(f"Invalid nodeS7 DB address: {address}")
            db_number = int(match.group(1))
            typecode = match.group(2)
            offset = int(match.group(3))
            trailing = match.group(4)
            datatype, bit, count = _nodes7_typecode_to_type(typecode, trailing)
            return cls(
                area=Area.DB,
                db_number=db_number,
                byte_offset=offset,
                bit=bit,
                datatype=datatype,
                count=count,
                name=name,
            )

        # Area-shortcut form: <M|I|Q|E|A>[typecode]<offset>[.<bit-or-length>]
        match = _NODES7_AREA_RE.match(s)
        if match:
            area_char = match.group(1)
            typecode = match.group(2) or ""
            offset = int(match.group(3))
            trailing = match.group(4)
            area = _NODES7_AREA_MAP[area_char]

            if not typecode:
                # Bare form: must be a bit access, e.g. M7.1
                if trailing is None:
                    raise ValueError(
                        f"Ambiguous nodeS7 address {address!r}: bare area+offset needs a bit suffix (M7.1) or typecode (MW7)."
                    )
                return cls(area=area, db_number=0, byte_offset=offset, bit=int(trailing), datatype="BOOL", count=1, name=name)

            datatype, bit, count = _nodes7_typecode_to_type(typecode, trailing)
            return cls(
                area=area,
                db_number=0,
                byte_offset=offset,
                bit=bit,
                datatype=datatype,
                count=count,
                name=name,
            )

        raise ValueError(f"Invalid nodeS7 tag address: {address}")

    def __str__(self) -> str:
        """Round-trip to nodeS7 syntax."""
        return _render_nodes7(self)


def parse_tag(address: str, *, strict: bool = True, name: str = "") -> Tag:
    """Autodetect dialect and parse a tag address string.

    Dialect is detected from syntax markers:

    - A comma (``,``) selects :class:`NodeS7Tag`.
    - A colon followed by a type (``:TYPE``) selects :class:`PLC4XTag`.

    Args:
        address: Tag address string.
        strict: When ``True`` (default), require one of the dialect markers
            above. Bare short forms like ``M7.1`` or ``IW22`` raise
            :class:`ValueError`. When ``False``, bare forms are dispatched
            to the nodeS7 parser (which accepts them).
        name: Optional tag name to store on the resulting Tag.

    Returns:
        A :class:`PLC4XTag` or :class:`NodeS7Tag` depending on the dialect
        detected.

    Raises:
        ValueError: If the input is ambiguous under strict mode, or if
            the selected parser fails to parse.
    """
    s = address.strip()
    if "," in s:
        return NodeS7Tag.parse(s, name)
    if ":" in s:
        return PLC4XTag.parse(s, name)
    if strict:
        raise ValueError(
            f"Ambiguous tag syntax {address!r}: must contain ',' (nodeS7) "
            f"or ':TYPE' (PLC4X). Pass strict=False to accept bare short forms."
        )
    return NodeS7Tag.parse(s, name)


# ---------------------------------------------------------------------------
# nodeS7 syntax tables and helpers
# ---------------------------------------------------------------------------

# DB form: DB<n>,<TYPECODE><OFFSET>[.<BIT or LENGTH>]
_NODES7_DB_RE = re.compile(r"^DB(\d+),([A-Z]+)(\d+)(?:\.(\d+))?$")

# Area-shortcut form: <AREA>[TYPECODE]<OFFSET>[.<BIT or LENGTH>]
_NODES7_AREA_RE = re.compile(r"^([MIQEA])([A-Z]*)(\d+)(?:\.(\d+))?$")

# Ordered longest-first so multi-char codes match before single-char
_NODES7_TYPECODES: list[tuple[str, str]] = [
    ("USINT", "USINT"),
    ("SINT", "SINT"),
    ("ULI", "ULINT"),
    ("LI", "LINT"),
    ("LW", "LWORD"),
    ("LR", "LREAL"),
    ("WS", "WSTRING"),
    ("DI", "DINT"),
    ("DW", "DWORD"),
    ("X", "BOOL"),
    ("B", "BYTE"),
    ("C", "CHAR"),
    ("I", "INT"),
    ("W", "WORD"),
    ("D", "DWORD"),
    ("R", "REAL"),
    ("S", "STRING"),
]

_NODES7_AREA_MAP: dict[str, Area] = {
    "M": Area.MK,
    "I": Area.PE,
    "Q": Area.PA,
    "E": Area.PE,  # German: Eingang
    "A": Area.PA,  # German: Ausgang
}


def _nodes7_typecode_to_type(typecode: str, trailing: str | None) -> tuple[str, int, int]:
    """Map a nodeS7 typecode to (datatype, bit, count).

    ``trailing`` is the optional ``.N`` suffix: it's a bit index for BOOL
    and a character length for STRING/WSTRING; otherwise rejected.
    """
    for prefix, dtype in _NODES7_TYPECODES:
        if typecode == prefix:
            if dtype == "BOOL":
                if trailing is None:
                    raise ValueError("nodeS7 BOOL address needs a bit suffix (X0.0)")
                return "BOOL", int(trailing), 1
            if dtype in ("STRING", "WSTRING"):
                if trailing is None:
                    raise ValueError(f"nodeS7 {dtype} address needs a length suffix (S0.20)")
                return f"{dtype}[{int(trailing)}]", 0, 1
            if trailing is not None:
                raise ValueError(f"nodeS7 {dtype} address does not take a trailing .N suffix")
            return dtype, 0, 1
    raise ValueError(f"Unknown nodeS7 typecode: {typecode!r}")


# Reverse map for __str__ rendering
_TYPE_TO_NODES7_CODE: dict[str, str] = {
    "BOOL": "X",
    "BYTE": "B",
    "CHAR": "C",
    "SINT": "SINT",
    "USINT": "USINT",
    "INT": "I",
    "WORD": "W",
    "DINT": "DI",
    "DWORD": "DW",
    "REAL": "R",
    "LREAL": "LR",
    "LINT": "LI",
    "ULINT": "ULI",
    "LWORD": "LW",
}


def _render_plc4x(tag: Tag) -> str:
    """Render a Tag in PLC4X syntax."""
    dt_upper = tag.datatype.upper()
    if _STRING_RE.match(dt_upper):
        dt_part = tag.datatype  # STRING[20] round-trips as-is
    elif tag.count > 1:
        dt_part = f"{tag.datatype}[{tag.count}]"
    else:
        dt_part = tag.datatype

    if tag.area == Area.DB:
        if dt_upper == "BOOL":
            return f"DB{tag.db_number}.DBX{tag.byte_offset}.{tag.bit}:BOOL"
        return f"DB{tag.db_number}:{tag.byte_offset}:{dt_part}"

    prefix = _AREA_PREFIX.get(tag.area, "?")
    if dt_upper == "BOOL":
        return f"{prefix}{tag.byte_offset}.{tag.bit}:BOOL"
    return f"{prefix}{tag.byte_offset}:{dt_part}"


def _render_nodes7(tag: Tag) -> str:
    """Render a Tag in nodeS7 syntax.

    Arrays (count > 1, non-string) are not expressible in nodeS7; they
    round-trip by emitting the base typecode without the count.
    """
    dt_upper = tag.datatype.upper()
    string_match = _STRING_RE.match(dt_upper)

    prefix = _AREA_PREFIX.get(tag.area, "?")

    if tag.area == Area.DB:
        if dt_upper == "BOOL":
            return f"DB{tag.db_number},X{tag.byte_offset}.{tag.bit}"
        if string_match:
            code = "S" if string_match.group(1) == "STRING" else "WS"
            length = string_match.group(2)
            return f"DB{tag.db_number},{code}{tag.byte_offset}.{length}"
        code = _TYPE_TO_NODES7_CODE.get(dt_upper, dt_upper)
        return f"DB{tag.db_number},{code}{tag.byte_offset}"

    if dt_upper == "BOOL":
        return f"{prefix}{tag.byte_offset}.{tag.bit}"
    if string_match:
        code = "S" if string_match.group(1) == "STRING" else "WS"
        length = string_match.group(2)
        return f"{prefix}{code}{tag.byte_offset}.{length}"
    code = _TYPE_TO_NODES7_CODE.get(dt_upper, dt_upper)
    return f"{prefix}{code}{tag.byte_offset}"


# ---------------------------------------------------------------------------
# Shared low-level helpers
# ---------------------------------------------------------------------------


def _parse_type(type_part: str) -> tuple[str, int]:
    """Parse ``INT`` or ``INT[5]`` into (datatype, count)."""
    type_part = type_part.strip()
    if "[" in type_part and type_part.endswith("]"):
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


def from_browse(variables: list[dict[str, Any]]) -> dict[str, Tag]:
    """Build a dict of Tags from :meth:`s7.Client.browse` results.

    .. warning:: This function is **experimental** and may change.

    When the browse result includes an ``lid`` key, the resulting Tag
    is configured for symbolic (LID-based) access suitable for
    optimized DBs. Otherwise it uses byte-offset access.

    Args:
        variables: List of variable-info dicts from ``client.browse()``.

    Returns:
        Dictionary mapping variable names to :class:`Tag` objects.
    """
    tags: dict[str, Tag] = {}
    for var in variables:
        name = var.get("name", "")
        if not name:
            continue
        lid = var.get("lid", 0)
        crc = var.get("symbol_crc", 0)
        access_sequence = [lid] if lid else []
        tags[name] = Tag(
            area=Area.DB,
            db_number=int(var.get("db_number", 0)),
            byte_offset=int(var.get("byte_offset", 0)),
            datatype=str(var.get("data_type", "BYTE")),
            count=int(var.get("count", 1)),
            name=name,
            access_sequence=access_sequence,
            symbol_crc=int(crc),
        )
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
