AsyncClient (legacy)
====================

The :class:`~snap7.async_client.AsyncClient` is the legacy async S7 client.
For new projects, we recommend using ``s7.AsyncClient`` instead --
see :doc:`s7commplus`.

The :class:`~snap7.async_client.AsyncClient` provides a native ``asyncio``
interface for communicating with Siemens S7 PLCs.  It has feature parity with
the synchronous :class:`~snap7.client.Client` and is safe for concurrent use
via ``asyncio.gather()``.

Quick start
-----------

.. code-block:: python

   import asyncio
   from s7 import AsyncClient

   async def main():
       async with AsyncClient() as client:
           await client.connect("192.168.1.10", 0, 1)
           data = await client.db_read(1, 0, 4)
           print(data)

   asyncio.run(main())

Concurrent reads
----------------

An internal ``asyncio.Lock`` serialises each send/receive cycle so that
multiple coroutines can safely share a single connection:

.. code-block:: python

   results = await asyncio.gather(
       client.db_read(1, 0, 4),
       client.db_read(1, 10, 4),
   )

API reference
-------------

.. automodule:: snap7.async_client
   :members:
   :exclude-members: AsyncISOTCPConnection
