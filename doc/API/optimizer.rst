Optimizer
=========

.. warning::

   The read optimizer is **experimental** and its API may change in future
   versions. Disable it with ``client.use_optimizer = False`` if you
   encounter issues.

The multi-variable read optimizer merges adjacent or overlapping read requests
and packs them into minimal PDU-sized S7 exchanges. This significantly reduces
the number of round-trips when reading many scattered variables.

How it works
------------

The optimizer uses a three-stage pipeline inspired by
`nodeS7 <https://github.com/plcpeople/nodeS7>`_:

1. **Sort** — items are sorted by area, DB number, and byte offset so that
   adjacent reads end up next to each other.

2. **Merge** — sorted items in the same area/DB with a small gap between them
   (configurable via ``multi_read_max_gap``) are merged into contiguous read
   blocks. This avoids issuing many small reads when a single larger read
   covers them all.

3. **Packetize** — merged blocks are packed into PDU-sized packets, respecting
   both the request and reply size budgets of the negotiated PDU length.

Parallel dispatch
-----------------

When there are multiple packets to send, the optimizer can fire them
back-to-back on the same TCP connection and collect responses by sequence
number (pipelining). This avoids paying a full round-trip per packet.

The number of in-flight packets is controlled by ``max_parallel``, which is
auto-tuned based on the negotiated PDU size after connecting:

.. list-table::
   :header-rows: 1

   * - PDU size
     - max_parallel
   * - >= 960
     - 8
   * - >= 480
     - 4
   * - >= 240
     - 2
   * - < 240
     - 1 (sequential)

You can override it manually::

   client.max_parallel = 2   # limit to 2 in-flight packets

Configuration
-------------

.. code-block:: python

   client.use_optimizer = False          # disable optimizer entirely
   client.multi_read_max_gap = 10        # merge reads up to 10 bytes apart (default 5)
   client.max_parallel = 1               # disable parallel dispatch (sequential only)

Plan caching
------------

The optimizer caches the merge/packetize plan for repeated calls with the same
item layout. If you always read the same set of variables in a loop (a common
pattern in PLC polling), the planning overhead is paid only on the first call.

API reference
-------------

.. automodule:: snap7.optimizer
   :members:
