"""Tests for the S7CommPlus type-info parser (PVartypeList / POffsetInfoType / VarnameList).

Pins the on-wire layouts and the tree-building behaviour browse() relies on to
reconstruct the per-tag symbol tree from a PLC's EXPLORE type-info response.
"""

import struct

from s7 import typeinfo as ti
from s7.protocol import DataType
from s7.vlq import encode_uint32_vlq


def _vartype_list_bytes(*elements: bytes) -> bytes:
    block = b"".join(elements)
    return struct.pack(">H", len(block) + 4) + struct.pack("<I", 1) + block + struct.pack(">H", 0)


def _multiblock_vartype_list_bytes(*blocks: tuple[bytes, ...]) -> bytes:
    """Frame several blocks of elements as a real multi-block PVartypeList.

    The first block carries the leading LE-u32 FirstId (counted in its length);
    subsequent blocks carry only elements. A BE-u16 zero block terminates the list.
    """
    out = b""
    for idx, elements in enumerate(blocks):
        block = b"".join(elements)
        if idx == 0:
            # FirstId is counted inside the first block's length.
            out += struct.pack(">H", len(block) + 4) + struct.pack("<I", 1) + block
        else:
            out += struct.pack(">H", len(block)) + block
    out += struct.pack(">H", 0)  # zero-length terminator block
    return out


def _varname_list_bytes(*names: str) -> bytes:
    block = b"".join(bytes([len(n.encode())]) + n.encode() + b"\x00" for n in names)
    return struct.pack(">H", len(block)) + block + struct.pack(">H", 0)


class TestSoftdatatype:
    def test_known_values(self) -> None:
        assert ti.Softdatatype.BOOL == 1
        assert ti.Softdatatype.BYTE == 2
        assert ti.Softdatatype.INT == 5
        assert ti.Softdatatype.REAL == 8
        assert ti.Softdatatype.LREAL == 48
        assert ti.Softdatatype.BBOOL == 40
        assert ti.Softdatatype.WSTRING == 62
        assert ti.Softdatatype.DTL == 67

    def test_supported_includes_scalars(self) -> None:
        for sdt in (ti.Softdatatype.BOOL, ti.Softdatatype.INT, ti.Softdatatype.REAL, ti.Softdatatype.LREAL):
            assert ti.is_softdatatype_supported(int(sdt))

    def test_supported_excludes_containers(self) -> None:
        # VOID(0), ARRAY(16), STRUCT(17), VARIANT(63) are container/marker types, not leaves.
        for sdt in (0, 16, 17, 63):
            assert not ti.is_softdatatype_supported(sdt)


class TestDatatypeSize:
    def test_one_byte_types(self) -> None:
        for sdt in (
            ti.Softdatatype.BOOL,
            ti.Softdatatype.BYTE,
            ti.Softdatatype.CHAR,
            ti.Softdatatype.USINT,
            ti.Softdatatype.SINT,
            ti.Softdatatype.BBOOL,
        ):
            assert ti.datatype_size(int(sdt)) == 1

    def test_two_byte_types(self) -> None:
        for sdt in (ti.Softdatatype.WORD, ti.Softdatatype.INT, ti.Softdatatype.UINT, ti.Softdatatype.DATE):
            assert ti.datatype_size(int(sdt)) == 2

    def test_four_byte_types(self) -> None:
        for sdt in (ti.Softdatatype.DWORD, ti.Softdatatype.DINT, ti.Softdatatype.REAL, ti.Softdatatype.UDINT):
            assert ti.datatype_size(int(sdt)) == 4

    def test_eight_byte_types(self) -> None:
        for sdt in (ti.Softdatatype.LREAL, ti.Softdatatype.LINT, ti.Softdatatype.LWORD, ti.Softdatatype.ULINT):
            assert ti.datatype_size(int(sdt)) == 8

    def test_dtl_is_twelve(self) -> None:
        assert ti.datatype_size(int(ti.Softdatatype.DTL)) == 12

    def test_string_uses_unspecified_length(self) -> None:
        # STRING/WSTRING stride comes from the array offset-info's first unspecified field + 2.
        assert ti.datatype_size(int(ti.Softdatatype.STRING), string_len=10) == 12

    def test_unknown_is_zero(self) -> None:
        assert ti.datatype_size(0) == 0


def _name_entry(s: str) -> bytes:
    raw = s.encode("utf-8")
    return bytes([len(raw)]) + raw + b"\x00"  # 1-byte len + UTF-8 bytes + null terminator


class TestVarnameList:
    def test_single_block_two_names(self) -> None:
        block = _name_entry("Foo") + _name_entry("Ab")  # 5 + 4 = 9 bytes
        data = struct.pack(">H", len(block)) + block + struct.pack(">H", 0)  # block + zero terminator
        names, off = ti.parse_varname_list(data, 0)
        assert names == ["Foo", "Ab"]
        assert off == len(data)

    def test_empty_list(self) -> None:
        data = struct.pack(">H", 0)  # immediate zero blocklen
        names, off = ti.parse_varname_list(data, 0)
        assert names == []
        assert off == 2

    def test_with_offset(self) -> None:
        block = _name_entry("X")
        data = b"\xff\xff" + struct.pack(">H", len(block)) + block + struct.pack(">H", 0)
        names, off = ti.parse_varname_list(data, 2)
        assert names == ["X"]
        assert off == len(data)


class TestOffsetInfo:
    def test_std_new_code8_opt_then_nonopt(self) -> None:
        # New Std (8): first u16 = optimized, second = non-optimized.
        data = struct.pack("<HH", 4, 20)
        oi, off = ti.parse_offset_info(data, 0, 8)
        assert oi.opt_addr == 4
        assert oi.nonopt_addr == 20
        assert not oi.has_relation and not oi.is_1dim and not oi.is_mdim
        assert off == 4

    def test_std_legacy_code1_nonopt_then_opt(self) -> None:
        # Legacy StructElemStd (1): order swapped — first u16 = non-optimized.
        data = struct.pack("<HH", 20, 4)
        oi, off = ti.parse_offset_info(data, 0, 1)
        assert oi.nonopt_addr == 20
        assert oi.opt_addr == 4

    def test_string_unspecified_and_addresses(self) -> None:
        # String (9): u16 unspec1, u16 unspec2, u32 opt, u32 nonopt.
        data = struct.pack("<HHII", 254, 256, 8, 100)
        oi, off = ti.parse_offset_info(data, 0, 9)
        assert oi.unspecified1 == 254
        assert oi.opt_addr == 8 and oi.nonopt_addr == 100
        assert off == 12

    def test_array1dim(self) -> None:
        # Array1Dim (10): u16,u16,u32 opt,u32 nonopt,i32 lower,u32 count.
        data = struct.pack("<HHIIiI", 0, 0, 16, 50, -3, 10)
        oi, off = ti.parse_offset_info(data, 0, 10)
        assert oi.is_1dim and not oi.has_relation
        assert oi.array_lower_bound == -3
        assert oi.array_element_count == 10
        assert oi.opt_addr == 16 and oi.nonopt_addr == 50
        assert off == 20

    def test_struct_has_relation(self) -> None:
        # Struct (12): u16,u16,u32 opt,u32 nonopt,u32 relid, then 4x u32 structinfo.
        data = struct.pack("<HHIII" + "I" * 4, 0, 0, 0, 0, 0x1234, 0, 0, 0, 0)
        oi, off = ti.parse_offset_info(data, 0, 12)
        assert oi.has_relation
        assert oi.relation_id == 0x1234
        assert off == len(data)

    def test_struct1dim_has_relation_and_array(self) -> None:
        # Struct1Dim (13): u16,u16,u32,u32,i32 lower,u32 count,u32 nonoptsize,u32 optsize,u32 relid,4xu32.
        data = struct.pack("<HHIIiIIII" + "I" * 4, 0, 0, 0, 0, 0, 5, 24, 16, 0x55, 0, 0, 0, 0)
        oi, off = ti.parse_offset_info(data, 0, 13)
        assert oi.has_relation and oi.is_1dim
        assert oi.array_element_count == 5
        assert oi.relation_id == 0x55

    def test_arraymdim_consumes_and_flags(self) -> None:
        # ArrayMDim (11): base 20 + 6 i32 lower bounds + 6 u32 counts = 68 bytes.
        data = (
            struct.pack("<HHIIiI", 0, 0, 0, 0, 0, 12)
            + struct.pack("<6i", 0, 0, 0, 0, 0, 0)
            + struct.pack("<6I", 3, 4, 0, 0, 0, 0)
        )
        oi, off = ti.parse_offset_info(data, 0, 11)
        assert oi.is_mdim and not oi.has_relation
        assert oi.mdim_element_count[:2] == [3, 4]
        assert off == 68

    def test_structmdim_consumes_and_flags(self) -> None:
        # StructMDim (14): 68 (mdim) + nonoptsize,optsize,relid + 4x structinfo = 96 bytes.
        data = (
            struct.pack("<HHIIiI", 0, 0, 0, 0, 0, 1)
            + struct.pack("<6i", *([0] * 6))
            + struct.pack("<6I", *([1] + [0] * 5))
            + struct.pack("<III" + "I" * 4, 8, 8, 0x77, 0, 0, 0, 0)
        )
        oi, off = ti.parse_offset_info(data, 0, 14)
        assert oi.has_relation and oi.is_mdim
        assert oi.relation_id == 0x77
        assert off == 96

    def test_fbsfb_has_relation(self) -> None:
        # FbSfb (15): u16,u16,u32,u32,u32 relid,4x info,u32 retainoff,u32 volatileoff = 40 bytes.
        data = struct.pack("<HHIII" + "I" * 4 + "II", 0, 0, 0, 0, 0x99, 0, 0, 0, 0, 0, 0)
        oi, off = ti.parse_offset_info(data, 0, 15)
        assert oi.has_relation
        assert oi.relation_id == 0x99
        assert off == 40

    def test_fbarray_has_relation(self) -> None:
        # FbArray (0): 12 base + relid+4info(20) + 6 section u32 (24) + 6 i32 + 6 u32 = 104 bytes.
        data = (
            struct.pack("<HHII", 0, 0, 0, 0)
            + struct.pack("<I" + "I" * 4, 0xAB, 0, 0, 0, 0)
            + struct.pack("<6I", *([0] * 6))
            + struct.pack("<6i", *([0] * 6))
            + struct.pack("<6I", *([0] * 6))
        )
        oi, off = ti.parse_offset_info(data, 0, 0)
        assert oi.has_relation
        assert oi.relation_id == 0xAB
        assert off == 104


def _element(lid: int, crc: int, sdt: int, attr_flags: int, bitoff_flags: int, offset_info: bytes) -> bytes:
    # LID (u32 LE) + SymbolCrc (u32 LE) + Softdatatype (1B) + AttributeFlags (u16 BE!) +
    # BitoffsetinfoFlags (1B) + offset-info bytes.
    return struct.pack("<II", lid, crc) + bytes([sdt]) + struct.pack(">H", attr_flags) + bytes([bitoff_flags]) + offset_info


class TestVartypeElement:
    def test_scalar_int_std(self) -> None:
        # offsetinfotype = 8 (Std) lives in AttributeFlags bits 12..15 → 0x8000.
        data = _element(5, 0, int(ti.Softdatatype.INT), 0x8000, 0x00, struct.pack("<HH", 4, 20))
        el, off = ti.parse_vartype_element(data, 0)
        assert el.lid == 5
        assert el.softdatatype == int(ti.Softdatatype.INT)
        assert el.offsetinfotype == 8
        assert el.offset_info.opt_addr == 4 and el.offset_info.nonopt_addr == 20
        assert off == 16  # 4+4+1+2+1+4

    def test_bool_attribute_bitoffset(self) -> None:
        # AttributeFlags low 3 bits carry the optimized bit offset for a BOOL.
        data = _element(7, 0, int(ti.Softdatatype.BOOL), 0x8000 | 0x0003, 0x00, struct.pack("<HH", 1, 2))
        el, _ = ti.parse_vartype_element(data, 0)
        assert el.attribute_bitoffset == 3

    def test_bitoffsetinfo_accessors(self) -> None:
        # BitoffsetinfoFlags: 0x70 nonopt bitoffset (>>4), 0x08 classic, 0x07 opt bitoffset.
        data = _element(1, 0, int(ti.Softdatatype.BOOL), 0x8000, 0x58, struct.pack("<HH", 0, 0))  # 0x58 = 0101_1000
        el, _ = ti.parse_vartype_element(data, 0)
        assert el.nonopt_bitoffset == 5  # (0x58 & 0x70) >> 4
        assert el.classic is True  # 0x58 & 0x08
        assert el.opt_bitoffset == 0  # 0x58 & 0x07


class TestVartypeList:
    def test_two_elements_one_block(self) -> None:
        e1 = _element(1, 0, int(ti.Softdatatype.INT), 0x8000, 0, struct.pack("<HH", 0, 0))  # 16 bytes
        e2 = _element(2, 0, int(ti.Softdatatype.REAL), 0x8000, 0, struct.pack("<HH", 2, 4))  # 16 bytes
        block = e1 + e2  # 32 bytes
        # first block: BE-u16 blocklen, then u32-LE FirstId, then the elements; zero terminator.
        data = struct.pack(">H", len(block) + 4) + struct.pack("<I", 1) + block + struct.pack(">H", 0)
        elements, off = ti.parse_vartype_list(data, 0)
        assert [e.lid for e in elements] == [1, 2]
        assert elements[1].softdatatype == int(ti.Softdatatype.REAL)
        assert off == len(data)

    def test_multi_block_returns_all_elements(self) -> None:
        # A real PLC splits a long element list across multiple blocks. Only the
        # first block has the leading FirstId; later blocks are pure elements.
        e1 = _element(1, 0, int(ti.Softdatatype.INT), 0x8000, 0, struct.pack("<HH", 0, 0))  # 16 bytes
        e2 = _element(2, 0, int(ti.Softdatatype.REAL), 0x8000, 0, struct.pack("<HH", 2, 4))  # 16 bytes
        e3 = _element(3, 0, int(ti.Softdatatype.DINT), 0x8000, 0, struct.pack("<HH", 8, 12))  # 16 bytes
        e4 = _element(4, 0, int(ti.Softdatatype.BOOL), 0x8000, 0, struct.pack("<HH", 14, 16))  # 16 bytes
        e5 = _element(5, 0, int(ti.Softdatatype.BYTE), 0x8000, 0, struct.pack("<HH", 15, 17))  # 16 bytes
        # Three non-empty blocks before the zero terminator: (e1,e2), (e3), (e4,e5).
        data = _multiblock_vartype_list_bytes((e1, e2), (e3,), (e4, e5))
        elements, off = ti.parse_vartype_list(data, 0)
        # ALL elements across ALL blocks are returned, in order.
        assert [e.lid for e in elements] == [1, 2, 3, 4, 5]
        assert elements[2].softdatatype == int(ti.Softdatatype.DINT)
        # Cursor lands exactly past the zero terminator (no mid-stream stop).
        assert off == len(data)

    def test_multi_block_offset_feeds_following_field(self) -> None:
        # The bug left the cursor mid-stream on multi-block lists, corrupting the
        # next field. Verify the returned offset cleanly points at trailing data.
        e1 = _element(1, 0, int(ti.Softdatatype.INT), 0x8000, 0, struct.pack("<HH", 0, 0))
        e2 = _element(2, 0, int(ti.Softdatatype.REAL), 0x8000, 0, struct.pack("<HH", 2, 4))
        vt = _multiblock_vartype_list_bytes((e1,), (e2,))
        sentinel = b"\xde\xad\xbe\xef"
        data = vt + sentinel
        elements, off = ti.parse_vartype_list(data, 0)
        assert [e.lid for e in elements] == [1, 2]
        assert data[off:] == sentinel


def _obj_header(relid: int, class_id: int) -> bytes:
    return bytes([0xA1]) + struct.pack(">I", relid) + encode_uint32_vlq(class_id) + encode_uint32_vlq(0) + encode_uint32_vlq(0)


class TestParseObject:
    def test_header_attribute_vartype_varname(self) -> None:
        el = _element(10, 0, int(ti.Softdatatype.INT), 0x8000, 0, struct.pack("<HH", 2, 4))
        body = _obj_header(0x8A0E0001, 2574)
        # Attribute 1502 (TI_TComSize) = UDINT-ish; use a USINT PValue for the test.
        body += bytes([0xA3]) + encode_uint32_vlq(1502) + bytes([0x00, DataType.USINT, 24])
        body += bytes([0xAB]) + _vartype_list_bytes(el)
        body += bytes([0xAC]) + _varname_list_bytes("Speed")
        body += bytes([0xA2])  # TerminatingObject
        obj, off = ti.parse_object(body, 0)
        assert obj.relation_id == 0x8A0E0001
        assert obj.class_id == 2574
        assert obj.attributes[1502] == bytes([24])
        assert [e.lid for e in obj.vartype_list] == [10]
        assert obj.varname_list == ["Speed"]
        assert off == len(body)

    def test_nested_child_object(self) -> None:
        child = _obj_header(0x00000002, 511) + bytes([0xA2])
        parent = _obj_header(0x00000001, 534) + child + bytes([0xA2])
        obj, off = ti.parse_object(parent, 0)
        assert obj.relation_id == 1 and obj.class_id == 534
        assert len(obj.objects) == 1
        assert obj.objects[0].relation_id == 2 and obj.objects[0].class_id == 511
        assert off == len(parent)

    def test_object_list_two_siblings(self) -> None:
        a = _obj_header(1, 511) + bytes([0xA2])
        b = _obj_header(2, 511) + bytes([0xA2])
        objs, off = ti.parse_object_list(a + b, 0)
        assert [o.relation_id for o in objs] == [1, 2]
        assert off == len(a + b)


def _vte(lid: int, sdt, oi: "ti.OffsetInfo", attr_flags: int = 0, bitoff: int = 0) -> "ti.VartypeListElement":
    return ti.VartypeListElement(
        lid=lid, symbol_crc=0, softdatatype=int(sdt), attribute_flags=attr_flags, bitoffsetinfo_flags=bitoff, offset_info=oi
    )


def _root(name: str, relid_db: int, ti_relid: int) -> "ti.Node":
    return ti.Node(node_type=ti.NodeType.ROOT, name=name, access_id=relid_db, relation_id=ti_relid)


class TestTreeBuilder:
    def test_scalar_leaf(self) -> None:
        root = _root("DB1", 0x8A0E0001, 0x100)
        type_obj = ti.PObject(
            relation_id=0x100,
            vartype_list=[_vte(10, ti.Softdatatype.INT, ti.OffsetInfo(code=8, opt_addr=2, nonopt_addr=4))],
            varname_list=["Speed"],
        )
        ti.build_tree([root], [type_obj])
        infos = ti.build_flat_list([root])
        assert len(infos) == 1
        v = infos[0]
        assert v.name == "DB1.Speed"
        assert v.access_sequence == "8A0E0001.A"  # DB relid + LID 0xA
        assert v.softdatatype == int(ti.Softdatatype.INT)
        assert v.opt_address == 2 and v.nonopt_address == 4

    def test_nested_struct_offsets_accumulate(self) -> None:
        root = _root("DB1", 0x8A0E0001, 0x100)
        outer = ti.PObject(
            relation_id=0x100,
            vartype_list=[
                _vte(
                    5,
                    ti.Softdatatype.STRUCT,
                    ti.OffsetInfo(code=12, opt_addr=10, nonopt_addr=100, relation_id=0x200, has_relation=True),
                )
            ],
            varname_list=["Motor"],
        )
        inner = ti.PObject(
            relation_id=0x200,
            vartype_list=[_vte(3, ti.Softdatatype.INT, ti.OffsetInfo(code=8, opt_addr=6, nonopt_addr=8))],
            varname_list=["Rpm"],
        )
        ti.build_tree([root], [outer, inner])
        infos = ti.build_flat_list([root])
        assert len(infos) == 1
        v = infos[0]
        assert v.name == "DB1.Motor.Rpm"
        assert v.access_sequence == "8A0E0001.5.3"
        assert v.opt_address == 16  # 10 (Motor) + 6 (Rpm)
        assert v.nonopt_address == 108

    def test_basic_array_elements(self) -> None:
        root = _root("DB1", 0x8A0E0001, 0x100)
        type_obj = ti.PObject(
            relation_id=0x100,
            vartype_list=[
                _vte(
                    9,
                    ti.Softdatatype.INT,
                    ti.OffsetInfo(code=10, opt_addr=20, nonopt_addr=40, array_element_count=3, array_lower_bound=0, is_1dim=True),
                )
            ],
            varname_list=["Vals"],
        )
        ti.build_tree([root], [type_obj])
        infos = ti.build_flat_list([root])
        assert [v.name for v in infos] == ["DB1.Vals[0]", "DB1.Vals[1]", "DB1.Vals[2]"]
        assert [v.access_sequence for v in infos] == ["8A0E0001.9.0", "8A0E0001.9.1", "8A0E0001.9.2"]
        assert [v.opt_address for v in infos] == [20, 22, 24]  # base + i*2 (INT stride)

    def test_struct_array_inserts_extra_one(self) -> None:
        root = _root("DB1", 0x8A0E0001, 0x100)
        outer = ti.PObject(
            relation_id=0x100,
            vartype_list=[
                _vte(
                    7,
                    ti.Softdatatype.STRUCT,
                    ti.OffsetInfo(
                        code=13,
                        opt_addr=0,
                        nonopt_addr=0,
                        array_element_count=2,
                        array_lower_bound=0,
                        relation_id=0x300,
                        has_relation=True,
                        is_1dim=True,
                    ),
                )
            ],
            varname_list=["Items"],
        )
        item_type = ti.PObject(
            relation_id=0x300,
            attributes={1502: struct.pack(">I", 8)},  # TI_TComSize = 8-byte struct stride
            vartype_list=[_vte(2, ti.Softdatatype.REAL, ti.OffsetInfo(code=8, opt_addr=0, nonopt_addr=0))],
            varname_list=["X"],
        )
        ti.build_tree([root], [outer, item_type])
        infos = ti.build_flat_list([root])
        assert [v.name for v in infos] == ["DB1.Items[0].X", "DB1.Items[1].X"]
        # StructArray inserts a ".1" between the array index id and the member LID.
        assert [v.access_sequence for v in infos] == ["8A0E0001.7.0.1.2", "8A0E0001.7.1.1.2"]
        assert [v.opt_address for v in infos] == [0, 8]  # element stride 8


class TestMDimArrays:
    def test_basic_mdim_array_ordering_bounds_and_offsets(self) -> None:
        # ARRAY[1..3, 10..11] of INT — dim0 (fastest, in-memory) has 3 elements, dim1 has 2.
        # The name lists the highest dimension first: [dim1, dim0].
        root = _root("DB1", 0x8A0E0001, 0x100)
        type_obj = ti.PObject(
            relation_id=0x100,
            vartype_list=[
                _vte(
                    9,
                    ti.Softdatatype.INT,
                    ti.OffsetInfo(
                        code=11,
                        opt_addr=20,
                        nonopt_addr=40,
                        array_element_count=6,
                        mdim_element_count=[3, 2, 0, 0, 0, 0],
                        mdim_lower_bounds=[1, 10, 0, 0, 0, 0],
                        is_mdim=True,
                    ),
                )
            ],
            varname_list=["Grid"],
        )
        ti.build_tree([root], [type_obj])
        infos = ti.build_flat_list([root])
        assert [v.name for v in infos] == [
            "DB1.Grid[10,1]",
            "DB1.Grid[10,2]",
            "DB1.Grid[10,3]",
            "DB1.Grid[11,1]",
            "DB1.Grid[11,2]",
            "DB1.Grid[11,3]",
        ]
        assert [v.access_sequence for v in infos] == [
            "8A0E0001.9.0",
            "8A0E0001.9.1",
            "8A0E0001.9.2",
            "8A0E0001.9.3",
            "8A0E0001.9.4",
            "8A0E0001.9.5",
        ]
        assert [v.opt_address for v in infos] == [20, 22, 24, 26, 28, 30]  # base + (n-1)*2
        assert [v.nonopt_address for v in infos] == [40, 42, 44, 46, 48, 50]

    def test_bbool_mdim_access_id_aligns_to_byte(self) -> None:
        # ARRAY[0..2, 0..1] of BOOL stored as BBOOL: each row of 3 bits rounds up to a byte,
        # so the access-id of the second row starts at 8, not 3. Offsets stay linear (n-1).
        root = _root("DB1", 0x8A0E0001, 0x100)
        type_obj = ti.PObject(
            relation_id=0x100,
            vartype_list=[
                _vte(
                    7,
                    ti.Softdatatype.BBOOL,
                    ti.OffsetInfo(
                        code=11,
                        opt_addr=0,
                        nonopt_addr=0,
                        array_element_count=6,
                        mdim_element_count=[3, 2, 0, 0, 0, 0],
                        mdim_lower_bounds=[0, 0, 0, 0, 0, 0],
                        is_mdim=True,
                    ),
                )
            ],
            varname_list=["Flags"],
        )
        ti.build_tree([root], [type_obj])
        infos = ti.build_flat_list([root])
        assert [v.name for v in infos] == [
            "DB1.Flags[0,0]",
            "DB1.Flags[0,1]",
            "DB1.Flags[0,2]",
            "DB1.Flags[1,0]",
            "DB1.Flags[1,1]",
            "DB1.Flags[1,2]",
        ]
        assert [v.access_sequence for v in infos] == [
            "8A0E0001.7.0",
            "8A0E0001.7.1",
            "8A0E0001.7.2",
            "8A0E0001.7.8",
            "8A0E0001.7.9",
            "8A0E0001.7.A",
        ]

    def test_struct_mdim_array_inserts_extra_one(self) -> None:
        # ARRAY[0..1, 0..1] of <struct> — StructArray nodes insert ".1" and stride by TComSize.
        root = _root("DB1", 0x8A0E0001, 0x100)
        outer = ti.PObject(
            relation_id=0x100,
            vartype_list=[
                _vte(
                    7,
                    ti.Softdatatype.STRUCT,
                    ti.OffsetInfo(
                        code=14,
                        opt_addr=0,
                        nonopt_addr=0,
                        array_element_count=4,
                        mdim_element_count=[2, 2, 0, 0, 0, 0],
                        mdim_lower_bounds=[0, 0, 0, 0, 0, 0],
                        relation_id=0x300,
                        has_relation=True,
                        is_mdim=True,
                    ),
                )
            ],
            varname_list=["Cells"],
        )
        item_type = ti.PObject(
            relation_id=0x300,
            attributes={1502: struct.pack(">I", 8)},  # TI_TComSize = 8-byte struct stride
            vartype_list=[_vte(2, ti.Softdatatype.REAL, ti.OffsetInfo(code=8, opt_addr=0, nonopt_addr=0))],
            varname_list=["X"],
        )
        ti.build_tree([root], [outer, item_type])
        infos = ti.build_flat_list([root])
        assert [v.name for v in infos] == [
            "DB1.Cells[0,0].X",
            "DB1.Cells[0,1].X",
            "DB1.Cells[1,0].X",
            "DB1.Cells[1,1].X",
        ]
        assert [v.access_sequence for v in infos] == [
            "8A0E0001.7.0.1.2",
            "8A0E0001.7.1.1.2",
            "8A0E0001.7.2.1.2",
            "8A0E0001.7.3.1.2",
        ]
        assert [v.opt_address for v in infos] == [0, 8, 16, 24]  # (n-1) * TComSize


class TestExtractTypeInfoObjects:
    def test_finds_container_children(self) -> None:
        child1 = _obj_header(0x100, 511) + bytes([0xA2])
        child2 = _obj_header(0x200, 511) + bytes([0xA2])
        container = _obj_header(0x537, ti.CLASS_OMS_TYPE_INFO_CONTAINER) + child1 + child2 + bytes([0xA2])
        response = bytes([0x00]) + container  # leading return-value VLQ + the container object
        objs = ti.extract_type_info_objects(response)
        assert [o.relation_id for o in objs] == [0x100, 0x200]

    def test_no_container_returns_empty(self) -> None:
        response = bytes([0x00]) + _obj_header(1, 999) + bytes([0xA2])
        assert ti.extract_type_info_objects(response) == []

    def test_skips_preamble_before_first_object(self) -> None:
        # Real EXPLORE(537) responses carry several preamble bytes between the return-value
        # and the first StartOfObject (0xA1) — the parser must skip to it.
        child = _obj_header(0x100, 511) + bytes([0xA2])
        container = _obj_header(0x219, ti.CLASS_OMS_TYPE_INFO_CONTAINER) + child + bytes([0xA2])
        response = bytes([0x00, 0x00, 0x00, 0x00, 0xC9, 0x4F]) + container  # 6-byte preamble
        objs = ti.extract_type_info_objects(response)
        assert [o.relation_id for o in objs] == [0x100]
