import ctypes
import snap7
from snap7.type import Area, S7DataItem, WordLen
from snap7.util import set_int, set_real, get_int, get_real, get_s5time


client = snap7.client.Client()
client.connect("192.168.100.100", 0, 2)

items = []


def set_data_item(area: Area, word_len: int, db_number: int, start: int, amount: int, data: bytearray) -> S7DataItem:
    item = S7DataItem()
    item.Area = ctypes.c_int32(area)
    item.WordLen = ctypes.c_int32(word_len)
    item.DBNumber = ctypes.c_int32(db_number)
    item.Start = ctypes.c_int32(start)
    item.Amount = ctypes.c_int32(amount)
    array_class = ctypes.c_uint8 * len(data)
    cdata = array_class.from_buffer_copy(data)
    item.pData = ctypes.cast(cdata, ctypes.POINTER(array_class)).contents
    return item


int_values = [10, 20, 30, 40]
ints = bytearray(len(int_values) * 2)
for i, value in enumerate(int_values):
    set_int(ints, i * 2, value)

real = bytearray(4)
set_real(real, 0, 42.5)

counters = bytearray(0x2999.to_bytes(2, "big") + 0x1111.to_bytes(2, "big"))

item1 = set_data_item(area=Area.DB, word_len=WordLen.Word.value, db_number=1, start=0, amount=4, data=ints)
item2 = set_data_item(area=Area.DB, word_len=WordLen.Real.value, db_number=1, start=8, amount=1, data=real)
item3 = set_data_item(area=Area.TM, word_len=WordLen.Timer.value, db_number=0, start=2, amount=2, data=counters)

items.append(item1)
items.append(item2)
items.append(item3)

client.write_multi_vars(items)

db_int = client.db_read(1, 0, 8)
db_real = client.db_read(1, 8, 12)
db_counters = client.ct_read(2, 2)

print(f"int values: {[get_int(db_int, i * 2) for i in range(4)]}")
print(f"real value: {get_real(db_real, 0)}")
print(f"counters: {get_s5time(counters, 0)}, {get_s5time(counters, 2)}")
