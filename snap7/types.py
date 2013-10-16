from ctypes import c_uint, c_ubyte, c_uint64, c_uint16, c_uint32

S7Object = c_uint
buffer_size = 65536
buffer_type = c_ubyte * buffer_size
time_t = c_uint64  # TODO: check if this is valid for all platforms
word = c_uint16
longword = c_uint32