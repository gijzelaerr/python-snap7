Connection Issues
=================

.. contents:: On this page
   :local:
   :depth: 2


.. _connection-recovery:

Connection Recovery
-------------------

Network connections to PLCs can drop due to cable issues, PLC restarts, or
network problems. Use a reconnection pattern to handle this gracefully:

.. code-block:: python

   import snap7
   import time
   import logging

   logger = logging.getLogger(__name__)

   client = snap7.Client()

   def connect(address: str = "192.168.1.10", rack: int = 0, slot: int = 1) -> None:
       client.connect(address, rack, slot)

   def safe_read(db: int, start: int, size: int) -> bytearray:
       """Read from DB with automatic reconnection on failure."""
       try:
           return client.db_read(db, start, size)
       except Exception:
           logger.warning("Read failed, attempting reconnection...")
           try:
               client.disconnect()
           except Exception:
               pass
           time.sleep(1)
           connect()
           return client.db_read(db, start, size)

   def safe_write(db: int, start: int, data: bytearray) -> None:
       """Write to DB with automatic reconnection on failure."""
       try:
           client.db_write(db, start, data)
       except Exception:
           logger.warning("Write failed, attempting reconnection...")
           try:
               client.disconnect()
           except Exception:
               pass
           time.sleep(1)
           connect()
           client.db_write(db, start, data)

For long-running applications, wrap your main loop with reconnection logic:

.. code-block:: python

   while True:
       try:
           data = safe_read(1, 0, 10)
           # process data...
           time.sleep(0.5)
       except Exception:
           logger.error("Failed after reconnection attempt, retrying in 5s...")
           time.sleep(5)


Connection Timeout
------------------

The default connection timeout is 5 seconds. You can configure it by accessing
the underlying connection object:

.. code-block:: python

   import snap7

   client = snap7.Client()

   # Connect with a custom timeout (in seconds)
   client.connect("192.168.1.10", 0, 1)

   # The timeout is set on the underlying connection
   # Default is 5.0 seconds
   client.connection.timeout = 10.0  # Set to 10 seconds

To set the timeout **before** connecting, use ``set_connection_params`` and then
connect manually, or simply reconnect after adjusting:

.. code-block:: python

   client = snap7.Client()
   client.connect("192.168.1.10", 0, 1)

   # Adjust timeout for slow networks
   client.connection.timeout = 15.0

.. note::

   If you are experiencing frequent timeouts, check your network quality first.
   Typical S7 communication on a local network should respond within
   milliseconds.
