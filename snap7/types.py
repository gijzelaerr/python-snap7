from ctypes import c_uint, c_ubyte, c_uint64, c_uint16, c_uint32

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
