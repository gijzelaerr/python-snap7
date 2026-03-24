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

    V1: Early S7-1200 FW V4.0 -- simple session handshake
    V2: Adds integrity checking and session authentication
    V3: Adds public-key-based key exchange
    TLS: TIA Portal V17+ -- standard TLS 1.3 with per-device certificates

    For new implementations, TLS (V3 + InitSsl) is the recommended target.
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


class ObjectId(IntEnum):
    """Well-known object IDs used in session establishment.

    Reference: thomas-v2/S7CommPlusDriver/Core/Ids.cs
    """

    NONE = 0
    GET_NEW_RID_ON_SERVER = 211
    CLASS_SUBSCRIPTIONS = 255
    CLASS_SERVER_SESSION_CONTAINER = 284
    OBJECT_SERVER_SESSION_CONTAINER = 285
    CLASS_SERVER_SESSION = 287
    OBJECT_NULL_SERVER_SESSION = 288
    SERVER_SESSION_CLIENT_RID = 300
    SERVER_SESSION_VERSION = 306


# Default TSAP for S7CommPlus connections
# The remote TSAP is the ASCII string "SIMATIC-ROOT-HMI" (16 bytes)
S7COMMPLUS_LOCAL_TSAP = 0x0600
S7COMMPLUS_REMOTE_TSAP = b"SIMATIC-ROOT-HMI"


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


class Ids(IntEnum):
    """Well-known IDs for S7CommPlus protocol structures.

    Reference: thomas-v2/S7CommPlusDriver/Core/Ids.cs
    """

    # Data block access sub-areas
    DB_VALUE_ACTUAL = 2550
    CONTROLLER_AREA_VALUE_ACTUAL = 2551

    # ObjectQualifier structure IDs
    OBJECT_QUALIFIER = 1256
    PARENT_RID = 1257
    COMPOSITION_AID = 1258
    KEY_QUALIFIER = 1259

    # Native object RIDs for memory areas
    NATIVE_THE_I_AREA_RID = 80
    NATIVE_THE_Q_AREA_RID = 81
    NATIVE_THE_M_AREA_RID = 82
    NATIVE_THE_S7_COUNTERS_RID = 83
    NATIVE_THE_S7_TIMERS_RID = 84

    # DB AccessArea base (add DB number to get area ID)
    DB_ACCESS_AREA_BASE = 0x8A0E0000


# Function codes that use the READ IntegrityId counter (V2+)
READ_FUNCTION_CODES: frozenset[int] = frozenset(
    {
        FunctionCode.GET_MULTI_VARIABLES,
        FunctionCode.EXPLORE,
        FunctionCode.GET_VAR_SUBSTREAMED,
        FunctionCode.GET_LINK,
        FunctionCode.GET_VARIABLE,
        FunctionCode.GET_VARIABLES_ADDRESS,
    }
)


class LegitimationId(IntEnum):
    """Legitimation IDs used in password authentication (V2+).

    Reference: thomas-v2/S7CommPlusDriver
    """

    SERVER_SESSION_REQUEST = 303
    SERVER_SESSION_RESPONSE = 304
    LEGITIMATE = 1846



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
