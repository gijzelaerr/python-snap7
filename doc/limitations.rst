Protocol Limitations and FAQ
============================

python-snap7 implements the classic S7 protocol over TCP/IP. The following
limitations apply to ``s7.Client``:

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - Limitation
     - Explanation
   * - Read tag/symbol names from PLC
     - The classic S7 protocol only addresses data by area, DB number, and byte
       offset; callers must provide the addresses.
   * - Get DB structure or layout from PLC
     - Classic S7 reads DBs as raw bytes, so callers must supply the layout.
   * - Discover PLCs on the network
     - The classic S7 protocol has no broadcast discovery mechanism. However,
       python-snap7 provides PROFINET DCP discovery via the ``s7 discover``
       CLI command (requires ``pip install python-snap7[discovery]``).
       See :doc:`cli` for details.
   * - Create PLC backups
     - Full project backup requires TIA Portal. python-snap7 can upload
       individual blocks, but this is not a complete backup.
