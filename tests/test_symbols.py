"""Tests for snap7.util.symbols — symbolic addressing."""

import json
import struct
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from snap7.util.symbols import SymbolTable, TagAddress, _parse_offset


# ---------------------------------------------------------------------------
# TagAddress basics
# ---------------------------------------------------------------------------


class TestTagAddress:
    def test_read_size_real(self) -> None:
        addr = TagAddress(db=1, offset=0, bit=0, type="REAL")
        assert addr.read_size() == 4

    def test_read_size_bool(self) -> None:
        addr = TagAddress(db=1, offset=4, bit=0, type="BOOL")
        assert addr.read_size() == 1

    def test_read_size_int(self) -> None:
        addr = TagAddress(db=1, offset=6, bit=0, type="INT")
        assert addr.read_size() == 2

    def test_read_size_string(self) -> None:
        addr = TagAddress(db=1, offset=8, bit=0, type="STRING[20]")
        assert addr.read_size() == 22  # 2-byte header + 20

    def test_read_size_wstring(self) -> None:
        addr = TagAddress(db=1, offset=0, bit=0, type="WSTRING[10]")
        assert addr.read_size() == 24  # 4-byte header + 10*2

    def test_read_size_fstring(self) -> None:
        addr = TagAddress(db=1, offset=0, bit=0, type="FSTRING[15]")
        assert addr.read_size() == 15

    def test_read_size_unknown_raises(self) -> None:
        addr = TagAddress(db=1, offset=0, bit=0, type="UNKNOWN_TYPE")
        with pytest.raises(ValueError, match="Unknown S7 type"):
            addr.read_size()

    def test_read_size_lreal(self) -> None:
        addr = TagAddress(db=1, offset=0, bit=0, type="LREAL")
        assert addr.read_size() == 8

    def test_read_size_dtl(self) -> None:
        addr = TagAddress(db=1, offset=0, bit=0, type="DTL")
        assert addr.read_size() == 12

    def test_byte_offset_property(self) -> None:
        addr = TagAddress(db=1, offset=10, bit=3, type="BOOL")
        assert addr.byte_offset == 10


# ---------------------------------------------------------------------------
# _parse_offset helper
# ---------------------------------------------------------------------------


class TestParseOffset:
    def test_integer_offset(self) -> None:
        assert _parse_offset("4") == (4, 0)

    def test_decimal_offset(self) -> None:
        assert _parse_offset("12.3") == (12, 3)

    def test_zero_bit(self) -> None:
        assert _parse_offset("4.0") == (4, 0)


# ---------------------------------------------------------------------------
# Construction from dict
# ---------------------------------------------------------------------------


class TestDictConstruction:
    def test_basic_construction(self) -> None:
        table = SymbolTable(
            {
                "Motor1.Speed": {"db": 1, "offset": 0, "type": "REAL"},
                "Motor1.Running": {"db": 1, "offset": 4, "bit": 0, "type": "BOOL"},
            }
        )
        assert len(table) == 2
        assert "Motor1.Speed" in table
        assert "Motor1.Running" in table

    def test_resolve_address(self) -> None:
        table = SymbolTable({"Tank.Level": {"db": 2, "offset": 10, "type": "INT"}})
        addr = table.resolve("Tank.Level")
        assert addr.db == 2
        assert addr.offset == 10
        assert addr.type == "INT"
        assert addr.bit == 0

    def test_resolve_with_bit(self) -> None:
        table = SymbolTable({"Valve.Open": {"db": 1, "offset": 4, "bit": 3, "type": "BOOL"}})
        addr = table.resolve("Valve.Open")
        assert addr.bit == 3

    def test_resolve_offset_with_dot_notation(self) -> None:
        table = SymbolTable({"Sensor.Active": {"db": 1, "offset": "12.5", "type": "BOOL"}})
        addr = table.resolve("Sensor.Active")
        assert addr.offset == 12
        assert addr.bit == 5

    def test_resolve_unknown_tag_raises(self) -> None:
        table = SymbolTable({})
        with pytest.raises(KeyError, match="Unknown tag"):
            table.resolve("NonExistent")

    def test_nested_path(self) -> None:
        table = SymbolTable({"Motors[3].Speed": {"db": 1, "offset": 24, "type": "REAL"}})
        addr = table.resolve("Motors[3].Speed")
        assert addr.db == 1
        assert addr.offset == 24

    def test_tags_property_returns_copy(self) -> None:
        table = SymbolTable({"X": {"db": 1, "offset": 0, "type": "INT"}})
        tags = table.tags
        tags["Y"] = TagAddress(db=2, offset=0, bit=0, type="INT")
        assert "Y" not in table


# ---------------------------------------------------------------------------
# Construction from CSV
# ---------------------------------------------------------------------------


CSV_CONTENT = """\
tag,db,offset,type
Motor1.Speed,1,0,REAL
Motor1.Running,1,4.0,BOOL
Tank.Level,1,6,INT
Tank.Name,1,8,STRING[20]
"""


class TestCSVConstruction:
    def test_from_csv_string(self) -> None:
        table = SymbolTable.from_csv(CSV_CONTENT)
        assert len(table) == 4
        addr = table.resolve("Motor1.Speed")
        assert addr.db == 1
        assert addr.offset == 0
        assert addr.type == "REAL"

    def test_from_csv_bool_bit(self) -> None:
        table = SymbolTable.from_csv(CSV_CONTENT)
        addr = table.resolve("Motor1.Running")
        assert addr.type == "BOOL"
        assert addr.bit == 0

    def test_from_csv_file(self, tmp_path: Path) -> None:
        csv_file = tmp_path / "tags.csv"
        csv_file.write_text(CSV_CONTENT)
        table = SymbolTable.from_csv(csv_file)
        assert len(table) == 4

    def test_from_csv_with_bit_column(self) -> None:
        csv_with_bit = """\
tag,db,offset,bit,type
Valve.Open,1,4,3,BOOL
"""
        table = SymbolTable.from_csv(csv_with_bit)
        addr = table.resolve("Valve.Open")
        assert addr.bit == 3


# ---------------------------------------------------------------------------
# Construction from JSON
# ---------------------------------------------------------------------------


class TestJSONConstruction:
    def test_from_json_string(self) -> None:
        data = {
            "Motor1.Speed": {"db": 1, "offset": 0, "type": "REAL"},
            "Motor1.Running": {"db": 1, "offset": 4, "bit": 0, "type": "BOOL"},
        }
        table = SymbolTable.from_json(json.dumps(data))
        assert len(table) == 2
        assert table.resolve("Motor1.Speed").type == "REAL"

    def test_from_json_file(self, tmp_path: Path) -> None:
        data = {"Temp": {"db": 3, "offset": 0, "type": "REAL"}}
        json_file = tmp_path / "tags.json"
        json_file.write_text(json.dumps(data))
        table = SymbolTable.from_json(json_file)
        assert len(table) == 1


# ---------------------------------------------------------------------------
# Read / Write with mocked client
# ---------------------------------------------------------------------------


def _make_client() -> MagicMock:
    """Create a MagicMock that behaves enough like snap7.Client."""
    return MagicMock(spec=["db_read", "db_write", "read_multi_vars"])


class TestRead:
    def test_read_real(self) -> None:
        client = _make_client()
        data = bytearray(4)
        struct.pack_into(">f", data, 0, 123.5)
        client.db_read.return_value = data

        table = SymbolTable({"Speed": {"db": 1, "offset": 0, "type": "REAL"}})
        value = table.read(client, "Speed")

        client.db_read.assert_called_once_with(1, 0, 4)
        assert isinstance(value, float)
        assert abs(value - 123.5) < 0.01

    def test_read_int(self) -> None:
        client = _make_client()
        data = bytearray(2)
        struct.pack_into(">h", data, 0, -42)
        client.db_read.return_value = data

        table = SymbolTable({"Level": {"db": 2, "offset": 10, "type": "INT"}})
        value = table.read(client, "Level")

        client.db_read.assert_called_once_with(2, 10, 2)
        assert value == -42

    def test_read_bool_true(self) -> None:
        client = _make_client()
        client.db_read.return_value = bytearray([0b00001000])

        table = SymbolTable({"Flag": {"db": 1, "offset": 4, "bit": 3, "type": "BOOL"}})
        value = table.read(client, "Flag")

        assert value is True

    def test_read_bool_false(self) -> None:
        client = _make_client()
        client.db_read.return_value = bytearray([0b00000000])

        table = SymbolTable({"Flag": {"db": 1, "offset": 4, "bit": 3, "type": "BOOL"}})
        value = table.read(client, "Flag")

        assert value is False

    def test_read_dint(self) -> None:
        client = _make_client()
        data = bytearray(4)
        struct.pack_into(">i", data, 0, -100000)
        client.db_read.return_value = data

        table = SymbolTable({"Counter": {"db": 1, "offset": 0, "type": "DINT"}})
        assert table.read(client, "Counter") == -100000

    def test_read_lreal(self) -> None:
        client = _make_client()
        data = bytearray(8)
        struct.pack_into(">d", data, 0, 3.14159265358979)
        client.db_read.return_value = data

        table = SymbolTable({"Pi": {"db": 1, "offset": 0, "type": "LREAL"}})
        pi_val = table.read(client, "Pi")
        assert isinstance(pi_val, float)
        assert abs(pi_val - 3.14159265358979) < 1e-10

    def test_read_byte(self) -> None:
        client = _make_client()
        client.db_read.return_value = bytearray([0xAB])

        table = SymbolTable({"Status": {"db": 1, "offset": 0, "type": "BYTE"}})
        assert table.read(client, "Status") == 0xAB

    def test_read_string(self) -> None:
        client = _make_client()
        text = "hello"
        # STRING format: max_size(1 byte), current_len(1 byte), chars...
        data = bytearray(22)
        data[0] = 20  # max size
        data[1] = len(text)  # current length
        for i, c in enumerate(text):
            data[2 + i] = ord(c)
        client.db_read.return_value = data

        table = SymbolTable({"Name": {"db": 1, "offset": 0, "type": "STRING[20]"}})
        assert table.read(client, "Name") == "hello"

    def test_read_char(self) -> None:
        client = _make_client()
        client.db_read.return_value = bytearray([ord("A")])

        table = SymbolTable({"Letter": {"db": 1, "offset": 0, "type": "CHAR"}})
        assert table.read(client, "Letter") == "A"

    def test_read_unknown_tag_raises(self) -> None:
        client = _make_client()
        table = SymbolTable({})
        with pytest.raises(KeyError):
            table.read(client, "NonExistent")


class TestWrite:
    def test_write_real(self) -> None:
        client = _make_client()
        table = SymbolTable({"Speed": {"db": 1, "offset": 0, "type": "REAL"}})
        table.write(client, "Speed", 123.5)

        client.db_write.assert_called_once()
        args = client.db_write.call_args
        assert args[0][0] == 1  # db
        assert args[0][1] == 0  # offset
        written = args[0][2]
        value = struct.unpack(">f", written)[0]
        assert abs(value - 123.5) < 0.01

    def test_write_int(self) -> None:
        client = _make_client()
        table = SymbolTable({"Level": {"db": 2, "offset": 10, "type": "INT"}})
        table.write(client, "Level", -42)

        args = client.db_write.call_args
        assert args[0][0] == 2
        assert args[0][1] == 10
        value = struct.unpack(">h", args[0][2])[0]
        assert value == -42

    def test_write_bool_set_true(self) -> None:
        client = _make_client()
        client.db_read.return_value = bytearray([0b00000000])

        table = SymbolTable({"Flag": {"db": 1, "offset": 4, "bit": 3, "type": "BOOL"}})
        table.write(client, "Flag", True)

        # Should read first then write
        client.db_read.assert_called_once_with(1, 4, 1)
        args = client.db_write.call_args
        assert args[0][0] == 1
        assert args[0][1] == 4
        assert args[0][2][0] & 0b00001000  # bit 3 should be set

    def test_write_bool_set_false(self) -> None:
        client = _make_client()
        client.db_read.return_value = bytearray([0b00001000])

        table = SymbolTable({"Flag": {"db": 1, "offset": 4, "bit": 3, "type": "BOOL"}})
        table.write(client, "Flag", False)

        args = client.db_write.call_args
        assert not (args[0][2][0] & 0b00001000)  # bit 3 should be cleared

    def test_write_dint(self) -> None:
        client = _make_client()
        table = SymbolTable({"Counter": {"db": 1, "offset": 0, "type": "DINT"}})
        table.write(client, "Counter", -100000)

        args = client.db_write.call_args
        value = struct.unpack(">i", args[0][2])[0]
        assert value == -100000

    def test_write_unknown_tag_raises(self) -> None:
        client = _make_client()
        table = SymbolTable({})
        with pytest.raises(KeyError):
            table.write(client, "NonExistent", 0)


# ---------------------------------------------------------------------------
# read_many
# ---------------------------------------------------------------------------


class TestReadMany:
    def test_read_many(self) -> None:
        client = _make_client()
        real_data = bytearray(4)
        struct.pack_into(">f", real_data, 0, 50.0)
        int_data = bytearray(2)
        struct.pack_into(">h", int_data, 0, 100)

        # read_many uses read_multi_vars for batching
        client.read_multi_vars.return_value = (0, [real_data, int_data])

        table = SymbolTable(
            {
                "Speed": {"db": 1, "offset": 0, "type": "REAL"},
                "Level": {"db": 1, "offset": 4, "type": "INT"},
            }
        )
        values = table.read_many(client, ["Speed", "Level"])
        speed = values["Speed"]
        assert isinstance(speed, float)
        assert abs(speed - 50.0) < 0.01
        assert values["Level"] == 100

    def test_read_many_single_tag(self) -> None:
        """Single tag falls back to read() instead of read_multi_vars."""
        client = _make_client()
        real_data = bytearray(4)
        struct.pack_into(">f", real_data, 0, 42.0)
        client.db_read.return_value = real_data

        table = SymbolTable({"Temp": {"db": 1, "offset": 0, "type": "REAL"}})
        values = table.read_many(client, ["Temp"])
        assert abs(values["Temp"] - 42.0) < 0.01

    def test_read_many_empty(self) -> None:
        client = _make_client()
        table = SymbolTable({"X": {"db": 1, "offset": 0, "type": "INT"}})
        assert table.read_many(client, []) == {}


# ---------------------------------------------------------------------------
# Merge
# ---------------------------------------------------------------------------


class TestMerge:
    def test_merge_two_tables(self) -> None:
        t1 = SymbolTable({"A": {"db": 1, "offset": 0, "type": "INT"}})
        t2 = SymbolTable({"B": {"db": 2, "offset": 0, "type": "REAL"}})
        merged = t1.merge(t2)
        assert len(merged) == 2
        assert "A" in merged
        assert "B" in merged

    def test_merge_override(self) -> None:
        t1 = SymbolTable({"A": {"db": 1, "offset": 0, "type": "INT"}})
        t2 = SymbolTable({"A": {"db": 2, "offset": 10, "type": "REAL"}})
        merged = t1.merge(t2)
        assert merged.resolve("A").db == 2
        assert merged.resolve("A").type == "REAL"


# ---------------------------------------------------------------------------
# Unsupported type errors
# ---------------------------------------------------------------------------


class TestUnsupportedType:
    def test_read_unsupported_type(self) -> None:
        client = _make_client()
        client.db_read.return_value = bytearray(4)

        table = SymbolTable({"X": {"db": 1, "offset": 0, "type": "STRUCT"}})
        # STRUCT is not in the type size map, so read_size will raise
        with pytest.raises(ValueError, match="Unknown S7 type"):
            table.read(client, "X")

    def test_write_unsupported_type(self) -> None:
        client = _make_client()

        table = SymbolTable({"X": {"db": 1, "offset": 0, "type": "STRUCT"}})
        with pytest.raises(ValueError, match="Unknown S7 type"):
            table.write(client, "X", 0)
