from ctypes import (
    c_uint8,
    c_uint16,
    Structure,
    c_byte,
)

word = c_uint16
byte = c_byte
u_char = c_uint8


class TS7ReqHeader(Structure):
    _fields_ = [
        ("P", byte),
        ("PDUType", byte),
        ("AB_EX", word),
        ("Sequence", word),
        ("ParLen", word),
        ("DataLen", word),
    ]


PS7ReqHeader = TS7ReqHeader
