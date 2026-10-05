PLC Support Matrix
==================

python-snap7 supports PLCs that expose the classic S7 protocol. Newer
controllers require PUT/GET access to be enabled in TIA Portal.

Supported PLCs
--------------

.. list-table::
   :header-rows: 1
   :widths: 25 15 20 40

   * - PLC Family
     - Introduced
     - S7 support
     - Notes
   * - S7-300
     - ~1994
     - Full
     - Works out of the box with ``s7.Client``.
   * - S7-400
     - ~1996
     - Full
     - Works out of the box with ``s7.Client``.
   * - S7-1200
     - 2009
     - PUT/GET
     - Enable PUT/GET in TIA Portal.
   * - S7-1500
     - 2012
     - PUT/GET
     - Enable PUT/GET in TIA Portal.
   * - S7-1500R/H
     - ~2019
     - Not supported
     - Redundant CPUs have no classic S7 fallback.
   * - ET 200SP CPU
     - ~2014
     - PUT/GET
     - Same behavior as an S7-1500 with matching firmware.
   * - S7-200 SMART
     - ~2012
     - Partial
     - Basic Ethernet read/write works; advanced functions may be unavailable.
   * - S7-200 (serial PPI)
     - ~1994
     - Experimental
     - Use :class:`~snap7.ppi.PPIClient`; see :doc:`ppi` for current limits.
   * - LOGO! 8
     - ~2014
     - Full
     - Use the :class:`~snap7.logo.Logo` class.

Enabling PUT/GET Access
-----------------------

For S7-1200 and S7-1500 PLCs, classic S7 protocol access requires the
**PUT/GET** option to be enabled. See :doc:`tia-portal-config` for
step-by-step instructions.

.. note::

   S7-1200 and S7-1500 CPUs natively speak **S7CommPlus**, the protocol TIA
   Portal itself uses. python-snap7 does not implement it. What it uses on
   these CPUs is the classic S7 protocol, which the CPU only serves as a
   compatibility feature (PUT/GET). That compatibility path is deliberately
   limited:

   - it only reaches non-optimized data blocks and the I/O, marker, timer and
     counter areas, so symbolic access to optimized DBs is not possible;
   - program blocks (OB/FC/FB) and block upload/download are generally
     refused, and the project source is never available;
   - it has no authentication, which is why Siemens disables it by default.

   If you need optimized DBs, symbolic access or any of the above, use an
   S7CommPlus client such as the standalone
   `s7commplus project <https://github.com/gijzelaerr/s7commplus>`_, OPC UA,
   or TIA Portal Openness, rather than trying to make python-snap7 do it.

.. warning::

   PUT/GET access provides unauthenticated read/write access to PLC memory.
   Only enable this on networks that are properly segmented and secured.

Feature Availability
--------------------

The matrix describes transport-level access, not a guarantee that every client
method is implemented by every CPU. Block transfer, CPU control, forcing,
passwords, diagnostic SZLs, and clock operations vary by model, firmware, and
protection level. See :doc:`advanced` and handle
:class:`~snap7.error.S7ProtocolError` when probing optional PLC capabilities.

For example, an S7-1200 CPU 1212C (firmware V4.7.3) with PUT/GET enabled
serves DB reads and writes but refuses ``upload()`` of a non-optimized DB with
``S7ProtocolError`` class 0x81, code 0x04 ("This service is not implemented on
the module") (`#907 <https://github.com/gijzelaerr/python-snap7/issues/907>`_).
Treat block upload and download on S7-1200/1500 as unsupported unless verified
on your CPU and firmware.

Alternatives for Unsupported PLCs
---------------------------------

If your PLC is not supported by python-snap7, consider these alternatives:

- **OPC UA**: S7-1500 PLCs (FW 2.0+) include a built-in OPC UA server. Use
  a Python OPC UA client such as `opcua-asyncio <https://github.com/FreeOpcUa/opcua-asyncio>`_.
- **TIA Portal**: Siemens' official engineering tool supports all protocols
  and PLC families.
- **PROFINET**: For real-time communication needs, PROFINET may be more
  appropriate than S7 communication.
