Connecting to PLCs
==================

This page shows how to connect to different Siemens PLC models using
python-snap7. All examples use the recommended ``s7`` package, which works
with every supported PLC model.

.. contents:: On this page
   :local:
   :depth: 2


Rack/Slot Reference
-------------------

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
     - PUT/GET access must be enabled in TIA Portal (or use S7CommPlus)
   * - S7-1500
     - 0
     - 1
     - PUT/GET access must be enabled in TIA Portal (or use S7CommPlus)
   * - S7-200 / Logo
     - --
     - --
     - Use ``set_connection_params`` with TSAP addressing (legacy ``snap7`` package)

.. warning::

   S7-1200 and S7-1500 PLCs ship with PUT/GET communication disabled by
   default. When using ``s7.Client``, the library automatically tries the
   S7CommPlus protocol first, which does not require PUT/GET to be enabled.
   If you need to use the legacy protocol, enable PUT/GET in TIA Portal
   under the CPU properties. See :doc:`tia-portal-config` for step-by-step
   instructions.


S7-300
------

.. code-block:: python

   from s7 import Client

   client = Client()
   client.connect("192.168.1.10", 0, 2)

S7-400
------

.. code-block:: python

   from s7 import Client

   client = Client()
   client.connect("192.168.1.10", 0, 3)

S7-1200 / S7-1500
------------------

.. code-block:: python

   from s7 import Client

   client = Client()
   client.connect("192.168.1.10", 0, 1)
   print(client.protocol)  # Protocol.S7COMMPLUS or Protocol.LEGACY

The client automatically tries S7CommPlus first and falls back to legacy S7
when needed. You can also force a specific protocol:

.. code-block:: python

   from s7 import Client, Protocol

   client = Client()
   # Force legacy S7 only (requires PUT/GET enabled)
   client.connect("192.168.1.10", 0, 1, protocol=Protocol.LEGACY)

   # Force S7CommPlus (raises on failure)
   client.connect("192.168.1.10", 0, 1, protocol=Protocol.S7COMMPLUS)

See :doc:`API/s7commplus` for details on TLS and password authentication.

S7-200 / Logo (TSAP Connection)
--------------------------------

S7-200 and Logo PLCs require TSAP addressing via the legacy ``snap7`` package:

.. code-block:: python

   import snap7

   client = snap7.Client()
   client.set_connection_params("192.168.1.10", 0x1000, 0x2000)
   client.connect("192.168.1.10", 0, 0)

Using a Non-Standard Port
--------------------------

.. code-block:: python

   from s7 import Client

   client = Client()
   client.connect("192.168.1.10", 0, 1, tcp_port=1102)

Legacy ``snap7`` Package
-------------------------

If you have existing code using ``snap7.Client``, it continues to work
unchanged:

.. code-block:: python

   import snap7

   client = snap7.Client()
   client.connect("192.168.1.10", 0, 1)
