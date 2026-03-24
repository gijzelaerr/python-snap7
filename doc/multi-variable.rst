Multi-Variable Read
===================

The ``read_multi_vars`` method reads multiple variables in a single PDU
request, which is significantly faster than individual reads.

.. code-block:: python

   import snap7
   from snap7.type import Area, WordLen, S7DataItem
   from ctypes import c_uint8, cast, POINTER

   client = snap7.Client()
   client.connect("192.168.1.10", 0, 1)

   # Prepare items to read
   items = []

   # Item 1: 4 bytes from DB1, offset 0
   item1 = S7DataItem()
   item1.Area = Area.DB
   item1.WordLen = WordLen.Byte
   item1.DBNumber = 1
   item1.Start = 0
   item1.Amount = 4
   buffer1 = (c_uint8 * 4)()
   item1.pData = cast(buffer1, POINTER(c_uint8))
   items.append(item1)

   # Item 2: 2 bytes from DB2, offset 10
   item2 = S7DataItem()
   item2.Area = Area.DB
   item2.WordLen = WordLen.Byte
   item2.DBNumber = 2
   item2.Start = 10
   item2.Amount = 2
   buffer2 = (c_uint8 * 2)()
   item2.pData = cast(buffer2, POINTER(c_uint8))
   items.append(item2)

   # Execute the multi-read
   result, data_items = client.read_multi_vars(items)

   # Access the returned data
   value1 = bytearray(buffer1)
   value2 = bytearray(buffer2)

.. warning::

   The S7 protocol limits multi-variable reads to **20 items** per request.
   If you need more, split them across multiple calls.
