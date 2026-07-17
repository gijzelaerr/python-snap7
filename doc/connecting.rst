Connecting to PLCs
==================

This page shows how to connect to different Siemens PLC models using
python-snap7.

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
     - PUT/GET access must be enabled in TIA Portal
   * - S7-1500
     - 0
     - 1
     - PUT/GET access must be enabled in TIA Portal
   * - S7-200 / Logo
     - --
     - --
     - Use ``set_connection_params`` with TSAP addressing

.. warning::

   S7-1200 and S7-1500 PLCs ship with PUT/GET communication disabled by
   default. You must enable PUT/GET in TIA Portal under the CPU properties
   to use the legacy S7 protocol.


S7-300
------

.. code-block:: python

   from snap7 import Client

   client = Client()
   client.connect("192.168.1.10", 0, 2)

S7-400
------

.. code-block:: python

   from snap7 import Client

   client = Client()
   client.connect("192.168.1.10", 0, 3)

S7-1200 / S7-1500
------------------

.. code-block:: python

   from snap7 import Client

   client = Client()
   client.connect("192.168.1.10", 0, 1)

S7-200 / Logo (TSAP Connection)
--------------------------------

S7-200 and Logo PLCs require TSAP addressing:

.. code-block:: python

   from snap7 import Client

   client = Client()
   client.set_connection_params("192.168.1.10", 0x1000, 0x2000)
   client.connect("192.168.1.10", 0, 0)

Using a Non-Standard Port
--------------------------

.. code-block:: python

   from snap7 import Client

   client = Client()
   client.connect("192.168.1.10", 0, 1, tcp_port=1102)

Routing (Multi-Subnet Access)
------------------------------

.. warning::

   Routing support is experimental and may change in future versions.

When the target PLC sits on a different subnet behind a gateway PLC, use
``connect_routed`` to let the gateway forward the connection:

.. code-block:: python

   from snap7 import Client

   client = Client()
   client.connect_routed(
       host="192.168.1.1",       # gateway PLC address
       router_rack=0,            # gateway rack
       router_slot=2,            # gateway slot
       subnet=0x0001,            # target subnet ID
       dest_rack=0,              # target PLC rack
       dest_slot=3,              # target PLC slot
   )
   data = client.db_read(1, 0, 4)
   client.disconnect()
