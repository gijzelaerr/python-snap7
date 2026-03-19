Examples & Cookbook
===================

This page provides practical examples for common python-snap7 tasks. All code
assumes you have already installed python-snap7:

.. code-block:: bash

   pip install python-snap7


Connecting to Different PLC Models
-----------------------------------

Rack/Slot Reference
^^^^^^^^^^^^^^^^^^^

.. list-table::
   :header-rows: 1
   :widths: 20 10 10 60

   * - PLC Model
     - Rack
     - Slot
     - Notes
   * - S7-300
     - 0
     - 2
     -
   * - S7-400
     - 0
     - 3
     - May vary with multi-rack configurations
   * - S7-1200
     - 0
     - 1
     - PUT/GET access must be enabled in TIA Portal
   * - S7-1500
     - 0
     - 1
     - PUT/GET access must be enabled in TIA Portal
   * - S7-200 / Logo
     - --
     - --
     - Use ``set_connection_params`` with TSAP addressing

.. warning::

   S7-1200 and S7-1500 PLCs ship with PUT/GET communication disabled by
   default. Enable it in TIA Portal under the CPU properties before
   connecting.

S7-300
^^^^^^

.. code-block:: python

   import snap7

   client = snap7.Client()
   client.connect("192.168.1.10", 0, 2)

S7-400
^^^^^^

.. code-block:: python

   import snap7

   client = snap7.Client()
   client.connect("192.168.1.10", 0, 3)

S7-1200 / S7-1500
^^^^^^^^^^^^^^^^^^

.. code-block:: python

   import snap7

   client = snap7.Client()
   client.connect("192.168.1.10", 0, 1)

S7-200 / Logo (TSAP Connection)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   import snap7

   client = snap7.Client()
   client.set_connection_params("192.168.1.10", 0x1000, 0x2000)
   client.connect("192.168.1.10", 0, 0)

Using a Non-Standard Port
^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   import snap7

   client = snap7.Client()
   client.connect("192.168.1.10", 0, 1, tcp_port=1102)


Address Mapping Guide
---------------------

PLC addresses in Siemens TIA Portal / STEP 7 map to python-snap7 API calls
as follows.

.. list-table::
   :header-rows: 1
   :widths: 25 40 35

   * - PLC Address
     - python-snap7 Call
     - Explanation
   * - DB1.DBB0
     - ``db_read(1, 0, 1)``
     - 1 byte at offset 0 of DB1
   * - DB1.DBW10
     - ``db_read(1, 10, 2)``
     - 2 bytes (WORD) at offset 10
   * - DB1.DBD20
     - ``db_read(1, 20, 4)``
     - 4 bytes (DWORD) at offset 20
   * - DB1.DBX0.3
     - ``db_read(1, 0, 1)`` then ``get_bool(data, 0, 3)``
     - Bit 3 of byte 0
   * - M0.0
     - ``mb_read(0, 1)`` then ``get_bool(data, 0, 0)``
     - Bit 0 of merker byte 0
   * - MW10
     - ``mb_read(10, 2)``
     - 2 bytes (WORD) from merker byte 10
   * - IW0 / EW0
     - ``read_area(Area.PE, 0, 0, 2)``
     - Analog input word at address 0
   * - QW0 / AW0
     - ``read_area(Area.PA, 0, 0, 2)``
     - Analog output word at address 0

.. important::

   The ``byte_index`` parameter in all ``snap7.util`` getter/setter functions
   is **relative to the returned bytearray**, not the absolute PLC address.

   For example, to read DB1.DBX10.3:

   .. code-block:: python

      data = client.db_read(1, 10, 1)  # Read 1 byte starting at offset 10
      value = snap7.util.get_bool(data, 0, 3)  # byte_index=0, NOT 10

   You read from PLC offset 10, but ``data[0]`` *is* byte 10 from the PLC.


Data Types Cookbook
-------------------

Each example below shows a complete read and write cycle.

BOOL
^^^^

Booleans require a **read-modify-write** pattern. You cannot write a single
bit to the PLC; you must read the enclosing byte, change the bit, then write
the whole byte back.

.. code-block:: python

   import snap7

   client = snap7.Client()
   client.connect("192.168.1.10", 0, 1)

   # Read DB1.DBX0.3 (bit 3 of byte 0)
   data = client.db_read(1, 0, 1)
   value = snap7.util.get_bool(data, 0, 3)
   print(f"DB1.DBX0.3 = {value}")

   # Write DB1.DBX0.3 -- read first, then modify, then write
   data = client.db_read(1, 0, 1)
   snap7.util.set_bool(data, 0, 3, True)
   client.db_write(1, 0, data)

.. warning::

   Never write a freshly created ``bytearray`` for booleans. Always read the
   current byte first to avoid overwriting neighboring bits.

BYTE (1 byte, unsigned 0--255)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   # Read DB1.DBB0 (1 byte at offset 0)
   data = client.db_read(1, 0, 1)
   value = snap7.util.get_byte(data, 0)
   print(f"DB1.DBB0 = {value}")

   # Write
   data = bytearray(1)
   snap7.util.set_byte(data, 0, 200)
   client.db_write(1, 0, data)

INT (2 bytes, signed -32768 to 32767)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   # Read DB1.DBW10
   data = client.db_read(1, 10, 2)
   value = snap7.util.get_int(data, 0)
   print(f"DB1.DBW10 = {value}")

   # Write
   data = bytearray(2)
   snap7.util.set_int(data, 0, -1234)
   client.db_write(1, 10, data)

WORD (2 bytes, unsigned 0--65535)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   # Read DB1.DBW20
   data = client.db_read(1, 20, 2)
   value = snap7.util.get_word(data, 0)
   print(f"DB1.DBW20 = {value}")

   # Write
   data = bytearray(2)
   snap7.util.set_word(data, 0, 50000)
   client.db_write(1, 20, data)

DINT (4 bytes, signed -2147483648 to 2147483647)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   # Read DB1.DBD30
   data = client.db_read(1, 30, 4)
   value = snap7.util.get_dint(data, 0)
   print(f"DB1.DBD30 = {value}")

   # Write
   data = bytearray(4)
   snap7.util.set_dint(data, 0, 100000)
   client.db_write(1, 30, data)

DWORD (4 bytes, unsigned 0--4294967295)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   # Read DB1.DBD40
   data = client.db_read(1, 40, 4)
   value = snap7.util.get_dword(data, 0)
   print(f"DB1.DBD40 = {value}")

   # Write
   data = bytearray(4)
   snap7.util.set_dword(data, 0, 3000000000)
   client.db_write(1, 40, data)

REAL (4 bytes, IEEE 754 float)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   # Read DB1.DBD50
   data = client.db_read(1, 50, 4)
   value = snap7.util.get_real(data, 0)
   print(f"DB1.DBD50 = {value}")

   # Write
   data = bytearray(4)
   snap7.util.set_real(data, 0, 3.14)
   client.db_write(1, 50, data)

LREAL (8 bytes, IEEE 754 double)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   # Read DB1, offset 60, 8 bytes
   data = client.db_read(1, 60, 8)
   value = snap7.util.get_lreal(data, 0)
   print(f"LREAL = {value}")

   # Write
   data = bytearray(8)
   snap7.util.set_lreal(data, 0, 3.141592653589793)
   client.db_write(1, 60, data)

STRING (2 header bytes + characters)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

S7 strings have a specific format:

- **Byte 0**: Maximum length (set when the variable is declared in the PLC)
- **Byte 1**: Actual (current) length of the string content
- **Bytes 2+**: ASCII characters

When reading, always request ``max_length + 2`` bytes to include the header.

.. code-block:: python

   # Read a string at DB1, offset 10, declared as STRING[20] in the PLC
   max_length = 20
   data = client.db_read(1, 10, max_length + 2)  # 20 + 2 header bytes = 22
   text = snap7.util.get_string(data, 0)
   print(f"String = '{text}'")

   # Write a string
   data = client.db_read(1, 10, max_length + 2)
   snap7.util.set_string(data, 0, "Hello", max_length)
   client.db_write(1, 10, data)

.. note::

   Always read the existing data before writing a string. The
   ``set_string`` function preserves the max-length header byte and pads
   unused characters with spaces.

DATE_AND_TIME (8 bytes, BCD encoded)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   from datetime import datetime

   # Read DATE_AND_TIME at DB1, offset 70 (returns ISO 8601 string)
   data = client.db_read(1, 70, 8)
   dt_string = snap7.util.get_dt(data, 0)
   print(f"DATE_AND_TIME = {dt_string}")  # e.g. '2024-06-15T14:30:00.000000'

   # Parse to Python datetime if needed
   dt_obj = datetime.fromisoformat(dt_string)

   # Write DATE_AND_TIME
   data = client.db_read(1, 70, 8)
   snap7.util.set_dt(data, 0, datetime(2024, 6, 15, 14, 30, 0))
   client.db_write(1, 70, data)


Memory Areas
------------

python-snap7 provides convenience methods for data blocks and merkers, and
the generic ``read_area`` / ``write_area`` for all other areas.

Data Blocks (DB)
^^^^^^^^^^^^^^^^

.. code-block:: python

   # Read 10 bytes from DB1 starting at offset 0
   data = client.db_read(1, 0, 10)

   # Write 4 bytes to DB1 starting at offset 0
   client.db_write(1, 0, bytearray([0x01, 0x02, 0x03, 0x04]))

Merkers / Flags (M)
^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   # Read 4 merker bytes starting at MB0
   data = client.mb_read(0, 4)

   # Write 2 bytes starting at MB10
   client.mb_write(10, 2, bytearray([0xFF, 0x00]))

Inputs (I / E)
^^^^^^^^^^^^^^

.. code-block:: python

   from snap7.type import Area

   # Read 2 input bytes starting at IB0
   data = client.read_area(Area.PE, 0, 0, 2)

Outputs (Q / A)
^^^^^^^^^^^^^^^

.. code-block:: python

   from snap7.type import Area

   # Read 2 output bytes starting at QB0
   data = client.read_area(Area.PA, 0, 0, 2)

   # Write to QB0
   client.write_area(Area.PA, 0, 0, bytearray([0x00, 0xFF]))

Timers (T)
^^^^^^^^^^

.. code-block:: python

   from snap7.type import Area

   # Read timer T0 (1 timer = 2 bytes)
   data = client.read_area(Area.TM, 0, 0, 1)

Counters (C)
^^^^^^^^^^^^^

.. code-block:: python

   from snap7.type import Area

   # Read counter C0 (1 counter = 2 bytes)
   data = client.read_area(Area.CT, 0, 0, 1)


Analog I/O
-----------

Analog inputs are typically 16-bit integers in the peripheral input area
(``Area.PE``). The raw value from the PLC needs to be scaled to engineering
units.

Reading Analog Inputs
^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   import snap7
   from snap7.type import Area

   client = snap7.Client()
   client.connect("192.168.1.10", 0, 1)

   # Read AIW0 (analog input word at address 0)
   data = client.read_area(Area.PE, 0, 0, 2)
   raw_value = snap7.util.get_int(data, 0)
   print(f"Raw value: {raw_value}")

   # Scale to engineering units
   # S7 analog modules typically use 0-27648 for 0-100% range
   min_range = 0.0    # e.g., 0 bar
   max_range = 10.0   # e.g., 10 bar
   scaled = raw_value * (max_range - min_range) / 27648.0 + min_range
   print(f"Pressure: {scaled:.2f} bar")

   # Read AIW2 (second analog input)
   data = client.read_area(Area.PE, 0, 2, 2)
   raw_value = snap7.util.get_int(data, 0)

Writing Analog Outputs
^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   from snap7.type import Area

   # Write to AQW0 (analog output word at address 0)
   data = bytearray(2)
   snap7.util.set_int(data, 0, 13824)  # ~50% of 27648
   client.write_area(Area.PA, 0, 0, data)

.. note::

   The standard scaling factor 27648 applies to most Siemens analog I/O
   modules. Check your module documentation for the actual range.


Multi-Variable Read
-------------------

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


Server Setup for Testing
-------------------------

The built-in server lets you test your client code without a physical PLC.

Basic Server Example
^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   from snap7.server import Server
   from snap7.type import SrvArea
   from ctypes import c_char

   # Create and configure the server
   server = Server()

   # Register a data block (DB1) with 100 bytes
   db_size = 100
   db_data = bytearray(db_size)
   db_array = (c_char * db_size).from_buffer(db_data)
   server.register_area(SrvArea.DB, 1, db_array)

   # Start the server on a non-privileged port
   server.start(tcp_port=1102)

Client-Server Round Trip
^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   import snap7
   from snap7.server import Server
   from snap7.type import SrvArea
   from ctypes import c_char

   # --- Server setup ---
   server = Server()
   db_size = 100
   db_data = bytearray(db_size)
   db_array = (c_char * db_size).from_buffer(db_data)
   server.register_area(SrvArea.DB, 1, db_array)
   server.start(tcp_port=1102)

   # --- Client connection ---
   client = snap7.Client()
   client.connect("127.0.0.1", 0, 1, tcp_port=1102)

   # Write data
   client.db_write(1, 0, bytearray([0x01, 0x02, 0x03, 0x04]))

   # Read it back
   data = client.db_read(1, 0, 4)
   print(f"Read back: {list(data)}")  # [1, 2, 3, 4]

   # Clean up
   client.disconnect()
   server.stop()

Registering Multiple Areas
^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   from snap7.server import Server
   from snap7.type import SrvArea
   from ctypes import c_char

   server = Server()

   # Register DB1
   db1_data = bytearray(100)
   db1 = (c_char * 100).from_buffer(db1_data)
   server.register_area(SrvArea.DB, 1, db1)

   # Register DB2
   db2_data = bytearray(200)
   db2 = (c_char * 200).from_buffer(db2_data)
   server.register_area(SrvArea.DB, 2, db2)

   # Register merker area (256 bytes)
   mk_data = bytearray(256)
   mk = (c_char * 256).from_buffer(mk_data)
   server.register_area(SrvArea.MK, 0, mk)

   server.start(tcp_port=1102)

.. note::

   Use a port number above 1024 (e.g., 1102) to avoid requiring root/admin
   privileges. Port 102 is the standard S7 port but is in the privileged
   range.

Using the Mainloop Helper
^^^^^^^^^^^^^^^^^^^^^^^^^^

For quick testing, the ``mainloop`` function starts a server with common
data blocks pre-registered:

.. code-block:: python

   from snap7.server import mainloop

   # Blocks the current thread
   mainloop(tcp_port=1102)
