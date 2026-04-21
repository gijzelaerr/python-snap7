"""Tests for the Tag parser and loaders."""

import json
from pathlib import Path

import pytest

from snap7.tags import NodeS7Tag, PLC4XTag, Tag, from_browse, load_csv, load_json, load_tia_xml, parse_tag
from snap7.type import Area


class TestTagFromString:
    """Parse tag address strings in PLC4X / Siemens notation."""

    def test_db_bit(self) -> None:
        t = Tag.from_string("DB1.DBX0.0:BOOL")
        assert t.area == Area.DB
        assert t.db_number == 1
        assert t.byte_offset == 0
        assert t.bit == 0
        assert t.datatype == "BOOL"
        assert t.count == 1

    def test_db_bit_nonzero(self) -> None:
        t = Tag.from_string("DB2.DBX10.5:BOOL")
        assert t.db_number == 2
        assert t.byte_offset == 10
        assert t.bit == 5

    def test_db_byte(self) -> None:
        t = Tag.from_string("DB1.DBB10:BYTE")
        assert t.datatype == "BYTE"
        assert t.byte_offset == 10

    def test_db_word(self) -> None:
        t = Tag.from_string("DB1.DBW10:INT")
        assert t.datatype == "INT"
        assert t.byte_offset == 10

    def test_db_dword(self) -> None:
        t = Tag.from_string("DB1.DBD10:REAL")
        assert t.datatype == "REAL"
        assert t.byte_offset == 10

    def test_db_short_form(self) -> None:
        t = Tag.from_string("DB1:10:INT")
        assert t.area == Area.DB
        assert t.db_number == 1
        assert t.byte_offset == 10
        assert t.datatype == "INT"

    def test_db_short_form_bit(self) -> None:
        t = Tag.from_string("DB1:10.3:BOOL")
        assert t.byte_offset == 10
        assert t.bit == 3

    def test_db_string(self) -> None:
        t = Tag.from_string("DB1:10:STRING[20]")
        assert t.datatype == "STRING[20]"
        assert t.count == 1
        assert t.size == 22  # 2-byte header + 20 bytes

    def test_db_wstring(self) -> None:
        t = Tag.from_string("DB1:10:WSTRING[10]")
        assert t.datatype == "WSTRING[10]"
        assert t.size == 24  # 4-byte header + 10 * 2 bytes

    def test_db_array(self) -> None:
        t = Tag.from_string("DB1:0:REAL[5]")
        assert t.datatype == "REAL"
        assert t.count == 5
        assert t.size == 20  # 5 * 4 bytes

    def test_db_array_int(self) -> None:
        t = Tag.from_string("DB1:0:INT[10]")
        assert t.count == 10
        assert t.size == 20

    def test_merker_bit(self) -> None:
        t = Tag.from_string("M10.5:BOOL")
        assert t.area == Area.MK
        assert t.db_number == 0
        assert t.byte_offset == 10
        assert t.bit == 5

    def test_merker_word(self) -> None:
        t = Tag.from_string("MW20:WORD")
        assert t.area == Area.MK
        assert t.byte_offset == 20

    def test_input_bit(self) -> None:
        t = Tag.from_string("I0.0:BOOL")
        assert t.area == Area.PE
        assert t.byte_offset == 0
        assert t.bit == 0

    def test_output_bit(self) -> None:
        t = Tag.from_string("Q0.0:BOOL")
        assert t.area == Area.PA

    def test_leading_percent(self) -> None:
        t = Tag.from_string("%DB1.DBX0.0:BOOL")
        assert t.area == Area.DB
        assert t.db_number == 1

    def test_case_insensitive(self) -> None:
        t = Tag.from_string("db1.dbw10:int")
        assert t.db_number == 1
        assert t.byte_offset == 10
        assert t.datatype == "INT"

    def test_missing_type_raises(self) -> None:
        with pytest.raises(ValueError, match="must include type"):
            Tag.from_string("DB1.DBW10")

    def test_unknown_area_raises(self) -> None:
        with pytest.raises(ValueError, match="Unsupported"):
            Tag.from_string("X1.XYZ:INT")

    def test_invalid_format_raises(self) -> None:
        with pytest.raises(ValueError):
            Tag.from_string(":::")


class TestTagSize:
    """Tag.size computes total bytes correctly."""

    def test_scalar_sizes(self) -> None:
        assert Tag(Area.DB, 1, 0, "BOOL").size == 1
        assert Tag(Area.DB, 1, 0, "INT").size == 2
        assert Tag(Area.DB, 1, 0, "DINT").size == 4
        assert Tag(Area.DB, 1, 0, "REAL").size == 4
        assert Tag(Area.DB, 1, 0, "LREAL").size == 8
        assert Tag(Area.DB, 1, 0, "DTL").size == 12

    def test_array_sizes(self) -> None:
        assert Tag(Area.DB, 1, 0, "REAL", count=5).size == 20
        assert Tag(Area.DB, 1, 0, "INT", count=10).size == 20

    def test_string_sizes(self) -> None:
        assert Tag(Area.DB, 1, 0, "STRING[20]").size == 22
        assert Tag(Area.DB, 1, 0, "WSTRING[10]").size == 24
        assert Tag(Area.DB, 1, 0, "FSTRING[16]").size == 16

    def test_unknown_type_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown S7 type"):
            Tag(Area.DB, 1, 0, "MYSTERY").size  # noqa: B018


class TestLoadCsv:
    """Load tags from CSV files and strings."""

    CSV = """tag,db,offset,type
Motor.Speed,1,0,REAL
Motor.Running,1,4,BOOL
SetPoint,1,6,INT
"""

    def test_from_string(self) -> None:
        tags = load_csv(self.CSV)
        assert len(tags) == 3
        assert "Motor.Speed" in tags
        assert tags["Motor.Speed"].datatype == "REAL"
        assert tags["Motor.Speed"].byte_offset == 0

    def test_bit_column(self) -> None:
        csv = """tag,db,offset,type,bit
Valve.Open,1,4,BOOL,3
"""
        tags = load_csv(csv)
        assert tags["Valve.Open"].bit == 3

    def test_from_file(self, tmp_path: Path) -> None:
        f = tmp_path / "tags.csv"
        f.write_text(self.CSV)
        tags = load_csv(f)
        assert "Motor.Speed" in tags


class TestLoadJson:
    """Load tags from JSON files and strings."""

    DATA = {
        "Tank.Level": {"db": 2, "offset": 10, "type": "INT"},
        "Alarm.Active": {"db": 2, "offset": 20, "bit": 2, "type": "BOOL"},
    }

    def test_from_string(self) -> None:
        tags = load_json(json.dumps(self.DATA))
        assert tags["Tank.Level"].datatype == "INT"
        assert tags["Alarm.Active"].bit == 2

    def test_from_file(self, tmp_path: Path) -> None:
        f = tmp_path / "tags.json"
        f.write_text(json.dumps(self.DATA))
        tags = load_json(f)
        assert "Tank.Level" in tags


class TestFromBrowse:
    """from_browse converts browse results to Tag dicts."""

    def test_classic_browse_result(self) -> None:
        variables = [
            {"name": "Motor.Speed", "db_number": 1, "byte_offset": 0, "data_type": "REAL"},
            {"name": "Motor.Running", "db_number": 1, "byte_offset": 4, "data_type": "BOOL"},
        ]
        tags = from_browse(variables)
        assert "Motor.Speed" in tags
        assert tags["Motor.Speed"].byte_offset == 0
        assert tags["Motor.Speed"].datatype == "REAL"
        assert tags["Motor.Speed"].is_symbolic is False

    def test_symbolic_browse_result(self) -> None:
        """When browse includes LID, produce symbolic Tags."""
        variables = [
            {"name": "Motor.Speed", "db_number": 1, "byte_offset": 0, "data_type": "REAL", "lid": 0xA, "symbol_crc": 0x12345678},
        ]
        tags = from_browse(variables)
        assert tags["Motor.Speed"].is_symbolic is True
        assert tags["Motor.Speed"].access_sequence == [0xA]
        assert tags["Motor.Speed"].symbol_crc == 0x12345678

    def test_skips_unnamed(self) -> None:
        variables = [{"name": "", "db_number": 1, "byte_offset": 0, "data_type": "BYTE"}]
        tags = from_browse(variables)
        assert len(tags) == 0


class TestSymbolicAccess:
    """Tag.from_access_string and symbolic access fields."""

    def test_from_access_string_db(self) -> None:
        # DB1 with LID 0xA
        t = Tag.from_access_string("8A0E0001.A", "REAL", name="Motor.Speed")
        assert t.area == Area.DB
        assert t.db_number == 1
        assert t.access_sequence == [0xA]
        assert t.datatype == "REAL"
        assert t.name == "Motor.Speed"
        assert t.is_symbolic is True

    def test_from_access_string_nested(self) -> None:
        t = Tag.from_access_string("8A0E0005.A.1.3", "INT")
        assert t.db_number == 5
        assert t.access_sequence == [0xA, 0x1, 0x3]

    def test_from_access_string_merker(self) -> None:
        t = Tag.from_access_string("52.A", "BYTE")
        assert t.area == Area.MK
        assert t.access_sequence == [0xA]

    def test_from_access_string_with_crc(self) -> None:
        t = Tag.from_access_string("8A0E0001.A", "REAL", symbol_crc=0x1234ABCD)
        assert t.symbol_crc == 0x1234ABCD

    def test_from_access_string_array(self) -> None:
        t = Tag.from_access_string("8A0E0001.A", "REAL[10]")
        assert t.count == 10
        assert t.size == 40

    def test_is_symbolic_flag(self) -> None:
        classic = Tag(Area.DB, 1, 0, "REAL")
        assert classic.is_symbolic is False

        symbolic = Tag(Area.DB, 1, 0, "REAL", access_sequence=[0xA])
        assert symbolic.is_symbolic is True

    def test_classic_tag_not_symbolic(self) -> None:
        t = Tag.from_string("DB1.DBX0.0:BOOL")
        assert t.is_symbolic is False
        assert t.access_sequence == []


class TestLoadTiaXml:
    """Load tags from TIA Portal XML exports."""

    XML = """<?xml version="1.0"?>
<Document>
  <SW.Blocks.GlobalDB>
    <AttributeList>
      <Number>5</Number>
    </AttributeList>
    <ObjectList>
      <Member Name="Temperature" Datatype="Real" Offset="0" />
      <Member Name="Pressure" Datatype="Real" Offset="4" />
      <Member Name="Running" Datatype="Bool" Offset="8" />
    </ObjectList>
  </SW.Blocks.GlobalDB>
</Document>
"""

    def test_parses_members(self) -> None:
        tags = load_tia_xml(self.XML)
        assert "Temperature" in tags
        assert tags["Temperature"].datatype == "REAL"
        assert tags["Temperature"].db_number == 5
        assert tags["Running"].datatype == "BOOL"

    def test_from_file(self, tmp_path: Path) -> None:
        f = tmp_path / "db.xml"
        f.write_text(self.XML)
        tags = load_tia_xml(f)
        assert len(tags) == 3


class TestNodeS7Parse:
    """Parse nodeS7 / pyS7 style tag addresses."""

    def test_db_bit(self) -> None:
        t = NodeS7Tag.parse("DB1,X0.0")
        assert isinstance(t, NodeS7Tag)
        assert t.area == Area.DB
        assert t.db_number == 1
        assert t.byte_offset == 0
        assert t.bit == 0
        assert t.datatype == "BOOL"

    def test_db_bit_nonzero(self) -> None:
        t = NodeS7Tag.parse("DB2,X10.5")
        assert t.db_number == 2
        assert t.byte_offset == 10
        assert t.bit == 5

    def test_db_byte(self) -> None:
        t = NodeS7Tag.parse("DB1,B10")
        assert t.datatype == "BYTE"
        assert t.byte_offset == 10

    def test_db_word(self) -> None:
        t = NodeS7Tag.parse("DB1,W10")
        assert t.datatype == "WORD"

    def test_db_int(self) -> None:
        t = NodeS7Tag.parse("DB1,I10")
        assert t.datatype == "INT"

    def test_db_dint(self) -> None:
        t = NodeS7Tag.parse("DB1,DI10")
        assert t.datatype == "DINT"

    def test_db_dword(self) -> None:
        t = NodeS7Tag.parse("DB1,DW10")
        assert t.datatype == "DWORD"

    def test_db_real(self) -> None:
        t = NodeS7Tag.parse("DB1,R4")
        assert t.datatype == "REAL"
        assert t.byte_offset == 4

    def test_db_lreal(self) -> None:
        t = NodeS7Tag.parse("DB1,LR8")
        assert t.datatype == "LREAL"

    def test_db_string(self) -> None:
        t = NodeS7Tag.parse("DB1,S10.20")
        assert t.datatype == "STRING[20]"
        assert t.byte_offset == 10
        assert t.size == 22

    def test_db_wstring(self) -> None:
        t = NodeS7Tag.parse("DB1,WS10.10")
        assert t.datatype == "WSTRING[10]"
        assert t.size == 24

    def test_marker_bit(self) -> None:
        t = NodeS7Tag.parse("M10.5")
        assert t.area == Area.MK
        assert t.byte_offset == 10
        assert t.bit == 5
        assert t.datatype == "BOOL"

    def test_marker_byte(self) -> None:
        t = NodeS7Tag.parse("MB10")
        assert t.area == Area.MK
        assert t.datatype == "BYTE"
        assert t.byte_offset == 10

    def test_marker_word(self) -> None:
        t = NodeS7Tag.parse("MW20")
        assert t.datatype == "WORD"
        assert t.byte_offset == 20

    def test_marker_real(self) -> None:
        t = NodeS7Tag.parse("MR4")
        assert t.datatype == "REAL"

    def test_input_bit(self) -> None:
        t = NodeS7Tag.parse("I0.0")
        assert t.area == Area.PE
        assert t.datatype == "BOOL"

    def test_input_word(self) -> None:
        t = NodeS7Tag.parse("IW22")
        assert t.area == Area.PE
        assert t.datatype == "WORD"

    def test_output_real(self) -> None:
        t = NodeS7Tag.parse("QR24")
        assert t.area == Area.PA
        assert t.datatype == "REAL"

    def test_german_input(self) -> None:
        t = NodeS7Tag.parse("E0.0")
        assert t.area == Area.PE

    def test_german_output(self) -> None:
        t = NodeS7Tag.parse("A0.0")
        assert t.area == Area.PA

    def test_case_insensitive(self) -> None:
        t = NodeS7Tag.parse("db1,r4")
        assert t.db_number == 1
        assert t.datatype == "REAL"

    def test_bit_without_suffix_raises(self) -> None:
        with pytest.raises(ValueError, match="bit suffix"):
            NodeS7Tag.parse("DB1,X0")

    def test_string_without_length_raises(self) -> None:
        with pytest.raises(ValueError, match="length suffix"):
            NodeS7Tag.parse("DB1,S0")

    def test_byte_with_suffix_raises(self) -> None:
        with pytest.raises(ValueError, match="does not take"):
            NodeS7Tag.parse("DB1,B0.5")

    def test_bare_area_without_suffix_raises(self) -> None:
        with pytest.raises(ValueError, match="Ambiguous"):
            NodeS7Tag.parse("M10")

    def test_unknown_typecode_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown nodeS7 typecode"):
            NodeS7Tag.parse("DB1,ZZZ0")


class TestParseTagDispatcher:
    """parse_tag autodetects dialect from syntax markers."""

    def test_colon_selects_plc4x(self) -> None:
        t = parse_tag("DB1.DBD0:REAL")
        assert isinstance(t, PLC4XTag)
        assert t.datatype == "REAL"

    def test_comma_selects_nodes7(self) -> None:
        t = parse_tag("DB1,R0")
        assert isinstance(t, NodeS7Tag)
        assert t.datatype == "REAL"

    def test_both_dialects_same_address(self) -> None:
        """PLC4X and nodeS7 renderings of the same address match on canonical fields."""
        p = parse_tag("DB1.DBD4:REAL")
        n = parse_tag("DB1,R4")
        assert p.area == n.area
        assert p.db_number == n.db_number
        assert p.byte_offset == n.byte_offset
        assert p.datatype == n.datatype

    def test_strict_rejects_bare_short_form(self) -> None:
        with pytest.raises(ValueError, match="Ambiguous"):
            parse_tag("M7.1")

    def test_permissive_accepts_bare_short_form(self) -> None:
        t = parse_tag("M7.1", strict=False)
        assert isinstance(t, NodeS7Tag)
        assert t.area == Area.MK
        assert t.datatype == "BOOL"

    def test_permissive_accepts_iw(self) -> None:
        t = parse_tag("IW22", strict=False)
        assert t.area == Area.PE
        assert t.datatype == "WORD"

    def test_strict_is_default(self) -> None:
        with pytest.raises(ValueError):
            parse_tag("IW22")

    def test_name_passed_through(self) -> None:
        t = parse_tag("DB1,R0", name="Motor.Speed")
        assert t.name == "Motor.Speed"


class TestTagStringRendering:
    """__str__ round-trips to each dialect's syntax."""

    def test_plc4x_db_bit(self) -> None:
        t = PLC4XTag.parse("DB1.DBX0.0:BOOL")
        assert str(t) == "DB1.DBX0.0:BOOL"

    def test_plc4x_db_word(self) -> None:
        t = PLC4XTag.parse("DB1.DBW10:INT")
        assert str(t) == "DB1:10:INT"  # canonical short form

    def test_plc4x_merker_bit(self) -> None:
        t = PLC4XTag.parse("M10.5:BOOL")
        assert str(t) == "M10.5:BOOL"

    def test_plc4x_merker_word(self) -> None:
        t = PLC4XTag.parse("MW20:WORD")
        assert str(t) == "M20:WORD"

    def test_plc4x_string(self) -> None:
        t = PLC4XTag.parse("DB1:10:STRING[20]")
        assert str(t) == "DB1:10:STRING[20]"

    def test_plc4x_array(self) -> None:
        t = PLC4XTag.parse("DB1:0:REAL[5]")
        assert str(t) == "DB1:0:REAL[5]"

    def test_nodes7_db_bit(self) -> None:
        t = NodeS7Tag.parse("DB1,X0.0")
        assert str(t) == "DB1,X0.0"

    def test_nodes7_db_real(self) -> None:
        t = NodeS7Tag.parse("DB1,R4")
        assert str(t) == "DB1,R4"

    def test_nodes7_db_string(self) -> None:
        t = NodeS7Tag.parse("DB1,S10.20")
        assert str(t) == "DB1,S10.20"

    def test_nodes7_marker_bit(self) -> None:
        t = NodeS7Tag.parse("M10.5")
        assert str(t) == "M10.5"

    def test_nodes7_marker_word(self) -> None:
        t = NodeS7Tag.parse("MW20")
        assert str(t) == "MW20"

    def test_nodes7_input_word(self) -> None:
        t = NodeS7Tag.parse("IW22")
        assert str(t) == "IW22"

    def test_bare_tag_defaults_to_plc4x(self) -> None:
        t = Tag(area=Area.DB, db_number=1, byte_offset=4, datatype="REAL")
        assert str(t) == "DB1:4:REAL"

    def test_plc4x_tag_isinstance_of_tag(self) -> None:
        t = PLC4XTag.parse("DB1,DBX0.0:BOOL") if False else PLC4XTag.parse("DB1.DBX0.0:BOOL")
        assert isinstance(t, Tag)

    def test_nodes7_tag_isinstance_of_tag(self) -> None:
        t = NodeS7Tag.parse("M10.5")
        assert isinstance(t, Tag)


class TestFromStringBackwardsCompat:
    """Tag.from_string still works and returns PLC4XTag."""

    def test_returns_plc4x_tag(self) -> None:
        t = Tag.from_string("DB1.DBD0:REAL")
        assert isinstance(t, PLC4XTag)
        assert isinstance(t, Tag)
        assert t.datatype == "REAL"
