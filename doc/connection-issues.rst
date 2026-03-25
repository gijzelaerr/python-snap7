Connection Issues
=================

.. contents:: On this page
   :local:
   :depth: 2


.. _connection-recovery:

Automatic Reconnection
----------------------

The :class:`~snap7.client.Client` has built-in auto-reconnect with exponential
backoff and optional heartbeat monitoring. This is the recommended approach for
long-running applications:

.. code-block:: python

   import snap7

   def on_disconnect():
       print("Connection lost!")

   def on_reconnect():
       print("Reconnected!")

   client = snap7.Client(
       auto_reconnect=True,        # Enable automatic reconnection
       max_retries=5,              # Retry up to 5 times (default: 3)
       retry_delay=1.0,            # Initial delay between retries in seconds
       backoff_factor=2.0,         # Double the delay after each failure
       max_delay=30.0,             # Cap delay at 30 seconds
       heartbeat_interval=10.0,    # Probe connection every 10 seconds (0=disabled)
       on_disconnect=on_disconnect,
       on_reconnect=on_reconnect,
   )
   client.connect("192.168.1.10", 0, 1)

   # If the connection drops, read/write operations will automatically
   # reconnect before retrying. The heartbeat detects silent disconnects.
   data = client.db_read(1, 0, 10)

The parameters:

- **auto_reconnect**: Enable automatic reconnection on connection loss.
- **max_retries**: Maximum reconnection attempts before raising an error.
- **retry_delay**: Initial delay (seconds) between reconnection attempts.
- **backoff_factor**: Multiplier applied to the delay after each failed attempt.
- **max_delay**: Upper bound on the delay between attempts.
- **heartbeat_interval**: Interval (seconds) for background heartbeat probes.
  Set to ``0`` to disable (default).
- **on_disconnect**: Callback invoked when the connection is lost.
- **on_reconnect**: Callback invoked after a successful reconnection.


Manual Reconnection
-------------------

If you need full control over reconnection behavior, you can implement it
manually:

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
