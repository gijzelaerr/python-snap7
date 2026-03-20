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
     - There is no S7 broadcast discovery mechanism. You must know the PLC's IP
       address.
   * - Create PLC backups
     - Full project backup requires TIA Portal. python-snap7 can upload
       individual blocks, but this is not a complete backup.
   * - Access S7-1200/1500 PLCs with S7CommPlus security
     - PLCs configured to require S7CommPlus encrypted communication cannot be
       accessed with the classic S7 protocol. PUT/GET must be enabled as a
       fallback.
