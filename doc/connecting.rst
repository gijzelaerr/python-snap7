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
   default. Enable it in TIA Portal under the CPU properties before
   connecting. See :doc:`tia-portal-config` for step-by-step instructions.


S7-300
------

.. code-block:: python

   import snap7

   client = snap7.Client()
   client.connect("192.168.1.10", 0, 2)

S7-400
------

.. code-block:: python

   import snap7

   client = snap7.Client()
   client.connect("192.168.1.10", 0, 3)

S7-1200 / S7-1500
------------------

.. code-block:: python

   import snap7

   client = snap7.Client()
   client.connect("192.168.1.10", 0, 1)

.. tip::

   For S7-1200/1500 PLCs you can also use the **experimental** ``s7`` package,
   which automatically tries the newer S7CommPlus protocol and falls back to
   legacy S7 when needed::

      from s7 import Client

      client = Client()
      client.connect("192.168.1.10", 0, 1)
      print(client.protocol)  # Protocol.S7COMMPLUS or Protocol.LEGACY

   See :doc:`API/s7commplus` for full details.

S7-200 / Logo (TSAP Connection)
--------------------------------

.. code-block:: python

   import snap7

   client = snap7.Client()
   client.set_connection_params("192.168.1.10", 0x1000, 0x2000)
   client.connect("192.168.1.10", 0, 0)

Using a Non-Standard Port
--------------------------

.. code-block:: python

   import snap7

   client = snap7.Client()
   client.connect("192.168.1.10", 0, 1, tcp_port=1102)
