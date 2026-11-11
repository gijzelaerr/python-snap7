Multi-Variable Read and Write
=============================

Reading several variables in one call is faster than reading them one by one:
the client merges adjacent addresses and packs the rest into as few PDU
exchanges as the negotiated PDU size allows.

Reading tags
------------

``read_tags`` takes address strings (or :class:`~snap7.tags.Tag` objects) and
returns the decoded values in the same order:

.. code-block:: python

   from s7 import Client

   client = Client()
   client.connect("192.168.1.10", 0, 1)

   level, setpoint, count = client.read_tags(
       ["DB200.DBD16:REAL", "DB200.DBD12:REAL", "DB200.DBW2:INT"]
   )

See :doc:`API/tags` for the address syntax.

Reading raw bytes
-----------------

``read_multi_vars`` takes a list of dicts with ``area``, ``start``, ``size``
and, for data blocks, ``db_number``. It returns a result code and one
``bytearray`` per item, in the order of the request:

.. code-block:: python

   from s7.type import Area
   from s7.util import get_int, get_real

   items = [
       {"area": Area.DB, "db_number": 200, "start": 16, "size": 4},
       {"area": Area.DB, "db_number": 200, "start": 2, "size": 2},
       {"area": Area.MK, "start": 20, "size": 1},
   ]
   _, buffers = client.read_multi_vars(items)

   level = get_real(buffers[0], 0)
   count = get_int(buffers[1], 0)

A failed read raises an exception from :mod:`snap7.error`; there is no
per-item status to check.

Writing
-------

``write_multi_vars`` takes the same dicts with ``data`` instead of ``size``:

.. code-block:: python

   client.write_multi_vars(
       [
           {"area": Area.DB, "db_number": 1, "start": 0, "data": bytearray([0, 10, 0, 20])},
           {"area": Area.MK, "start": 20, "data": bytearray([0x01])},
       ]
   )

The items are written one after the other, each in its own request. The call
raises on the first item the PLC refuses, and the items before it stay
written.

Limits and tuning
-----------------

.. warning::

   One call accepts at most **20 items** (``Client.MAX_VARS``) and raises
   ``ValueError`` above that. Split longer lists across several calls.

* The read optimizer is experimental. Set ``client.use_optimizer = False`` to
  read each item with its own request instead. See :doc:`API/optimizer`.
* When a read needs more than one PDU, ``Client`` sends up to
  ``client.max_parallel`` requests before it reads the replies. See
  :doc:`thread-safety`.
* ``AsyncClient`` has the same methods as coroutines, but reads the items one
  after the other without the optimizer.

The ``S7DataItem`` form
-----------------------

``Client.read_multi_vars`` and ``Client.write_multi_vars`` still accept the
ctypes ``S7DataItem`` structures of the original Snap7 library, so that old
code keeps working. This path reads and writes the items one at a time and
never sets the ``Result`` field of an item; errors raise exceptions instead.
``AsyncClient`` does not accept it. Use ``read_tags`` or the dict form in new
code.

Complete scripts are in ``example/read_multi.py`` and
``example/write_multi.py``.
