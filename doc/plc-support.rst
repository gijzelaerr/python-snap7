PLC Support Matrix
==================

This page documents which Siemens PLC families are supported by python-snap7,
the communication protocols they use, and any configuration requirements.

Supported PLCs
--------------

.. list-table::
   :header-rows: 1
   :widths: 20 10 10 10 10 15 25

   * - PLC Family
     - Introduced
     - S7 (classic)
     - S7CommPlus V1
     - S7CommPlus V2/V3
     - python-snap7 support
     - Notes
   * - S7-300
     - ~1994
     - Yes
     - No
     - No
     - **Full**
     - Works out of the box.
   * - S7-400
     - ~1996
     - Yes
     - No
     - No
     - **Full**
     - Works out of the box.
   * - S7-1200 (FW ≤3)
     - 2009
     - Yes
     - No
     - No
     - **Full**
     - Enable PUT/GET access in TIA Portal.
   * - S7-1200 (FW 4+)
     - ~2014
     - Yes
     - Yes
     - No
     - **Full**
     - Enable PUT/GET access in TIA Portal. Uses classic S7.
   * - S7-1500 (FW 1.x)
     - 2012
     - PUT/GET only
     - Yes
     - No
     - **Full** (experimental S7CommPlus)
     - S7CommPlus V1 session + legacy S7 fallback for data.
   * - S7-1500 (FW 2.x)
     - ~2016
     - PUT/GET only
     - No
     - V2
     - **Full** (S7CommPlus V2)
     - S7CommPlus V2 with TLS is supported via the ``s7`` package.
   * - S7-1500 (FW 3.x+)
     - ~2022
     - PUT/GET only
     - No
     - V3
     - **PUT/GET only**
     - S7CommPlus V3 uses proprietary crypto; not yet supported.
   * - S7-1500R/H
     - ~2019
     - No
     - No
     - V2/V3
     - **Not supported**
     - Redundant CPUs; no classic S7 fallback available.
   * - ET 200SP CPU
     - ~2014
     - PUT/GET only
     - Yes
     - Yes
     - **PUT/GET only**
     - Same behavior as S7-1500 with matching firmware.
   * - S7-200 SMART
     - ~2012
     - Subset
     - No
     - No
     - **Partial**
     - Basic read/write works. Some advanced functions may not be available.
   * - LOGO! 8
     - ~2014
     - Subset
     - No
     - No
     - **Full**
     - Use the :class:`~snap7.logo.Logo` class.


Enabling PUT/GET Access
-----------------------

For S7-1200 and S7-1500 PLCs, classic S7 protocol access requires the
**PUT/GET** option to be enabled. See :doc:`tia-portal-config` for
step-by-step instructions.

.. warning::

   PUT/GET access provides unauthenticated read/write access to PLC memory.
   Only enable this on networks that are properly segmented and secured.


Protocol Overview
-----------------

Siemens has evolved their PLC communication protocols over time:

.. list-table::
   :header-rows: 1
   :widths: 20 15 15 50

   * - Protocol
     - Encryption
     - Authentication
     - Used by
   * - S7 (classic)
     - None
     - None
     - S7-300, S7-400, S7-1200, S7-1500 (PUT/GET mode)
   * - S7CommPlus V1
     - None
     - Challenge-response
     - S7-1200 FW 4+, S7-1500 FW 1.x
   * - S7CommPlus V2
     - TLS 1.3
     - Challenge-response + TLS
     - S7-1500 FW 2.x
   * - S7CommPlus V3
     - TLS
     - Certificate-based
     - S7-1500 FW 3.x+

python-snap7 implements the **classic S7 protocol** and **S7CommPlus V1/V2**.
The classic protocol remains available on most PLC families via the PUT/GET
mechanism. S7CommPlus V1 and V2 (with TLS) are supported via the
``s7`` package. For PLCs that require S7CommPlus V3 (such
as the S7-1500R/H), consider using OPC UA as an alternative.


Alternatives for Unsupported PLCs
---------------------------------

If your PLC is not supported by python-snap7, consider these alternatives:

- **OPC UA**: S7-1500 PLCs (FW 2.0+) include a built-in OPC UA server. Use
  a Python OPC UA client such as `opcua-asyncio <https://github.com/FreeOpcUa/opcua-asyncio>`_.
- **TIA Portal**: Siemens' official engineering tool supports all protocols
  and PLC families.
- **PROFINET**: For real-time communication needs, PROFINET may be more
  appropriate than S7 communication.
