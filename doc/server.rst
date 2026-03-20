Server Setup for Testing
========================

The built-in server lets you test your client code without a physical PLC.

.. contents:: On this page
   :local:
   :depth: 2


Basic Server Example
--------------------

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
-------------------------

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
---------------------------

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
--------------------------

For quick testing, the ``mainloop`` function starts a server with common
data blocks pre-registered:

.. code-block:: python

   from snap7.server import mainloop

   # Blocks the current thread
   mainloop(tcp_port=1102)
