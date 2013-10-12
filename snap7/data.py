from ctypes import c_int


block_types = {
    'OB': c_int(0x38),
    'DB': c_int(0x41),
    'SDB': c_int(0x42),
    'FC': c_int(0x43),
    'SFC': c_int(0x44),
    'FB': c_int(0x45),
    'SFB': c_int(0x46),
}

