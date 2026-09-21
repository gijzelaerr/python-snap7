Client
======

The ``s7`` package implements the classic S7 protocol for S7-300/400 PLCs and
PUT/GET access on S7-1200/1500.

Use ``Client`` for synchronous applications::

   from s7 import Client

   with Client() as client:
       client.connect("192.168.1.10", 0, 1)
       data = client.db_read(1, 0, 4)

Use ``AsyncClient`` when the surrounding application uses ``asyncio``::

   import asyncio
   from s7 import AsyncClient

   async def main():
       async with AsyncClient() as client:
           await client.connect("192.168.1.10", 0, 1)
           data = await client.db_read(1, 0, 4)

   asyncio.run(main())

Both clients expose the same main PLC operations, including area and DB
access, block transfer, CPU information and control, clock access, force
operations, and session passwords. Methods that perform I/O are coroutines on
``AsyncClient``. See :doc:`../advanced` for the less common operations.

s7.Client
---------

.. automodule:: snap7.client
   :members:
   :inherited-members:

s7.AsyncClient
--------------

.. automodule:: snap7.async_client
   :members:
   :inherited-members:
   :exclude-members: AsyncISOTCPConnection
