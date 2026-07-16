"""S7CommPlus type-info parsing and symbol-tree reconstruction.

Decodes the type-information container returned by an S7-1500's EXPLORE response
and flattens it into a list of readable tags. The structures below follow the
S7CommPlus wire protocol (PVartypeList, POffsetInfoType, the PObject tree and the
VarnameList) as observed on an S7-1500 and documented publicly.

The end product is a flat list of :class:`VarInfo` records, each carrying the
symbolic name, the access sequence (used to address the tag), the software
datatype and the optimized / non-optimized byte (and bit) offsets.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field
from enum import IntEnum

from .codec import decode_pvalue_to_bytes
from .protocol import DataType  # noqa: F401  (re-exported convenience for callers)
from .vlq import decode_uint32_vlq

# -- Element ID tags in the PObject stream --

START_OF_OBJECT = 0xA1
TERMINATING_OBJECT = 0xA2
ATTRIBUTE = 0xA3
VARTYPE_LIST = 0xAB
VARNAME_LIST = 0xAC

# Class id of the container object holding the per-type objects.
CLASS_OMS_TYPE_INFO_CONTAINER = 534

# Attribute id carrying a struct/UDT byte size (TI_TComSize), stored as big-endian u32.
TI_TCOM_SIZE = 1502


# ---------------------------------------------------------------------------
# 1. Software datatypes
# ---------------------------------------------------------------------------


class Softdatatype(IntEnum):
    """PLC "software datatype" ids (distinct from the PValue wire DataType)."""

    VOID = 0
    BOOL = 1
    BYTE = 2
    CHAR = 3
    WORD = 4
    INT = 5
    DWORD = 6
    DINT = 7
    REAL = 8
    DATE = 9
    TIMEOFDAY = 10
    TIME = 11
    S5TIME = 12
    DATEANDTIME = 14
    INTERNETTIME = 15
    ARRAY = 16
    STRUCT = 17
    ENDSTRUCT = 18
    STRING = 19
    POINTER = 20
    MULTIFB = 21
    ANY = 22
    BLOCKFB = 23
    BLOCKFC = 24
    BLOCKDB = 25
    BLOCKSDB = 26
    COUNTER = 28
    TIMER = 29
    BBOOL = 40
    LREAL = 48
    ULINT = 49
    LINT = 50
    LWORD = 51
    USINT = 52
    UINT = 53
    UDINT = 54
    SINT = 55
    WCHAR = 61
    WSTRING = 62
    VARIANT = 63
    LTIME = 64
    LTOD = 65
    LDT = 66
    DTL = 67
    REMOTE = 96
    AOMIDENT = 128


# Leaf datatypes that browse() emits as readable tags. Containers and markers
# (VOID, ARRAY, STRUCT, ENDSTRUCT, MULTIFB, VARIANT, DTL, system ids) are not
# leaves — their members are emitted instead.
SUPPORTED_SOFTDATATYPES = frozenset(
    {
        Softdatatype.BOOL,
        Softdatatype.BYTE,
        Softdatatype.CHAR,
        Softdatatype.WORD,
        Softdatatype.INT,
        Softdatatype.DWORD,
        Softdatatype.DINT,
        Softdatatype.REAL,
        Softdatatype.DATE,
        Softdatatype.TIMEOFDAY,
        Softdatatype.TIME,
        Softdatatype.S5TIME,
        Softdatatype.DATEANDTIME,
        Softdatatype.STRING,
        Softdatatype.POINTER,
        Softdatatype.ANY,
        Softdatatype.BBOOL,
        Softdatatype.LREAL,
        Softdatatype.ULINT,
        Softdatatype.LINT,
        Softdatatype.LWORD,
        Softdatatype.USINT,
        Softdatatype.UINT,
        Softdatatype.UDINT,
        Softdatatype.SINT,
        Softdatatype.WCHAR,
        Softdatatype.WSTRING,
        Softdatatype.LTIME,
        Softdatatype.LTOD,
        Softdatatype.LDT,
    }
)


def is_softdatatype_supported(code: int) -> bool:
    """True if ``code`` is a leaf datatype browse() emits as a readable tag."""
    return code in SUPPORTED_SOFTDATATYPES


_SIZE_1 = {
    Softdatatype.BOOL,
    Softdatatype.BYTE,
    Softdatatype.CHAR,
    Softdatatype.USINT,
    Softdatatype.SINT,
    Softdatatype.BBOOL,
}
_SIZE_2 = {
    Softdatatype.WORD,
    Softdatatype.INT,
    Softdatatype.UINT,
    Softdatatype.DATE,
    Softdatatype.S5TIME,
    Softdatatype.WCHAR,
}
_SIZE_4 = {
    Softdatatype.DWORD,
    Softdatatype.DINT,
    Softdatatype.REAL,
    Softdatatype.TIMEOFDAY,
    Softdatatype.TIME,
    Softdatatype.UDINT,
}
_SIZE_8 = {
    Softdatatype.LREAL,
    Softdatatype.ULINT,
    Softdatatype.LINT,
    Softdatatype.LWORD,
    Softdatatype.DATEANDTIME,
    Softdatatype.LTIME,
    Softdatatype.LTOD,
    Softdatatype.LDT,
}


def datatype_size(code: int, *, string_len: int = 0) -> int:
    """Element byte stride for a software datatype.

    ``string_len`` is the array offset-info's ``unspecified1`` and is only used
    for STRING / WSTRING (whose stride is ``string_len + 2``).
    """
    if code in _SIZE_1:
        return 1
    if code in _SIZE_2:
        return 2
    if code in _SIZE_4:
        return 4
    if code in _SIZE_8:
        return 8
    if code == Softdatatype.DTL:
        return 12
    if code == Softdatatype.POINTER:
        return 6
    if code in (Softdatatype.ANY, Softdatatype.REMOTE):
        return 10
    if code in (Softdatatype.STRING, Softdatatype.WSTRING):
        return string_len + 2
    return 0


# ---------------------------------------------------------------------------
# 3. POffsetInfoType
# ---------------------------------------------------------------------------


@dataclass
class OffsetInfo:
    """Union of the address/dimension info attached to a vartype element."""

    code: int = 0
    opt_addr: int = 0
    nonopt_addr: int = 0
    unspecified1: int = 0
    unspecified2: int = 0
    array_lower_bound: int = 0
    array_element_count: int = 0
    mdim_lower_bounds: list[int] = field(default_factory=lambda: [0] * 6)
    mdim_element_count: list[int] = field(default_factory=lambda: [0] * 6)
    nonopt_struct_size: int = 0
    opt_struct_size: int = 0
    relation_id: int = 0
    is_1dim: bool = False
    is_mdim: bool = False
    has_relation: bool = False


def parse_offset_info(data: bytes, offset: int, offsetinfotype: int) -> tuple[OffsetInfo, int]:
    """Parse a POffsetInfoType selected by ``offsetinfotype`` (0..15)."""
    oi = OffsetInfo(code=offsetinfotype)

    if offsetinfotype in (1, 8):  # Std
        a, b = struct.unpack_from("<HH", data, offset)
        if offsetinfotype == 8:
            oi.opt_addr, oi.nonopt_addr = a, b
        else:  # legacy: order swapped
            oi.nonopt_addr, oi.opt_addr = a, b
        return oi, offset + 4

    if offsetinfotype in (2, 9):  # String
        oi.unspecified1, oi.unspecified2, oi.opt_addr, oi.nonopt_addr = struct.unpack_from("<HHII", data, offset)
        return oi, offset + 12

    if offsetinfotype in (3, 10):  # Array1Dim
        (oi.unspecified1, oi.unspecified2, oi.opt_addr, oi.nonopt_addr, oi.array_lower_bound, oi.array_element_count) = (
            struct.unpack_from("<HHIIiI", data, offset)
        )
        oi.is_1dim = True
        return oi, offset + 20

    if offsetinfotype in (4, 11):  # ArrayMDim
        (oi.unspecified1, oi.unspecified2, oi.opt_addr, oi.nonopt_addr, oi.array_lower_bound, oi.array_element_count) = (
            struct.unpack_from("<HHIIiI", data, offset)
        )
        offset += 20
        oi.mdim_lower_bounds = list(struct.unpack_from("<6i", data, offset))
        offset += 24
        oi.mdim_element_count = list(struct.unpack_from("<6I", data, offset))
        offset += 24
        oi.is_mdim = True
        return oi, offset

    if offsetinfotype in (5, 12):  # Struct
        vals = struct.unpack_from("<HHIII4I", data, offset)
        oi.unspecified1, oi.unspecified2, oi.opt_addr, oi.nonopt_addr, oi.relation_id = vals[:5]
        oi.has_relation = True
        return oi, offset + struct.calcsize("<HHIII4I")

    if offsetinfotype in (6, 13):  # Struct1Dim
        vals = struct.unpack_from("<HHIIiIIII4I", data, offset)
        (
            oi.unspecified1,
            oi.unspecified2,
            oi.opt_addr,
            oi.nonopt_addr,
            oi.array_lower_bound,
            oi.array_element_count,
            oi.nonopt_struct_size,
            oi.opt_struct_size,
            oi.relation_id,
        ) = vals[:9]
        oi.has_relation = True
        oi.is_1dim = True
        return oi, offset + struct.calcsize("<HHIIiIIII4I")

    if offsetinfotype in (7, 14):  # StructMDim
        (oi.unspecified1, oi.unspecified2, oi.opt_addr, oi.nonopt_addr, oi.array_lower_bound, oi.array_element_count) = (
            struct.unpack_from("<HHIIiI", data, offset)
        )
        offset += 20
        oi.mdim_lower_bounds = list(struct.unpack_from("<6i", data, offset))
        offset += 24
        oi.mdim_element_count = list(struct.unpack_from("<6I", data, offset))
        offset += 24
        tail = struct.unpack_from("<III4I", data, offset)
        oi.nonopt_struct_size, oi.opt_struct_size, oi.relation_id = tail[:3]
        offset += struct.calcsize("<III4I")
        oi.has_relation = True
        oi.is_mdim = True
        return oi, offset

    if offsetinfotype == 15:  # FbSfb
        vals = struct.unpack_from("<HHIII4III", data, offset)
        oi.unspecified1, oi.unspecified2, oi.opt_addr, oi.nonopt_addr, oi.relation_id = vals[:5]
        oi.has_relation = True
        return oi, offset + struct.calcsize("<HHIII4III")

    if offsetinfotype == 0:  # FbArray
        oi.unspecified1, oi.unspecified2, oi.opt_addr, oi.nonopt_addr = struct.unpack_from("<HHII", data, offset)
        offset += 12
        relinfo = struct.unpack_from("<I4I", data, offset)
        oi.relation_id = relinfo[0]
        offset += 20
        sections = struct.unpack_from("<6I", data, offset)
        oi.array_element_count = sections[2]
        offset += 24
        oi.mdim_lower_bounds = list(struct.unpack_from("<6i", data, offset))
        offset += 24
        oi.mdim_element_count = list(struct.unpack_from("<6I", data, offset))
        offset += 24
        oi.has_relation = True
        return oi, offset

    raise ValueError(f"Unsupported offsetinfotype: {offsetinfotype}")


# ---------------------------------------------------------------------------
# 4. VartypeListElement & PVartypeList
# ---------------------------------------------------------------------------


@dataclass
class VartypeListElement:
    """One entry of a PVartypeList describing a single member's address/type."""

    lid: int = 0
    symbol_crc: int = 0
    softdatatype: int = 0
    attribute_flags: int = 0
    bitoffsetinfo_flags: int = 0
    offset_info: OffsetInfo = field(default_factory=OffsetInfo)

    @property
    def offsetinfotype(self) -> int:
        """The 4-bit POffsetInfoType selector held in AttributeFlags bits 12..15."""
        return (self.attribute_flags >> 12) & 0x0F

    @property
    def attribute_bitoffset(self) -> int:
        """Optimized bit offset carried in the low 3 bits of AttributeFlags."""
        return self.attribute_flags & 0x07

    @property
    def nonopt_bitoffset(self) -> int:
        return (self.bitoffsetinfo_flags & 0x70) >> 4

    @property
    def opt_bitoffset(self) -> int:
        return self.bitoffsetinfo_flags & 0x07

    @property
    def classic(self) -> bool:
        return bool(self.bitoffsetinfo_flags & 0x08)


def parse_vartype_element(data: bytes, offset: int) -> tuple[VartypeListElement, int]:
    """Parse one VartypeListElement and its embedded POffsetInfoType."""
    lid, symbol_crc = struct.unpack_from("<II", data, offset)
    offset += 8
    softdatatype = data[offset]
    offset += 1
    (attribute_flags,) = struct.unpack_from(">H", data, offset)
    offset += 2
    bitoffsetinfo_flags = data[offset]
    offset += 1

    el = VartypeListElement(
        lid=lid,
        symbol_crc=symbol_crc,
        softdatatype=softdatatype,
        attribute_flags=attribute_flags,
        bitoffsetinfo_flags=bitoffsetinfo_flags,
    )
    el.offset_info, offset = parse_offset_info(data, offset, el.offsetinfotype)
    return el, offset


def parse_vartype_list(data: bytes, offset: int) -> tuple[list[VartypeListElement], int]:
    """Parse a PVartypeList.

    Framing: a sequence of one or more blocks, terminated by a zero-length block.
    Each block opens with a BE-u16 block length (``block_end = offset_after_len +
    block_length``). Only the very first block carries a leading LE-u32 FirstId
    (a starting index, counted inside that block's length) before its elements.
    Elements are read until ``offset >= block_end`` (at least one per block). A
    following BE-u16 length > 0 is a further block of elements (no FirstId); a
    length of 0 terminates the list (its 2 bytes are consumed).

    Real PLCs split a long element list across multiple blocks, so the loop is
    mandatory — treating it as a single block plus a 2-byte terminator misaligns
    the cursor and corrupts the subsequent VarnameList parse.
    """
    elements: list[VartypeListElement] = []
    first_block = True
    while True:
        (block_len,) = struct.unpack_from(">H", data, offset)
        offset += 2
        if block_len == 0:
            # Zero-length block terminates the list.
            break
        block_end = offset + block_len
        if first_block:
            offset += 4  # leading LE-u32 FirstId — a starting index, not a count
            first_block = False
        # At least one element per block; read until the block is consumed.
        while offset < block_end:
            el, offset = parse_vartype_element(data, offset)
            elements.append(el)
    return elements, offset


# ---------------------------------------------------------------------------
# 5/6. PObject tree & VarnameList
# ---------------------------------------------------------------------------


def parse_varname_list(data: bytes, offset: int) -> tuple[list[str], int]:
    """Parse a VarnameList: BE-u16 block lengths of name entries, ending at a zero block."""
    names: list[str] = []
    while True:
        (block_len,) = struct.unpack_from(">H", data, offset)
        offset += 2
        if block_len == 0:
            break
        end = offset + block_len
        while offset < end:
            name_len = data[offset]
            offset += 1
            raw = data[offset : offset + name_len]
            offset += name_len
            offset += 1  # trailing zero byte
            names.append(raw.decode("utf-8", errors="replace"))
    return names, offset


@dataclass
class PObject:
    """A node of the S7CommPlus object tree (one type / container / nested object)."""

    relation_id: int = 0
    class_id: int = 0
    attributes: dict[int, bytes] = field(default_factory=dict)
    vartype_list: list[VartypeListElement] = field(default_factory=list)
    varname_list: list[str] = field(default_factory=list)
    objects: list["PObject"] = field(default_factory=list)


def parse_object(data: bytes, offset: int) -> tuple[PObject, int]:
    """Parse a single PObject starting at a 0xA1 tag, up to its 0xA2 terminator."""
    assert data[offset] == START_OF_OBJECT
    offset += 1
    (relation_id,) = struct.unpack_from(">I", data, offset)
    offset += 4
    class_id, consumed = decode_uint32_vlq(data, offset)
    offset += consumed
    for _ in range(2):  # ClassFlags, AttributeId
        _, consumed = decode_uint32_vlq(data, offset)
        offset += consumed

    obj = PObject(relation_id=relation_id, class_id=class_id)

    while offset < len(data):
        tag = data[offset]
        if tag == TERMINATING_OBJECT:
            offset += 1
            break
        if tag == ATTRIBUTE:
            offset += 1
            attr_id, consumed = decode_uint32_vlq(data, offset)
            offset += consumed
            value, consumed = decode_pvalue_to_bytes(data, offset)
            offset += consumed
            obj.attributes[attr_id] = value
        elif tag == VARTYPE_LIST:
            offset += 1
            obj.vartype_list, offset = parse_vartype_list(data, offset)
        elif tag == VARNAME_LIST:
            offset += 1
            obj.varname_list, offset = parse_varname_list(data, offset)
        elif tag == START_OF_OBJECT:
            child, offset = parse_object(data, offset)
            obj.objects.append(child)
        else:
            offset += 1  # unknown tag — skip defensively
    return obj, offset


def parse_object_list(data: bytes, offset: int) -> tuple[list[PObject], int]:
    """Parse a sequence of sibling PObjects (consecutive 0xA1 blocks)."""
    objects: list[PObject] = []
    while offset < len(data) and data[offset] == START_OF_OBJECT:
        obj, offset = parse_object(data, offset)
        objects.append(obj)
    return objects, offset


def _find_container(objects: list[PObject], class_id: int) -> PObject | None:
    for obj in objects:
        if obj.class_id == class_id:
            return obj
        found = _find_container(obj.objects, class_id)
        if found is not None:
            return found
    return None


def extract_type_info_objects(response: bytes) -> list[PObject]:
    """Return the per-type objects from an EXPLORE(type-info) response.

    Skips the leading ReturnValue VLQ and any preamble, parses the object stream,
    and returns the children of the type-info container object (or ``[]``).
    """
    _return_value, consumed = decode_uint32_vlq(response, 0)
    offset = consumed
    while offset < len(response) and response[offset] != START_OF_OBJECT:
        offset += 1
    if offset >= len(response):
        return []
    objects, _ = parse_object_list(response, offset)
    container = _find_container(objects, CLASS_OMS_TYPE_INFO_CONTAINER)
    return container.objects if container is not None else []


# ---------------------------------------------------------------------------
# 7. Tree model & builder
# ---------------------------------------------------------------------------


class NodeType(IntEnum):
    UNDEFINED = 0
    ROOT = 1
    VAR = 2
    ARRAY = 3
    STRUCT_ARRAY = 4


@dataclass
class Node:
    node_type: NodeType = NodeType.UNDEFINED
    name: str = ""
    access_id: int = 0
    softdatatype: int = 0
    relation_id: int = 0
    vte: VartypeListElement | None = None
    array_adr_offset_opt: int = 0
    array_adr_offset_nonopt: int = 0
    children: list["Node"] = field(default_factory=list)


@dataclass
class VarInfo:
    """A flattened, readable tag."""

    name: str = ""
    access_sequence: str = ""
    softdatatype: int = 0
    opt_address: int = 0
    opt_bitoffset: int = 0
    nonopt_address: int = 0
    nonopt_bitoffset: int = 0


def _tcom_size(obj: PObject | None) -> int:
    if obj is None:
        return 0
    raw = obj.attributes.get(TI_TCOM_SIZE)
    if not raw or len(raw) < 4:
        # Stored big-endian u32; pad/parse defensively.
        return int.from_bytes(raw, "big") if raw else 0
    return struct.unpack_from(">I", raw, 0)[0]


def _find_type_object(objects: list[PObject], relation_id: int) -> PObject | None:
    for obj in objects:
        if obj.relation_id == relation_id:
            return obj
    return None


def build_tree(root_nodes: list[Node], type_objects: list[PObject]) -> None:
    """Expand each ROOT node against the matching type object (in place)."""
    for node in root_nodes:
        if node.node_type != NodeType.ROOT:
            continue
        obj = _find_type_object(type_objects, node.relation_id)
        if obj is not None:
            _add_subnodes(node, obj, type_objects)


def _add_subnodes(node: Node, obj: PObject, objects: list[PObject]) -> None:
    for i, vte in enumerate(obj.vartype_list):
        name = obj.varname_list[i] if i < len(obj.varname_list) else ""
        subnode = Node(
            node_type=NodeType.UNDEFINED,
            name=name,
            access_id=vte.lid,
            softdatatype=vte.softdatatype,
            vte=vte,
        )
        node.children.append(subnode)
        oi = vte.offset_info

        if oi.is_1dim:
            for elem in range(oi.array_element_count):
                label = f"[{elem + oi.array_lower_bound}]"
                if oi.has_relation:
                    struct_type = _find_type_object(objects, oi.relation_id)
                    stride = _tcom_size(struct_type)
                    arr_node = Node(
                        node_type=NodeType.STRUCT_ARRAY,
                        name=label,
                        access_id=elem,
                        softdatatype=vte.softdatatype,
                        relation_id=oi.relation_id,
                        vte=vte,
                        array_adr_offset_opt=elem * stride,
                        array_adr_offset_nonopt=elem * stride,
                    )
                    subnode.children.append(arr_node)
                    if struct_type is not None:
                        _add_subnodes(arr_node, struct_type, objects)
                else:
                    stride = datatype_size(vte.softdatatype, string_len=oi.unspecified1)
                    arr_node = Node(
                        node_type=NodeType.ARRAY,
                        name=label,
                        access_id=elem,
                        softdatatype=vte.softdatatype,
                        vte=vte,
                        array_adr_offset_opt=elem * stride,
                        array_adr_offset_nonopt=elem * stride,
                    )
                    subnode.children.append(arr_node)

        elif oi.is_mdim:
            _add_mdim_subnodes(subnode, vte, oi, objects)

        elif oi.has_relation:
            struct_type = _find_type_object(objects, oi.relation_id)
            if struct_type is not None:
                _add_subnodes(subnode, struct_type, objects)
        # else: scalar leaf, no children.


def _add_mdim_subnodes(subnode: Node, vte: VartypeListElement, oi: OffsetInfo, objects: list[PObject]) -> None:
    counts = oi.mdim_element_count
    lowers = oi.mdim_lower_bounds
    actdimensions = sum(1 for c in counts if c > 0)
    struct_type = _find_type_object(objects, oi.relation_id) if oi.has_relation else None
    stride = _tcom_size(struct_type) if oi.has_relation else datatype_size(vte.softdatatype, string_len=oi.unspecified1)

    xx = [0] * 6
    arr_id = 0
    n = 1
    while n <= oi.array_element_count:
        indices = (str(xx[j] + lowers[j]) for j in range(actdimensions - 1, -1, -1))
        label = "[" + ",".join(indices) + "]"
        elem_off = (n - 1) * stride

        if oi.has_relation:
            arr_node = Node(
                node_type=NodeType.STRUCT_ARRAY,
                name=label,
                access_id=arr_id,
                softdatatype=vte.softdatatype,
                relation_id=oi.relation_id,
                vte=vte,
                array_adr_offset_opt=elem_off,
                array_adr_offset_nonopt=elem_off,
            )
            subnode.children.append(arr_node)
            if struct_type is not None:
                _add_subnodes(arr_node, struct_type, objects)
        else:
            arr_node = Node(
                node_type=NodeType.ARRAY,
                name=label,
                access_id=arr_id,
                softdatatype=vte.softdatatype,
                vte=vte,
                array_adr_offset_opt=elem_off,
                array_adr_offset_nonopt=elem_off,
            )
            subnode.children.append(arr_node)

        # Odometer step (axis 0 fastest).
        xx[0] += 1
        if vte.softdatatype == Softdatatype.BBOOL and xx[0] >= counts[0] and counts[0] % 8 != 0:
            arr_id += 8 - (xx[0] % 8)  # rows of bits pad up to a byte
        for dim in range(5):
            if xx[dim] >= counts[dim]:
                xx[dim] = 0
                xx[dim + 1] += 1
        arr_id += 1
        n += 1


# ---------------------------------------------------------------------------
# 8. Flatten
# ---------------------------------------------------------------------------


def build_flat_list(root_nodes: list[Node]) -> list[VarInfo]:
    """Walk each populated ROOT and produce the flat list of readable tags."""
    result: list[VarInfo] = []
    for root in root_nodes:
        if not root.children:
            continue
        _walk(root, "", "", 0, 0, result)
    return result


def _walk(node: Node, names: str, access_ids: str, opt_off: int, nonopt_off: int, result: list[VarInfo]) -> None:
    # Accumulate this node's name and access-id contribution.
    if node.node_type == NodeType.ROOT:
        names = names + node.name
        access_ids = access_ids + f"{node.access_id:X}"
    elif node.node_type == NodeType.ARRAY:
        names = names + node.name  # "[..]" index label, no dot
        access_ids = access_ids + "." + f"{node.access_id:X}"
    elif node.node_type == NodeType.STRUCT_ARRAY:
        names = names + node.name
        access_ids = access_ids + "." + f"{node.access_id:X}" + ".1"
    else:  # UNDEFINED / VAR member
        names = names + "." + node.name
        access_ids = access_ids + "." + f"{node.access_id:X}"

    if node.children:
        # Descend into a branch — advance the running byte offsets.
        if node.node_type == NodeType.ARRAY:
            assert node.vte is not None
            opt_off = node.vte.offset_info.opt_addr
            nonopt_off = node.vte.offset_info.nonopt_addr
        elif node.node_type == NodeType.STRUCT_ARRAY:
            opt_off += node.array_adr_offset_opt
            nonopt_off += node.array_adr_offset_nonopt
        elif node.vte is not None:
            opt_off += node.vte.offset_info.opt_addr
            nonopt_off += node.vte.offset_info.nonopt_addr

        for child in node.children:
            child_opt, child_nonopt = opt_off, nonopt_off
            if child.node_type == NodeType.ARRAY:
                child_opt += child.array_adr_offset_opt
                child_nonopt += child.array_adr_offset_nonopt
            _walk(child, names, access_ids, child_opt, child_nonopt, result)
        return

    # Leaf node — emit if the datatype is a readable leaf.
    if not is_softdatatype_supported(node.softdatatype):
        return

    info = VarInfo(name=names, access_sequence=access_ids, softdatatype=node.softdatatype)
    if node.node_type == NodeType.ARRAY:
        # Basic-array element: offset already includes the element stride.
        info.opt_address = opt_off
        info.nonopt_address = nonopt_off
    else:
        assert node.vte is not None
        info.opt_address = opt_off + node.vte.offset_info.opt_addr
        info.nonopt_address = nonopt_off + node.vte.offset_info.nonopt_addr

    vte = node.vte
    if node.softdatatype == Softdatatype.BOOL and vte is not None:
        info.opt_bitoffset = vte.attribute_bitoffset
        info.nonopt_bitoffset = vte.nonopt_bitoffset if vte.classic else vte.attribute_bitoffset
    elif node.softdatatype == Softdatatype.BBOOL and vte is not None:
        info.opt_bitoffset = vte.opt_bitoffset

    result.append(info)
