"""
Example ussage of the read_multi_vars function

This was tested against a S7-319 CPU
"""

import ctypes

from snap7 import Client
from error import check_error
from snap7.type import S7DataItem, Area, WordLen
from snap7.util import get_real, get_int

client = Client()
client.connect("10.100.5.2", 0, 2)

data_items = (S7DataItem * 3)()

data_items[0].Area = ctypes.c_int32(Area.DB.value)
data_items[0].WordLen = ctypes.c_int32(WordLen.Byte.value)
data_items[0].Result = ctypes.c_int32(0)
data_items[0].DBNumber = ctypes.c_int32(200)
data_items[0].Start = ctypes.c_int32(16)
data_items[0].Amount = ctypes.c_int32(4)  # reading a REAL, 4 bytes

data_items[1].Area = ctypes.c_int32(Area.DB.value)
data_items[1].WordLen = ctypes.c_int32(WordLen.Byte.value)
data_items[1].Result = ctypes.c_int32(0)
data_items[1].DBNumber = ctypes.c_int32(200)
data_items[1].Start = ctypes.c_int32(12)
data_items[1].Amount = ctypes.c_int32(4)  # reading a REAL, 4 bytes

data_items[2].Area = ctypes.c_int32(Area.DB.value)
data_items[2].WordLen = ctypes.c_int32(WordLen.Byte.value)
data_items[2].Result = ctypes.c_int32(0)
data_items[2].DBNumber = ctypes.c_int32(200)
data_items[2].Start = ctypes.c_int32(2)
data_items[2].Amount = ctypes.c_int32(2)  # reading an INT, 2 bytes

# create buffers to receive the data
# use the Amount attribute on each item to size the buffer
for di in data_items:
    # create the buffer
    buffer = ctypes.create_string_buffer(di.Amount)

    # cast the pointer to the buffer to the required type
    pBuffer = ctypes.cast(ctypes.pointer(buffer), ctypes.POINTER(ctypes.c_uint8))
    di.pData = pBuffer

result, data_items = client.read_multi_vars(data_items)

for di in data_items:
    check_error(di.Result)

result_values = []
# function to cast bytes to match data_types[] above
byte_to_value = [get_real, get_real, get_int]

# unpack and test the result of each read
for i in range(0, len(data_items)):
    btv = byte_to_value[i]
    di = data_items[i]
    value = btv(di.pData, 0)
    result_values.append(value)
print(result_values)

client.disconnect()
client.destroy()
