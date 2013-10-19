from ctypes import c_uint, c_ubyte, c_uint64, c_uint16, c_uint32, c_int,\
    c_int8, c_int16, c_int32

S7Object = c_uint
buffer_size = 65536
buffer_type = c_ubyte * buffer_size
time_t = c_uint64  # TODO: check if this is valid for all platforms
word = c_uint16
longword = c_uint32

# // PARAMS LIST
LocalPort       = 1
RemotePort      = 2
PingTimeout     = 3
SendTimeout     = 4
RecvTimeout     = 5
WorkInterval    = 6
SrcRef          = 7
DstRef          = 8
SrcTSap         = 9
PDURequest      = 10
MaxClients      = 11
BSendTimeout    = 12
BRecvTimeout    = 13
RecoveryTime    = 14
KeepAliveTime   = 15

# mask types
mkEvent = 0
mkLog = 1


# Area ID
S7AreaPE   = 0x81
S7AreaPA   = 0x82
S7AreaMK   = 0x83
S7AreaDB   = 0x84
S7AreaCT   = 0x1C
S7AreaTM   = 0x1D

# Word Length
S7WLBit     = 0x01
S7WLByte    = 0x02
S7WLWord    = 0x04
S7WLDWord   = 0x06
S7WLReal    = 0x08
S7WLCounter = 0x1C
S7WLTimer   = 0x1D

wordlen_to_ctypes = {
    S7WLByte: c_int8,
    S7WLWord: c_int16,
    S7WLDWord: c_int32,
    S7WLReal: c_int32,
    S7WLCounter: c_int16,
    S7WLTimer: c_int16,
}

block_types = {
    'OB': c_int(0x38),
    'DB': c_int(0x41),
    'SDB': c_int(0x42),
    'FC': c_int(0x43),
    'SFC': c_int(0x44),
    'FB': c_int(0x45),
    'SFB': c_int(0x46),
}