Protocol Limitations and FAQ
============================

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
     - The classic S7 protocol has no broadcast discovery mechanism. However,
       python-snap7 provides PROFINET DCP discovery via the ``s7 discover``
       CLI command (requires ``pip install python-snap7[discovery]``).
       See :doc:`cli` for details.
   * - Create PLC backups
     - Full project backup requires TIA Portal. python-snap7 can upload
       individual blocks, but this is not a complete backup.
   * - Access S7-1200/1500 PLCs with S7CommPlus security
     - python-snap7 supports S7CommPlus V1 and V2 (with TLS) via
       :mod:`snap7.s7commplus`. V3 is not yet supported. For PLCs that only
       support V3, enable PUT/GET as a fallback or use OPC UA.
