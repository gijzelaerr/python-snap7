"""Typed symbolic tag descriptors built from S7CommPlus browse metadata."""

from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Iterator
from typing import Any, Optional

from .protocol import DataType
from .typeinfo import Softdatatype


_WIRE_TYPES: dict[Softdatatype, DataType] = {
    Softdatatype.BOOL: DataType.BOOL,
    Softdatatype.BBOOL: DataType.BOOL,
    Softdatatype.BYTE: DataType.BYTE,
    Softdatatype.CHAR: DataType.BYTE,
    Softdatatype.WORD: DataType.WORD,
    Softdatatype.INT: DataType.INT,
    Softdatatype.DWORD: DataType.DWORD,
    Softdatatype.DINT: DataType.DINT,
    Softdatatype.REAL: DataType.REAL,
    Softdatatype.DATE: DataType.UINT,
    Softdatatype.TIMEOFDAY: DataType.UDINT,
    Softdatatype.TIME: DataType.DINT,
    Softdatatype.S5TIME: DataType.WORD,
    Softdatatype.DATEANDTIME: DataType.TIMESTAMP,
    Softdatatype.STRING: DataType.S7STRING,
    Softdatatype.LREAL: DataType.LREAL,
    Softdatatype.ULINT: DataType.ULINT,
    Softdatatype.LINT: DataType.LINT,
    Softdatatype.LWORD: DataType.LWORD,
    Softdatatype.USINT: DataType.USINT,
    Softdatatype.UINT: DataType.UINT,
    Softdatatype.UDINT: DataType.UDINT,
    Softdatatype.SINT: DataType.SINT,
    Softdatatype.WCHAR: DataType.UINT,
    Softdatatype.WSTRING: DataType.WSTRING,
    Softdatatype.LTIME: DataType.TIMESPAN,
    Softdatatype.LTOD: DataType.ULINT,
    Softdatatype.LDT: DataType.TIMESTAMP,
}


@dataclass(frozen=True)
class ArrayDimension:
    """One PLC array dimension."""

    lower_bound: int
    element_count: int


@dataclass(frozen=True)
class SymbolicTag:
    """Resolved symbolic address and type metadata for one browsed tag."""

    name: str
    access_area: int
    lids: tuple[int, ...]
    softdatatype: Softdatatype
    datatype: Optional[DataType]
    symbol_crc: int = 0
    array_dimensions: tuple[ArrayDimension, ...] = ()
    string_length: int = 0
    opt_address: int = 0
    opt_bitoffset: int = 0
    nonopt_address: int = 0
    nonopt_bitoffset: int = 0

    @classmethod
    def from_browse(cls, item: dict[str, Any]) -> "SymbolicTag":
        """Create a descriptor from one :meth:`Client.browse` result."""
        name = str(item["name"])
        parts = str(item["access_sequence"]).split(".")
        if len(parts) < 2 or any(not part for part in parts):
            raise ValueError(f"Tag {name!r} has an invalid access sequence")
        try:
            access_area, *lids = (int(part, 16) for part in parts)
            softdatatype = Softdatatype[item["data_type"]]
        except (KeyError, ValueError) as exc:
            raise ValueError(f"Tag {name!r} has unsupported browse metadata") from exc

        dimensions = tuple(ArrayDimension(int(lower), int(count)) for lower, count in item.get("array_dimensions", ()))
        return cls(
            name=name,
            access_area=access_area,
            lids=tuple(lids),
            softdatatype=softdatatype,
            datatype=_WIRE_TYPES.get(softdatatype),
            symbol_crc=int(item.get("symbol_crc", 0)),
            array_dimensions=dimensions,
            string_length=int(item.get("string_length", 0)),
            opt_address=int(item.get("opt_address", 0)),
            opt_bitoffset=int(item.get("opt_bitoffset", 0)),
            nonopt_address=int(item.get("nonopt_address", 0)),
            nonopt_bitoffset=int(item.get("nonopt_bitoffset", 0)),
        )


@dataclass(frozen=True)
class TagResult:
    """Per-item result returned by a named batch operation."""

    tag: SymbolicTag
    value: Optional[bytes] = None
    error: Optional[Exception] = None

    @property
    def success(self) -> bool:
        return self.error is None


class SymbolCatalog:
    """An in-memory, name-indexed snapshot of PLC browse metadata."""

    def __init__(self, tags: list[SymbolicTag]) -> None:
        self._tags: dict[str, SymbolicTag] = {}
        for tag in tags:
            if tag.name in self._tags:
                raise ValueError(f"Duplicate symbolic tag name: {tag.name!r}")
            self._tags[tag.name] = tag

    @classmethod
    def from_browse(cls, variables: list[dict[str, Any]]) -> "SymbolCatalog":
        return cls([SymbolicTag.from_browse(variable) for variable in variables])

    def resolve(self, name: str) -> SymbolicTag:
        try:
            return self._tags[name]
        except KeyError as exc:
            raise KeyError(f"Unknown symbolic tag: {name!r}") from exc

    def __len__(self) -> int:
        return len(self._tags)

    def __iter__(self) -> Iterator[SymbolicTag]:
        return iter(self._tags.values())
