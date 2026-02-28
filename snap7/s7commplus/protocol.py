"""
S7CommPlus protocol constants and types.

Defines the protocol framing, opcodes, function codes, data types,
element IDs, and other constants needed for S7CommPlus communication.

Reference: thomas-v2/S7CommPlusDriver (C#, LGPL-3.0)
Reference: Wireshark S7CommPlus dissector
"""

from enum import IntEnum


# Protocol identification byte (vs 0x32 for legacy S7comm)
PROTOCOL_ID = 0x72


class ProtocolVersion(IntEnum):
    """S7CommPlus protocol versions.

    V1: Early S7-1200 FW V4.0 -- trivial anti-replay (challenge + 0x80)
    V2: Adds integrity checking and proprietary session authentication
    V3: Adds ECC-based key exchange (broken via CVE-2022-38465)
    TLS: TIA Portal V17+ -- standard TLS 1.3 with per-device certificates

    For new implementations, only TLS (V3 + InitSsl) should be targeted.
    """

    V1 = 0x01
    V2 = 0x02
    V3 = 0x03
    SYSTEM_EVENT = 0xFE


class Opcode(IntEnum):
    """S7CommPlus opcodes (first byte after header)."""

    REQUEST = 0x31
    RESPONSE = 0x32
    NOTIFICATION = 0x33
    RESPONSE2 = 0x02  # Seen in some older firmware


class FunctionCode(IntEnum):
    """S7CommPlus function codes.

    These identify the type of operation in a request/response pair.
    """

    ERROR = 0x04B1
    EXPLORE = 0x04BB
    CREATE_OBJECT = 0x04CA
    DELETE_OBJECT = 0x04D4
    SET_VARIABLE = 0x04F2
    GET_VARIABLE = 0x04FC  # Only in old S7-1200 firmware
    ADD_LINK = 0x0506
    REMOVE_LINK = 0x051A
    GET_LINK = 0x0524
    SET_MULTI_VARIABLES = 0x0542
    GET_MULTI_VARIABLES = 0x054C
    BEGIN_SEQUENCE = 0x0556
    END_SEQUENCE = 0x0560
    INVOKE = 0x056B
    SET_VAR_SUBSTREAMED = 0x057C
    GET_VAR_SUBSTREAMED = 0x0586
    GET_VARIABLES_ADDRESS = 0x0590
    ABORT = 0x059A
    ERROR2 = 0x05A9
    INIT_SSL = 0x05B3


class ElementID(IntEnum):
    """Tag IDs used in the object serialization format.

    S7CommPlus uses a tagged object model where data is structured as
    nested objects with attributes, similar to TLV encoding.
    """

    START_OF_OBJECT = 0xA1
    TERMINATING_OBJECT = 0xA2
    ATTRIBUTE = 0xA3
    RELATION = 0xA4
    START_OF_TAG_DESCRIPTION = 0xA7
    TERMINATING_TAG_DESCRIPTION = 0xA8
    VARTYPE_LIST = 0xAB
    VARNAME_LIST = 0xAC


class DataType(IntEnum):
    """S7CommPlus wire data types.

    These identify how values are encoded on the wire in the S7CommPlus
    protocol. Note: these differ from the Softdatatype IDs used for
    PLC variable type metadata.
    """

    NULL = 0x00
    BOOL = 0x01
    USINT = 0x02
    UINT = 0x03
    UDINT = 0x04
    ULINT = 0x05
    SINT = 0x06
    INT = 0x07
    DINT = 0x08
    LINT = 0x09
    BYTE = 0x0A
    WORD = 0x0B
    DWORD = 0x0C
    LWORD = 0x0D
    REAL = 0x0E
    LREAL = 0x0F
    TIMESTAMP = 0x10
    TIMESPAN = 0x11
    RID = 0x12
    AID = 0x13
    BLOB = 0x14
    WSTRING = 0x15
    VARIANT = 0x16
    STRUCT = 0x17
    S7STRING = 0x19


class SoftDataType(IntEnum):
    """PLC soft data types (used in variable metadata / tag descriptions).

    These correspond to the data types as they appear in the PLC's symbol
    table and are used for symbolic access to optimized data blocks.
    """

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
    TIME_OF_DAY = 10
    TIME = 11
    S5TIME = 12
    DATE_AND_TIME = 14
    ARRAY = 16
    STRUCT = 17
    STRING = 19
    POINTER = 20
    ANY = 22
    BLOCK_FB = 23
    BLOCK_FC = 24
    BLOCK_DB = 25
    BLOCK_SDB = 26
    COUNTER = 28
    TIMER = 29
    IEC_COUNTER = 30
    IEC_TIMER = 31
    BLOCK_SFB = 32
    BLOCK_SFC = 33
    BLOCK_OB = 36
    BLOCK_UDT = 37
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
