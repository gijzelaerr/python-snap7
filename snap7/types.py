"""
Python equivalent for snap7 specific types.
"""
import ctypes
from enum import Enum

from .common import ADict

S7Object = ctypes.c_void_p
buffer_size = 65536
buffer_type = ctypes.c_ubyte * buffer_size
time_t = ctypes.c_uint64  # TODO: check if this is valid for all platforms
word = ctypes.c_uint16
longword = ctypes.c_uint32

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

param_types = ADict({
    LocalPort: ctypes.c_uint16,
    RemotePort: ctypes.c_uint16,
    PingTimeout: ctypes.c_int32,
    SendTimeout: ctypes.c_int32,
    RecvTimeout: ctypes.c_int32,
    WorkInterval: ctypes.c_int32,
    SrcRef: ctypes.c_uint16,
    DstRef: ctypes.c_uint16,
    SrcTSap: ctypes.c_uint16,
    PDURequest: ctypes.c_int32,
    MaxClients: ctypes.c_int32,
    BSendTimeout: ctypes.c_int32,
    BRecvTimeout: ctypes.c_int32,
    RecoveryTime: ctypes.c_uint32,
    KeepAliveTime: ctypes.c_uint32,
})

# mask types
mkEvent = 0
mkLog = 1


# Area ID
class Areas(Enum):
    PE = 0x81
    PA = 0x82
    MK = 0x83
    DB = 0x84
    CT = 0x1C
    TM = 0x1D


# Leave it for now
S7AreaPE = 0x81
S7AreaPA = 0x82
S7AreaMK = 0x83
S7AreaDB = 0x84
S7AreaCT = 0x1C
S7AreaTM = 0x1D


areas = ADict({
    'PE': 0x81,
    'PA': 0x82,
    'MK': 0x83,
    'DB': 0x84,
    'CT': 0x1C,
    'TM': 0x1D,
})


# Word Length
class WordLen(Enum):
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


# Leave it for now
S7WLBit = 0x01
S7WLByte = 0x02
S7WLChar = 0x03
S7WLWord = 0x04
S7WLInt = 0x05
S7WLDWord = 0x06
S7WLDInt = 0x07
S7WLReal = 0x08
S7WLCounter = 0x1C
S7WLTimer = 0x1D

# Server Area ID  (use with Register/unregister - Lock/unlock Area)
# NOTE: these are not the same for the client!!
srvAreaPE = 0
srvAreaPA = 1
srvAreaMK = 2
srvAreaCT = 3
srvAreaTM = 4
srvAreaDB = 5

server_areas = ADict({
    'PE': 0,
    'PA': 1,
    'MK': 2,
    'CT': 3,
    'TM': 4,
    'DB': 5,
})

wordlen_to_ctypes = ADict({
    S7WLBit: ctypes.c_int16,
    S7WLByte: ctypes.c_int8,
    S7WLWord: ctypes.c_int16,
    S7WLDWord: ctypes.c_int32,
    S7WLReal: ctypes.c_int32,
    S7WLCounter: ctypes.c_int16,
    S7WLTimer: ctypes.c_int16,
})

block_types = ADict({
    'OB': ctypes.c_int(0x38),
    'DB': ctypes.c_int(0x41),
    'SDB': ctypes.c_int(0x42),
    'FC': ctypes.c_int(0x43),
    'SFC': ctypes.c_int(0x44),
    'FB': ctypes.c_int(0x45),
    'SFB': ctypes.c_int(0x46),
})

server_statuses = {
    0: 'SrvStopped',
    1: 'SrvRunning',
    2: 'SrvError',
}

cpu_statuses = {
    0: 'S7CpuStatusUnknown',
    4: 'S7CpuStatusStop',
    8: 'S7CpuStatusRun',
}


class SrvEvent(ctypes.Structure):
    _fields_ = [
        ('EvtTime', time_t),
        ('EvtSender', ctypes.c_int),
        ('EvtCode', longword),
        ('EvtRetCode', word),
        ('EvtParam1', word),
        ('EvtParam2', word),
        ('EvtParam3', word),
        ('EvtParam4', word),
    ]

    def __str__(self) -> str:
        return f"<event time: {self.EvtTime} sender: {self.EvtSender} code: {self.EvtCode} " \
               f"retcode: {self.EvtRetCode} param1: {self.EvtParam1} param2:{self.EvtParam2} " \
               f"param3: {self.EvtParam3} param4: {self.EvtParam4}>"


class BlocksList(ctypes.Structure):
    _fields_ = [
        ('OBCount', ctypes.c_int32),
        ('FBCount', ctypes.c_int32),
        ('FCCount', ctypes.c_int32),
        ('SFBCount', ctypes.c_int32),
        ('SFCCount', ctypes.c_int32),
        ('DBCount', ctypes.c_int32),
        ('SDBCount', ctypes.c_int32),
    ]

    def __str__(self) -> str:
        return f"<block list count OB: {self.OBCount} FB: {self.FBCount} FC: {self.FCCount} SFB: {self.SFBCount} " \
               f"SFC: {hex(self.SFCCount)} DB: {self.DBCount} SDB: {self.SDBCount}>"


class TS7BlockInfo(ctypes.Structure):
    _fields_ = [
        ('BlkType', ctypes.c_int32),
        ('BlkNumber', ctypes.c_int32),
        ('BlkLang', ctypes.c_int32),
        ('BlkFlags', ctypes.c_int32),
        ('MC7Size', ctypes.c_int32),
        ('LoadSize', ctypes.c_int32),
        ('LocalData', ctypes.c_int32),
        ('SBBLength', ctypes.c_int32),
        ('CheckSum', ctypes.c_int32),
        ('Version', ctypes.c_int32),
        ('CodeDate', ctypes.c_char * 11),
        ('IntfDate', ctypes.c_char * 11),
        ('Author', ctypes.c_char * 9),
        ('Family', ctypes.c_char * 9),
        ('Header', ctypes.c_char * 9),
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


class S7DataItem(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ('Area', ctypes.c_int32),
        ('WordLen', ctypes.c_int32),
        ('Result', ctypes.c_int32),
        ('DBNumber', ctypes.c_int32),
        ('Start', ctypes.c_int32),
        ('Amount', ctypes.c_int32),
        ('pData', ctypes.POINTER(ctypes.c_uint8))
    ]

    def __str__(self) -> str:
        return f"<S7DataItem Area: {self.Area} WordLen: {self.WordLen} Result: {self.Result} "\
               f"DBNumber: {self.DBNumber} Start: {self.Start} Amount: {self.Amount} pData: {self.pData}>"


class S7CpuInfo(ctypes.Structure):
    _fields_ = [
        ('ModuleTypeName', ctypes.c_char * 33),
        ('SerialNumber', ctypes.c_char * 25),
        ('ASName', ctypes.c_char * 25),
        ('Copyright', ctypes.c_char * 27),
        ('ModuleName', ctypes.c_char * 25)
    ]

    def __str__(self):
        return f"<S7CpuInfo ModuleTypeName: {self.ModuleTypeName} SerialNumber: {self.SerialNumber} "\
               f"ASName: {self.ASName} Copyright: {self.Copyright} ModuleName: {self.ModuleName}>"


class S7SZLHeader(ctypes.Structure):
    """
        LengthDR: Length of a data record of the partial list in bytes
        NDR: Number of data records contained in the partial list
    """
    _fields_ = [
        ('LengthDR', ctypes.c_uint16),
        ('NDR', ctypes.c_uint16)
    ]

    def __str__(self) -> str:
        return f"<S7SZLHeader LengthDR: {self.LengthDR}, NDR: {self.NDR}>"


class S7SZL(ctypes.Structure):
    """See §33.1 of System Software for S7-300/400 System and Standard Functions"""
    _fields_ = [
        ('Header', S7SZLHeader),
        ('Data', ctypes.c_byte * (0x4000 - 4))
    ]

    def __str__(self) -> str:
        return f"<S7SZL Header: {self.S7SZHeader}, Data: {self.Data}>"


class S7SZLList(ctypes.Structure):
    _fields_ = [
        ('Header', S7SZLHeader),
        ('List', word * (0x4000 - 2))
    ]


class S7OrderCode(ctypes.Structure):
    _fields_ = [
        ('OrderCode', ctypes.c_char * 21),
        ('V1', ctypes.c_byte),
        ('V2', ctypes.c_byte),
        ('V3', ctypes.c_byte)
    ]


class S7CpInfo(ctypes.Structure):
    _fields_ = [
        ('MaxPduLength', ctypes.c_uint16),
        ('MaxConnections', ctypes.c_uint16),
        ('MaxMpiRate', ctypes.c_uint16),
        ('MaxBusRate', ctypes.c_uint16)
    ]

    def __str__(self) -> str:
        return f"<S7CpInfo MaxPduLength: {self.MaxPduLength} MaxConnections: {self.MaxConnections} "\
               f"MaxMpiRate: {self.MaxMpiRate} MaxBusRate: {self.MaxBusRate}>"


class S7Protection(ctypes.Structure):
    """See §33.19 of System Software for S7-300/400 System and Standard Functions"""
    _fields_ = [
        ('sch_schal', word),
        ('sch_par', word),
        ('sch_rel', word),
        ('bart_sch', word),
        ('anl_sch', word),
    ]
