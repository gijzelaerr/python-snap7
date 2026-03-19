"""
Symbolic addressing for S7 PLC data blocks.

Provides a SymbolTable class that maps human-readable tag names to PLC
addresses (db_number, byte_offset, data_type), enabling read/write operations
by tag name instead of raw addresses.

Example::

    from snap7.util.symbols import SymbolTable

    symbols = SymbolTable.from_csv("tags.csv")
    value = symbols.read(client, "Motor1.Speed")
    symbols.write(client, "Motor1.Speed", 1500.0)
"""

import csv
import io
import json
import re
from dataclasses import dataclass
from logging import getLogger
from pathlib import Path
from typing import Any, Dict, Union

from snap7.client import Client
from snap7.type import ValueType
from snap7.util import (
    get_bool,
    get_byte,
    get_char,
    get_dint,
    get_dword,
    get_dt,
    get_dtl,
    get_int,
    get_lreal,
    get_real,
    get_sint,
    get_string,
    get_tod,
    get_udint,
    get_uint,
    get_usint,
    get_wchar,
    get_word,
    get_wstring,
    get_date,
    get_time,
    get_lword,
    set_bool,
    set_byte,
    set_char,
    set_date,
    set_dint,
    set_dword,
    set_dt,
    set_dtl,
    set_int,
    set_lreal,
    set_real,
    set_sint,
    set_string,
    set_tod,
    set_udint,
    set_uint,
    set_usint,
    set_wchar,
    set_word,
    set_wstring,
    set_time,
    set_lword,
)

logger = getLogger(__name__)

# Mapping from S7 type name to the number of bytes needed to read
_TYPE_SIZE: Dict[str, int] = {
    "BOOL": 1,
    "BYTE": 1,
    "SINT": 1,
    "USINT": 1,
    "CHAR": 1,
    "INT": 2,
    "UINT": 2,
    "WORD": 2,
    "DATE": 2,
    "DINT": 4,
    "UDINT": 4,
    "DWORD": 4,
    "REAL": 4,
    "TIME": 4,
    "TOD": 4,
    "TIME_OF_DAY": 4,
    "DATE_AND_TIME": 8,
    "DT": 8,
    "LREAL": 8,
    "LWORD": 8,
    "WCHAR": 2,
    "DTL": 12,
}

# Regex to extract STRING[n] or WSTRING[n] with size parameter
_STRING_RE = re.compile(r"^(STRING|WSTRING|FSTRING)\[(\d+)]$", re.IGNORECASE)


@dataclass(frozen=True)
class TagAddress:
    """Resolved address for a single PLC tag."""

    db: int
    offset: int
    bit: int
    type: str

    @property
    def byte_offset(self) -> int:
        """Return the byte offset (without bit component)."""
        return self.offset

    def read_size(self) -> int:
        """Return the number of bytes that need to be read from the PLC for this tag."""
        upper = self.type.upper()
        match = _STRING_RE.match(upper)
        if match:
            kind = match.group(1)
            length = int(match.group(2))
            if kind == "FSTRING":
                return length
            elif kind == "STRING":
                # S7 STRING: 2-byte header + max_length characters
                return 2 + length
            elif kind == "WSTRING":
                # S7 WSTRING: 4-byte header + max_length * 2 bytes
                return 4 + length * 2
        if upper in _TYPE_SIZE:
            return _TYPE_SIZE[upper]
        raise ValueError(f"Unknown S7 type: {self.type}")


def _parse_offset(offset_str: str) -> tuple[int, int]:
    """Parse an offset string like '4' or '4.0' into (byte_offset, bit_index).

    Args:
        offset_str: offset value, e.g. '4', '4.0', '12.3'

    Returns:
        Tuple of (byte_offset, bit_index).
    """
    if "." in str(offset_str):
        parts = str(offset_str).split(".")
        return int(parts[0]), int(parts[1])
    return int(float(offset_str)), 0


class SymbolTable:
    """Map symbolic tag names to PLC addresses and perform typed reads/writes.

    Supports construction from:
    - A Python dict mapping tag names to address dicts
    - A CSV file or string (via :meth:`from_csv`)
    - A JSON file or string (via :meth:`from_json`)

    Tag names support dot-separated nested paths (e.g. ``"Motor1.Speed"``)
    and array indexing (e.g. ``"Motors[3].Speed"``).

    Example::

        symbols = SymbolTable({
            "Motor1.Speed": {"db": 1, "offset": 0, "type": "REAL"},
            "Motor1.Running": {"db": 1, "offset": 4, "bit": 0, "type": "BOOL"},
        })
        value = symbols.read(client, "Motor1.Speed")
        symbols.write(client, "Motor1.Speed", 1500.0)
    """

    def __init__(self, tags: Dict[str, Dict[str, Any]]) -> None:
        self._tags: Dict[str, TagAddress] = {}
        for name, info in tags.items():
            self._add_tag(name, info)

    # ------------------------------------------------------------------
    # Construction helpers
    # ------------------------------------------------------------------

    def _add_tag(self, name: str, info: Dict[str, Any]) -> None:
        db = int(info["db"])
        offset_raw = info.get("offset", 0)
        byte_offset, default_bit = _parse_offset(str(offset_raw))
        bit = int(info.get("bit", default_bit))
        type_ = str(info["type"])
        self._tags[name] = TagAddress(db=db, offset=byte_offset, bit=bit, type=type_)

    @classmethod
    def from_csv(cls, source: Union[str, Path]) -> "SymbolTable":
        """Create a SymbolTable from a CSV file or CSV string.

        The CSV must have columns: ``tag``, ``db``, ``offset``, ``type``.
        An optional ``bit`` column overrides the bit index parsed from the offset.

        Args:
            source: path to a CSV file, or a CSV-formatted string.

        Returns:
            A new :class:`SymbolTable`.
        """
        path = Path(source)
        if path.exists():
            text = path.read_text()
        else:
            text = str(source)

        reader = csv.DictReader(io.StringIO(text))
        tags: Dict[str, Dict[str, Any]] = {}
        for row in reader:
            name = row["tag"].strip()
            entry: Dict[str, Any] = {
                "db": row["db"].strip(),
                "offset": row["offset"].strip(),
                "type": row["type"].strip(),
            }
            if "bit" in row and row["bit"] is not None and row["bit"].strip():
                entry["bit"] = row["bit"].strip()
            tags[name] = entry
        return cls(tags)

    @classmethod
    def from_json(cls, source: Union[str, Path]) -> "SymbolTable":
        """Create a SymbolTable from a JSON file or JSON string.

        The JSON should be an object mapping tag names to address objects,
        each with keys ``db``, ``offset``, ``type``, and optionally ``bit``.

        Args:
            source: path to a JSON file, or a JSON-formatted string.

        Returns:
            A new :class:`SymbolTable`.
        """
        path = Path(source)
        if path.exists():
            text = path.read_text()
        else:
            text = str(source)

        data: Dict[str, Dict[str, Any]] = json.loads(text)
        return cls(data)

    # ------------------------------------------------------------------
    # Lookup
    # ------------------------------------------------------------------

    def resolve(self, tag: str) -> TagAddress:
        """Resolve a tag name to its :class:`TagAddress`.

        Args:
            tag: the symbolic name (e.g. ``"Motor1.Speed"``).

        Returns:
            The resolved address.

        Raises:
            KeyError: if the tag is not defined in this table.
        """
        if tag in self._tags:
            return self._tags[tag]
        raise KeyError(f"Unknown tag: {tag!r}")

    @property
    def tags(self) -> Dict[str, TagAddress]:
        """Return a copy of the internal tag mapping."""
        return dict(self._tags)

    def __len__(self) -> int:
        return len(self._tags)

    def __contains__(self, tag: str) -> bool:
        return tag in self._tags

    # ------------------------------------------------------------------
    # Read / write
    # ------------------------------------------------------------------

    def read(self, client: Client, tag: str) -> ValueType:
        """Read a single tag value from the PLC.

        Args:
            client: a connected :class:`~snap7.client.Client`.
            tag: symbolic tag name.

        Returns:
            The value, typed according to the tag's S7 data type.
        """
        addr = self.resolve(tag)
        size = addr.read_size()
        data = client.db_read(addr.db, addr.byte_offset, size)
        return self._get_value(data, 0, addr)

    def write(self, client: Client, tag: str, value: Any) -> None:
        """Write a single tag value to the PLC.

        Args:
            client: a connected :class:`~snap7.client.Client`.
            tag: symbolic tag name.
            value: the value to write.
        """
        addr = self.resolve(tag)
        size = addr.read_size()

        upper = addr.type.upper()
        if upper == "BOOL":
            # For BOOL we need to read-modify-write the byte
            data = client.db_read(addr.db, addr.byte_offset, 1)
            set_bool(data, 0, addr.bit, bool(value))
            client.db_write(addr.db, addr.byte_offset, data)
            return

        # For non-BOOL types we can write directly
        data = bytearray(size)
        self._set_value(data, 0, addr, value)
        client.db_write(addr.db, addr.byte_offset, data)

    def read_many(self, client: Client, tags: list[str]) -> Dict[str, ValueType]:
        """Read multiple tags, grouping reads by DB where possible.

        Args:
            client: a connected :class:`~snap7.client.Client`.
            tags: list of tag names to read.

        Returns:
            Dictionary mapping tag names to their values.
        """
        result: Dict[str, ValueType] = {}
        for tag in tags:
            result[tag] = self.read(client, tag)
        return result

    # ------------------------------------------------------------------
    # Internal getter / setter dispatch
    # ------------------------------------------------------------------

    @staticmethod
    def _get_value(data: bytearray, base_offset: int, addr: TagAddress) -> ValueType:
        """Extract a typed value from a bytearray at the given offset."""
        upper = addr.type.upper()
        offset = base_offset

        if upper == "BOOL":
            return get_bool(data, offset, addr.bit)

        match = _STRING_RE.match(upper)
        if match:
            kind = match.group(1)
            length = int(match.group(2))
            if kind == "FSTRING":
                from snap7.util import get_fstring

                return get_fstring(data, offset, length)
            elif kind == "STRING":
                return get_string(data, offset)
            elif kind == "WSTRING":
                return get_wstring(data, offset)

        _getter_map: Dict[str, Any] = {
            "BYTE": get_byte,
            "SINT": get_sint,
            "USINT": get_usint,
            "CHAR": get_char,
            "INT": get_int,
            "UINT": get_uint,
            "WORD": get_word,
            "DATE": get_date,
            "DINT": get_dint,
            "UDINT": get_udint,
            "DWORD": get_dword,
            "REAL": get_real,
            "TIME": get_time,
            "TOD": get_tod,
            "TIME_OF_DAY": get_tod,
            "DATE_AND_TIME": get_dt,
            "DT": get_dt,
            "LREAL": get_lreal,
            "LWORD": get_lword,
            "WCHAR": get_wchar,
            "DTL": get_dtl,
        }

        if upper in _getter_map:
            return _getter_map[upper](data, offset)  # type: ignore[no-any-return]

        raise ValueError(f"Unsupported S7 type for reading: {addr.type}")

    @staticmethod
    def _set_value(data: bytearray, base_offset: int, addr: TagAddress, value: Any) -> None:
        """Write a typed value into a bytearray at the given offset."""
        upper = addr.type.upper()
        offset = base_offset

        if upper == "BOOL":
            set_bool(data, offset, addr.bit, bool(value))
            return

        match = _STRING_RE.match(upper)
        if match:
            kind = match.group(1)
            length = int(match.group(2))
            if kind == "FSTRING":
                from snap7.util import set_fstring

                set_fstring(data, offset, str(value), length)
                return
            elif kind == "STRING":
                set_string(data, offset, str(value), length)
                return
            elif kind == "WSTRING":
                set_wstring(data, offset, str(value), length)
                return

        _int_setter_map: Dict[str, Any] = {
            "BYTE": set_byte,
            "SINT": set_sint,
            "USINT": set_usint,
            "INT": set_int,
            "UINT": set_uint,
            "WORD": set_word,
            "DINT": set_dint,
            "UDINT": set_udint,
            "DWORD": set_dword,
            "LWORD": set_lword,
        }

        if upper in _int_setter_map:
            _int_setter_map[upper](data, offset, int(value))
            return

        _simple_setter_map: Dict[str, Any] = {
            "REAL": set_real,
            "LREAL": set_lreal,
            "CHAR": set_char,
            "WCHAR": set_wchar,
            "TIME": set_time,
            "DATE": set_date,
            "TOD": set_tod,
            "TIME_OF_DAY": set_tod,
            "DATE_AND_TIME": set_dt,
            "DT": set_dt,
            "DTL": set_dtl,
        }

        if upper in _simple_setter_map:
            _simple_setter_map[upper](data, offset, value)
            return

        raise ValueError(f"Unsupported S7 type for writing: {addr.type}")

    # ------------------------------------------------------------------
    # Merge
    # ------------------------------------------------------------------

    def merge(self, other: "SymbolTable") -> "SymbolTable":
        """Return a new SymbolTable containing tags from both tables.

        Args:
            other: another :class:`SymbolTable` to merge with.

        Returns:
            A new merged :class:`SymbolTable`. Tags from *other* override
            duplicates from *self*.
        """
        combined: Dict[str, Dict[str, Any]] = {}
        for name, addr in self._tags.items():
            combined[name] = {"db": addr.db, "offset": addr.offset, "bit": addr.bit, "type": addr.type}
        for name, addr in other._tags.items():
            combined[name] = {"db": addr.db, "offset": addr.offset, "bit": addr.bit, "type": addr.type}
        return SymbolTable(combined)
