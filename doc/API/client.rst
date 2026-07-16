Client
======

python-snap7 provides two client packages:

- ``s7commplus``: S7CommPlus protocol for S7-1200/1500 PLCs
- ``snap7``: Classic S7 protocol for S7-300/400 and PUT/GET access on S7-1200/1500

s7commplus.Client
-----------------

.. code-block:: python

   from s7commplus import Client

   client = Client()
   client.connect("192.168.1.10")
   data = client.db_read(1, 0, 4)
   client.disconnect()

s7commplus.AsyncClient
----------------------

.. code-block:: python

   import asyncio
   from s7commplus import AsyncClient

   async def main():
       client = AsyncClient()
       await client.connect("192.168.1.10")
       data = await client.db_read(1, 0, 4)
       await client.disconnect()

   asyncio.run(main())

V2 connection with TLS
----------------------

S7-1500 PLCs with firmware 2.x use S7CommPlus V2, which requires TLS. Pass
``use_tls=True`` to the ``connect()`` method:

.. code-block:: python

   from s7commplus import Client

   client = Client()
   client.connect("192.168.1.10", use_tls=True)
   data = client.db_read(1, 0, 4)
   client.disconnect()

For PLCs with custom certificates, provide the certificate paths:

.. code-block:: python

   client.connect(
       "192.168.1.10",
       use_tls=True,
       tls_cert="/path/to/client.pem",
       tls_key="/path/to/client.key",
       tls_ca="/path/to/ca.pem",
   )

Password authentication
-----------------------

Password-protected PLCs require the ``password`` keyword argument:

.. code-block:: python

   from s7commplus import Client

   client = Client()
   client.connect("192.168.1.10", use_tls=True, password="my_plc_password")
   data = client.db_read(1, 0, 4)
   client.disconnect()

Concurrent async reads
----------------------

An internal ``asyncio.Lock`` serialises each send/receive cycle so that
multiple coroutines can safely share a single connection:

.. code-block:: python

   results = await asyncio.gather(
       client.db_read(1, 0, 4),
       client.db_read(1, 10, 4),
   )

----

.. automodule:: s7commplus.client
   :members:

.. automodule:: s7commplus.async_client
   :members:

snap7.Client (legacy)
---------------------

The ``snap7.Client`` implements the classic S7 protocol for S7-300/400 PLCs
and PUT/GET access on S7-1200/1500.

.. automodule:: snap7.client
   :members:

snap7.AsyncClient (legacy)
--------------------------

.. automodule:: snap7.async_client
   :members:
   :exclude-members: AsyncISOTCPConnection
