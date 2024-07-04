"""
Python equivalent for snap7 specific types.
"""

from _ctypes import Array
from ctypes import (
    c_int16,
    c_int8,
    c_int32,
    c_void_p,
    c_ubyte,
    c_uint64,
    c_uint16,
    c_uint32,
    Structure,
    POINTER,
    c_char,
    c_byte,
    c_int,
    c_uint8,
)
from datetime import datetime, date, timedelta
from enum import IntEnum
from typing import Dict, Union, Literal

CDataArrayType = Union[
    Array[c_byte], Array[c_int], Array[c_int16], Array[c_int32], Array[c_uint8], Array[c_uint16], Array[c_uint32]
]
CDataType = Union[type[c_int8], type[c_int16], type[c_int32], type[c_uint8], type[c_uint16], type[c_uint32]]
ValueType = Union[int, float, str, datetime, bytearray, bytes, date, timedelta]

Context = Literal["client", "server", "partner"]

S7Object = c_void_p
buffer_size = 65536
# noinspection PyTypeChecker
buffer_type = c_ubyte * buffer_size
time_t = c_uint64
word = c_uint16
longword = c_uint32

# mask types
mkEvent = 0
mkLog = 1


class Parameter(IntEnum):
    # // PARAMS LIST
    LocalPort = 1
    RemotePort = 2
    PingTimeout = 3
    SendTimeout = 4
    RecvTimeout = 5
    WorkInterval = 6
    SrcRef = 7
    DstRef = 8
    SrcTSap = 9
    PDURequest = 10
    MaxClients = 11
    BSendTimeout = 12
    BRecvTimeout = 13
    RecoveryTime = 14
    KeepAliveTime = 15

    @property
    def ctype(self) -> CDataType:
        map_: Dict[int, CDataType] = {
            self.LocalPort: c_uint16,
            self.RemotePort: c_uint16,
            self.PingTimeout: c_int32,
            self.SendTimeout: c_int32,
            self.RecvTimeout: c_int32,
            self.WorkInterval: c_int32,
            self.SrcRef: c_uint16,
            self.DstRef: c_uint16,
            self.SrcTSap: c_uint16,
            self.PDURequest: c_int32,
            self.MaxClients: c_int32,
            self.BSendTimeout: c_int32,
            self.BRecvTimeout: c_int32,
            self.RecoveryTime: c_uint32,
            self.KeepAliveTime: c_uint32,
        }
        return map_[self]


# Area ID
# Word Length
class WordLen(IntEnum):
    Bit = 0x01
    Byte = 0x02
    Char = 0x03
    Word = 0x04
    Int = 0x05
    DWord = 0x06
    DInt = 0x07
    Real = 0x08
    Counter = 0x1C
    Timer = 0x1D

    @property
    def ctype(self) -> CDataType:
        map_: Dict[WordLen, CDataType] = {
            WordLen.Bit: c_int16,
            WordLen.Byte: c_int8,
            WordLen.Word: c_int16,
            WordLen.DWord: c_int32,
            WordLen.Real: c_int32,
            WordLen.Counter: c_int16,
            WordLen.Timer: c_int16,
        }
        return map_[self]


class Area(IntEnum):
    PE = 0x81
    PA = 0x82
    MK = 0x83
    DB = 0x84
    CT = 0x1C
    TM = 0x1D

    def wordlen(self) -> WordLen:
        if self == Area.TM:
            return WordLen.Timer
        elif self == Area.CT:
            return WordLen.Counter
        return WordLen.Byte


# backwards compatible alias
Areas = Area


class SrvArea(IntEnum):
    """
    NOTE: these values are DIFFERENT from the normal area IDs.
    """

    PE = 0
    PA = 1
    MK = 2
    CT = 3
    TM = 4
    DB = 5


class Block(IntEnum):
    OB = 0x38
    DB = 0x41
    SDB = 0x42
    FC = 0x43
    SFC = 0x44
    FB = 0x45
    SFB = 0x46

    @property
    def ctype(self) -> c_int:
        return c_int(self)


server_statuses = {
    0: "SrvStopped",
    1: "SrvRunning",
    2: "SrvError",
}

cpu_statuses = {
    0: "S7CpuStatusUnknown",
    4: "S7CpuStatusStop",
    8: "S7CpuStatusRun",
}


class SrvEvent(Structure):
    _fields_ = [
        ("EvtTime", time_t),
        ("EvtSender", c_int),
        ("EvtCode", longword),
        ("EvtRetCode", word),
        ("EvtParam1", word),
        ("EvtParam2", word),
        ("EvtParam3", word),
        ("EvtParam4", word),
    ]

    def __str__(self) -> str:
        return (
            f"<event time: {self.EvtTime} sender: {self.EvtSender} code: {self.EvtCode} "
            f"return code: {self.EvtRetCode} param1: {self.EvtParam1} param2:{self.EvtParam2} "
            f"param3: {self.EvtParam3} param4: {self.EvtParam4}>"
        )


class BlocksList(Structure):
    _fields_ = [
        ("OBCount", c_int32),
        ("FBCount", c_int32),
        ("FCCount", c_int32),
        ("SFBCount", c_int32),
        ("SFCCount", c_int32),
        ("DBCount", c_int32),
        ("SDBCount", c_int32),
    ]

    def __str__(self) -> str:
        return (
            f"<block list count OB: {self.OBCount} FB: {self.FBCount} FC: {self.FCCount} SFB: {self.SFBCount} "
            f"SFC: {hex(self.SFCCount)} DB: {self.DBCount} SDB: {self.SDBCount}>"
        )


# noinspection PyTypeChecker
class TS7BlockInfo(Structure):
    _fields_ = [
        ("BlkType", c_int32),
        ("BlkNumber", c_int32),
        ("BlkLang", c_int32),
        ("BlkFlags", c_int32),
        ("MC7Size", c_int32),
        ("LoadSize", c_int32),
        ("LocalData", c_int32),
        ("SBBLength", c_int32),
        ("CheckSum", c_int32),
        ("Version", c_int32),
        ("CodeDate", c_char * 11),
        ("IntfDate", c_char * 11),
        ("Author", c_char * 9),
        ("Family", c_char * 9),
        ("Header", c_char * 9),
    ]

    def __str__(self) -> str:
        return f"""\
    Block type: {self.BlkType}
    Block number: {self.BlkNumber}
    Block language: {self.BlkLang}
    Block flags: {self.BlkFlags}
    MC7Size: {self.MC7Size}
    Load memory size: {self.LoadSize}
    Local data: {self.LocalData}
    SBB Length: {self.SBBLength}
    Checksum: {self.CheckSum}
    Version: {self.Version}
    Code date: {self.CodeDate}
    Interface date: {self.IntfDate}
    Author: {self.Author}
    Family: {self.Family}
    Header: {self.Header}"""


class S7DataItem(Structure):
    _pack_ = 1
    _fields_ = [
        ("Area", c_int32),
        ("WordLen", c_int32),
        ("Result", c_int32),
        ("DBNumber", c_int32),
        ("Start", c_int32),
        ("Amount", c_int32),
        ("pData", POINTER(c_uint8)),
    ]

    def __str__(self) -> str:
        return (
            f"<S7DataItem Area: {self.Area} WordLen: {self.WordLen} Result: {self.Result} "
            f"DBNumber: {self.DBNumber} Start: {self.Start} Amount: {self.Amount} pData: {self.pData}>"
        )


# noinspection PyTypeChecker
class S7CpuInfo(Structure):
    """
    S7CpuInfo class for handling CPU with :
        - ModuleTypeName => Model of S7-CPU
        - SerialNumber => SN of the S7-CPU
        - ASName => Family Class of the S7-CPU
        - Copyright => Siemens Copyright
        - ModuleName => TIA project name or for other S7-CPU, same as ModuleTypeName

    """

    _fields_ = [
        ("ModuleTypeName", c_char * 33),
        ("SerialNumber", c_char * 25),
        ("ASName", c_char * 25),
        ("Copyright", c_char * 27),
        ("ModuleName", c_char * 25),
    ]

    def __str__(self) -> str:
        return (
            f"<S7CpuInfo ModuleTypeName: {self.ModuleTypeName} SerialNumber: {self.SerialNumber} "
            f"ASName: {self.ASName} Copyright: {self.Copyright} ModuleName: {self.ModuleName}>"
        )


class S7SZLHeader(Structure):
    """
    LengthDR: Length of a data record of the partial list in bytes
    NDR: Number of data records contained in the partial list
    """

    _fields_ = [("LengthDR", c_uint16), ("NDR", c_uint16)]

    def __str__(self) -> str:
        return f"<S7SZLHeader LengthDR: {self.LengthDR}, NDR: {self.NDR}>"


class S7SZL(Structure):
    """See §33.1 of System Software for S7-300/400 System and Standard Functions"""

    _fields_ = [("Header", S7SZLHeader), ("Data", c_byte * (0x4000 - 4))]

    def __str__(self) -> str:
        return f"<S7SZL Header: {self.S7SZHeader}, Data: {self.Data}>"


class S7SZLList(Structure):
    _fields_ = [("Header", S7SZLHeader), ("List", word * (0x4000 - 2))]


class S7OrderCode(Structure):
    _fields_ = [("OrderCode", c_char * 21), ("V1", c_byte), ("V2", c_byte), ("V3", c_byte)]


class S7CpInfo(Structure):
    """
    S7 Cp class for Communication Information :
        - MaxPduLength => Size of the maximum PDU length in bytes
        - MaxConnections => Max connection allowed to S7-CPU or Server
        - MaxMpiRate => MPI rate (MPI use is deprecated)
        - MaxBusRate => Profibus rate

    Every data packet exchanged with a PLC must fit within the PDU size,
    whose is fixed from 240 up to 960 bytes.

    """

    _fields_ = [
        ("MaxPduLength", c_uint16),
        ("MaxConnections", c_uint16),
        ("MaxMpiRate", c_uint16),
        ("MaxBusRate", c_uint16),
    ]

    def __str__(self) -> str:
        return (
            f"<S7CpInfo MaxPduLength: {self.MaxPduLength} MaxConnections: {self.MaxConnections} "
            f"MaxMpiRate: {self.MaxMpiRate} MaxBusRate: {self.MaxBusRate}>"
        )


class S7Protection(Structure):
    """See §33.19 of System Software for S7-300/400 System and Standard Functions"""

    _fields_ = [
        ("sch_schal", word),
        ("sch_par", word),
        ("sch_rel", word),
        ("bart_sch", word),
        ("anl_sch", word),
    ]
