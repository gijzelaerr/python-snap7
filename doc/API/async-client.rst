Async Client
============

``AsyncClient`` is the ``asyncio`` counterpart of :doc:`client`. It has the
same PLC operations, and every method that talks to the PLC is a coroutine::

   import asyncio
   from s7 import AsyncClient

   async def main() -> None:
       async with AsyncClient() as client:
           await client.connect("192.168.1.10", 0, 1)
           data = await client.db_read(1, 0, 4)
           await client.db_write(1, 0, bytearray([1, 2, 3, 4]))

   asyncio.run(main())

Leaving the ``async with`` block disconnects the client.

Concurrency
-----------

An internal ``asyncio.Lock`` serialises each request and its reply, so several
coroutines can share one client::

   async def read_all(client: AsyncClient) -> list[bytearray]:
       return await asyncio.gather(
           client.db_read(1, 0, 4),
           client.db_read(1, 10, 4),
           client.db_read(2, 0, 8),
       )

The requests still go to the PLC one after the other; ``gather`` only lets the
rest of the application run while they wait. One client belongs to one event
loop. Do not call it from other threads.

Differences from ``Client``
---------------------------

* There is no heartbeat thread and no ``heartbeat_interval`` argument.
  ``is_alive`` reports the connection state seen by the last operation.
* ``read_multi_vars`` and ``write_multi_vars`` accept only the dict form, and
  ``read_multi_vars`` and ``read_tags`` read the items one after the other.
  There is no read optimizer and no ``max_parallel``. See
  :doc:`../multi-variable`.

s7.AsyncClient
--------------

.. automodule:: snap7.async_client
   :members:
   :inherited-members:
   :exclude-members: AsyncISOTCPConnection
