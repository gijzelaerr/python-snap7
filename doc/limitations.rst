Protocol Limitations and FAQ
============================

python-snap7 implements both the classic S7 protocol and S7CommPlus over
TCP/IP. The following limitations apply to the classic protocol exposed by
``s7.Client``; the native S7CommPlus client has different capabilities:

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - Limitation
     - Explanation
   * - Read tag/symbol names from PLC
     - The classic S7 protocol only addresses data by area, DB number, and byte
       offset. The experimental ``s7commplus.Client.browse()`` API can read the
       symbol tree from supported S7-1200/1500 PLCs.
   * - Get DB structure or layout from PLC
     - Classic S7 reads DBs as raw bytes, so callers must supply the layout.
       S7CommPlus browsing can reconstruct type information and optimized
       symbolic access paths on supported S7-1200/1500 PLCs.
   * - Discover PLCs on the network
     - The classic S7 protocol has no broadcast discovery mechanism. However,
       python-snap7 provides PROFINET DCP discovery via the ``s7 discover``
       CLI command (requires ``pip install python-snap7[discovery]``).
       See :doc:`cli` for details.
   * - Create PLC backups
     - Full project backup requires TIA Portal. python-snap7 can upload
       individual blocks, but this is not a complete backup.
   * - S7CommPlus V4
     - python-snap7 supports S7CommPlus V1, V2, and V3 via the ``s7commplus``
       package. V4 is not yet supported. For PLCs that require V4, use OPC UA
       as an alternative.
