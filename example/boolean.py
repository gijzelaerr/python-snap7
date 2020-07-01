"""
So how to change a bool value? 

1) Read out the _bytearray your boolean values are in. 
2) In this byte_array you need to find the byte (byteindex) 
3) Find the bit in this byte (bitindex) so you can 
4) set the correct value with utility function set_bool which does all the hard work.
set_bool(_bytearray = data which you read out before.., byte_index, bool_index, value),
5) write back the changed bytearray back to the PLC.

A round trip wil take 5ms.

The example code

https://github.com/gijzelaerr/python-snap7/blob/master/example/

the minimun amount of data being read or written to a plc is 1 byte.
"""
import snap7
from snap7.snap7types import areas

plc = snap7.client.Client()
plc.connect('192.168.200.24', 0, 3)
value = 0  # Bit Value

# In this example boolean in DB 31 at byte 120 and bit 5 is changed. = 120.5 

reading = plc.db_read(31, 120, 1)  # read 1 byte from db 31 staring from byte 120
snap7.util.set_bool(reading, 0, 5, value)  # set a value of fifth bit with value
plc.db_write(reading, 31, 120, 1)  # write back the bytearray and now the boolean value is changed
#  in the PLC.

# NOTE you could also use the read_area and write_area functions.
# then you can specify an area to read from:
# https://github.com/gijzelaerr/python-snap7/blob/master/snap7/snap7types.py


# play with these functions.
dbnumber = 0    # replace 0 with your wanted DB number
start = 0       # replace 0 with your wanted start number
size = 0        # replace 0 with the size of the value

plc.read_area(areas['MK'], dbnumber, start, size)
plc.write_area(areas['MK'], dbnumber, start, size)
# read the client source code!
# and official snap7 documentation
