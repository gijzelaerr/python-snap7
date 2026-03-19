Troubleshooting
===============

This page covers the most common issues encountered when using python-snap7
and how to resolve them.

.. contents:: On this page
   :local:
   :depth: 2


Error Message Reference
-----------------------

The following table maps common S7 error strings to their likely cause and fix.

.. list-table::
   :header-rows: 1
   :widths: 35 30 35

   * - Error message
     - Likely cause
     - Fix
   * - ``CLI : function refused by CPU (Unknown error)``
     - PUT/GET communication is not enabled on the PLC, or the data block
       still has optimized block access enabled.
     - Enable PUT/GET in TIA Portal and disable optimized block access on each
       DB. See :ref:`s7-1200-1500-configuration` below.
   * - ``CPU : Function not available``
     - The requested function is not supported on this PLC model. S7-1200 and
       S7-1500 PLCs restrict certain operations.
     - Check Siemens documentation for your PLC model. Some functions are only
       available on S7-300/400.
   * - ``CPU : Item not available``
     - Wrong DB number, the DB does not exist, or the address is out of range.
     - Verify the DB number exists on the PLC and that the offset and size are
       within bounds.
   * - ``CPU : Address out of range``
     - Reading or writing past the end of a DB or memory area.
     - Check the DB size in TIA Portal and ensure ``start + size`` does not
       exceed it.
   * - ``CPU : Function not authorized for current protection level``
     - The PLC has password protection enabled.
     - Remove or lower the protection level in TIA Portal under
       Protection & Security.
   * - ``ISO : An error occurred during recv TCP : Connection timed out``
     - Network issue: PLC is unreachable, a firewall is blocking port 102, or
       the PLC is not responding.
     - Check network connectivity (``ping``), verify firewall rules, and ensure
       the PLC is powered on and reachable.
   * - ``ISO : An error occurred during send TCP : Connection timed out``
     - Same as above.
     - Same as above.
   * - ``TCP : Unreachable peer``
     - The PLC is not reachable on the network.
     - Verify IP address, subnet, and routing. Ensure the PLC Ethernet port is
       connected and configured.
   * - ``TCP : Connection reset`` / Socket error 32 (broken pipe)
     - The connection to the PLC was lost unexpectedly.
     - The PLC may have been restarted, the cable disconnected, or another
       client took over the connection. See :ref:`connection-recovery` below.


.. _s7-1200-1500-configuration:

S7-1200/1500 Configuration
--------------------------

S7-1200 and S7-1500 PLCs require specific configuration in TIA Portal before
python-snap7 can communicate with them. Without these settings, you will get
``CLI : function refused by CPU`` errors.

Step 1: Enable PUT/GET Communication
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

1. Open your project in TIA Portal.
2. In the project tree, double-click on the PLC device.
3. Go to **Properties** > **Protection & Security** > **Connection mechanisms**.
4. Check **Permit access with PUT/GET communication from remote partner**.
5. Compile and download to the PLC.

.. warning::

   This setting allows any network client to read and write PLC memory without
   authentication. Only enable this on isolated industrial networks.

Step 2: Disable Optimized Block Access
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

This must be done for **each** data block you want to access:

1. In the project tree, right-click on the data block (e.g., DB1).
2. Select **Properties**.
3. Go to the **Attributes** tab.
4. **Uncheck** "Optimized block access".
5. Click OK.
6. Compile and download to the PLC.

.. warning::

   Changing the "Optimized block access" setting reinitializes the data block,
   which resets all values in that DB to their defaults. Do this before
   commissioning, or back up your data first.

Step 3: Compile and Download
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

After making both changes:

1. Compile the project (**Build** > **Compile**).
2. Download to the PLC (**Online** > **Download to device**).
3. The PLC may need to restart depending on the changes.


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


Thread Safety
-------------

The ``Client`` class is **not** thread-safe. Concurrent calls from multiple
threads on the same ``Client`` instance will corrupt the TCP connection state
and cause unpredictable errors.

**Option 1: One client per thread**

.. code-block:: python

   import threading
   import snap7

   def worker(address: str, rack: int, slot: int) -> None:
       client = snap7.Client()
       client.connect(address, rack, slot)
       data = client.db_read(1, 0, 10)
       client.disconnect()

   t1 = threading.Thread(target=worker, args=("192.168.1.10", 0, 1))
   t2 = threading.Thread(target=worker, args=("192.168.1.10", 0, 1))
   t1.start()
   t2.start()

**Option 2: Shared client with a lock**

.. code-block:: python

   import threading
   import snap7

   client = snap7.Client()
   client.connect("192.168.1.10", 0, 1)
   lock = threading.Lock()

   def safe_read(db: int, start: int, size: int) -> bytearray:
       with lock:
           return client.db_read(db, start, size)


Protocol Limitations and FAQ
-----------------------------

python-snap7 implements the S7 protocol over TCP/IP. The following operations
are **not possible** with this protocol:

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - Limitation
     - Explanation
   * - Read tag/symbol names from PLC
     - Symbol names exist only in the TIA Portal project file, not in the PLC.
       The S7 protocol only addresses data by area, DB number, and byte offset.
   * - Get DB structure or layout from PLC
     - The PLC stores only raw bytes. The structure definition lives in the TIA
       Portal project. You must define your data layout in your Python code.
   * - Discover PLCs on the network
     - There is no S7 broadcast discovery mechanism. You must know the PLC's IP
       address.
   * - Create PLC backups
     - Full project backup requires TIA Portal. python-snap7 can upload
       individual blocks, but this is not a complete backup.
   * - Access S7-1200/1500 PLCs with S7CommPlus security
     - PLCs configured to require S7CommPlus encrypted communication cannot be
       accessed with the classic S7 protocol. PUT/GET must be enabled as a
       fallback.
