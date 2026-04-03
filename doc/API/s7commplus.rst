S7 Client (recommended)
=======================

The ``s7`` package is the recommended entry point for communicating with any
supported Siemens S7 PLC. It provides a unified client that works with all
PLC models -- S7-300, S7-400, S7-1200 and S7-1500 -- and automatically
selects the best protocol (S7CommPlus or legacy S7).

Synchronous client
------------------

.. code-block:: python

   from s7 import Client

   client = Client()
   client.connect("192.168.1.10", 0, 1)
   data = client.db_read(1, 0, 4)
   print(client.protocol)   # Protocol.S7COMMPLUS or Protocol.LEGACY
   client.disconnect()

Asynchronous client
-------------------

.. code-block:: python

   import asyncio
   from s7 import AsyncClient

   async def main():
       client = AsyncClient()
       await client.connect("192.168.1.10", 0, 1)
       data = await client.db_read(1, 0, 4)
       await client.disconnect()

   asyncio.run(main())

V2 connection with TLS
----------------------

S7-1500 PLCs with firmware 2.x use S7CommPlus V2, which requires TLS. Pass
``use_tls=True`` to the ``connect()`` method:

.. code-block:: python

   from s7 import Client

   client = Client()
   client.connect("192.168.1.10", 0, 1, use_tls=True)
   data = client.db_read(1, 0, 4)
   client.disconnect()

For PLCs with custom certificates, provide the certificate paths:

.. code-block:: python

   client.connect(
       "192.168.1.10", 0, 1,
       use_tls=True,
       tls_cert="/path/to/client.pem",
       tls_key="/path/to/client.key",
       tls_ca="/path/to/ca.pem",
   )

Password authentication
-----------------------

Password-protected PLCs require the ``password`` keyword argument:

.. code-block:: python

   from s7 import Client

   client = Client()
   client.connect("192.168.1.10", 0, 1, use_tls=True, password="my_plc_password")
   data = client.db_read(1, 0, 4)
   client.disconnect()

Protocol selection
------------------

By default the client uses ``Protocol.AUTO`` which tries S7CommPlus first.
You can force a specific protocol:

.. code-block:: python

   from s7 import Client, Protocol

   # Force legacy S7 only
   client = Client()
   client.connect("192.168.1.10", 0, 1, protocol=Protocol.LEGACY)

   # Force S7CommPlus (raises on failure)
   client.connect("192.168.1.10", 0, 1, protocol=Protocol.S7COMMPLUS)

API reference
-------------

.. automodule:: s7.client
   :members:

.. automodule:: s7.async_client
   :members:
