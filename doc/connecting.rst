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
   * - S7-200 (serial PPI)
     - --
     - --
     - Use ``PPIClient`` and a serial interface; see :doc:`ppi`.
   * - LOGO! / S7-200 (Ethernet)
     - --
     - --
     - Use ``Logo`` or the controller's documented TSAP values.

.. warning::

   S7-1200 and S7-1500 PLCs ship with PUT/GET communication disabled by
   default. Enable PUT/GET in TIA Portal under the CPU properties before using
   ``s7.Client``. See :doc:`tia-portal-config` for step-by-step instructions.


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

S7-1200 / S7-1500 (PUT/GET)
----------------------------

If PUT/GET access is enabled in TIA Portal, you can also use the legacy
protocol:

.. code-block:: python

   from s7 import Client

   client = Client()
   client.connect("192.168.1.10", 0, 1)

S7-200 Serial PPI
-----------------

Serial S7-200 connections use :class:`~snap7.ppi.PPIClient`, not rack/slot or
TSAP addressing::

   from s7 import PPIClient

   with PPIClient("/dev/ttyUSB0", station=2, baudrate=9600) as client:
       data = client.v_read(0, 4)

Install ``python-snap7[ppi]`` and see :doc:`ppi` for supported areas and
limitations.

LOGO! and Ethernet TSAP Connections
-----------------------------------

For LOGO!, prefer the dedicated :class:`~snap7.logo.Logo` class. Controllers
that expose classic S7 over Ethernet with explicit TSAPs can use
``set_connection_params()`` before connecting:

.. code-block:: python

   from s7 import Client

   client = Client()
   client.set_connection_params("192.168.1.10", 0x1000, 0x2000)
   client.connect("192.168.1.10", 0, 0)

The TSAP values are controller and project specific; the example values are
not universal defaults.

Using a Non-Standard Port
--------------------------

.. code-block:: python

   from s7 import Client

   client = Client()
   client.connect("192.168.1.10", 0, 1, tcp_port=1102)

Routing (Multi-Subnet Access)
------------------------------

.. warning::

   Routing support is experimental and may change in future versions.

When the target PLC sits on a different subnet behind a gateway PLC, use
``connect_routed`` to let the gateway forward the connection:

.. code-block:: python

   from s7 import Client

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

Legacy ``snap7`` Package
-------------------------

If you have existing code using ``snap7.Client``, it continues to work
unchanged — ``snap7`` is an alias for ``s7``:

.. code-block:: python

   import snap7

   client = snap7.Client()
   client.connect("192.168.1.10", 0, 1)

Asynchronous Connections
------------------------

``AsyncClient`` provides native ``asyncio`` I/O and serializes request/response
cycles on its connection::

   import asyncio
   from s7 import AsyncClient

   async def main():
       async with AsyncClient() as client:
           await client.connect("192.168.1.10", 0, 1)
           data = await client.db_read(1, 0, 4)

   asyncio.run(main())
