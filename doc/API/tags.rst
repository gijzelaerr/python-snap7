Tags
====

Symbolic and typed access to PLC variables.

A :class:`~snap7.tags.Tag` describes a typed value at a specific S7 address.
Tags can be constructed from a PLC4X-style address string, or loaded in
bulk from CSV, JSON, or TIA Portal XML exports.

.. code-block:: python

   from s7 import Client, Tag, load_tia_xml

   client = Client()
   client.connect("192.168.1.10", 0, 1)

   # Ad-hoc access with PLC4X-style strings
   speed = client.read_tag("DB1.DBD0:REAL")
   running = client.read_tag("DB1.DBX4.0:BOOL")
   client.write_tag("DB1.DBW6:INT", 1500)

   # Batch read (uses optimizer when enabled)
   values = client.read_tags(["DB1.DBD0:REAL", "DB1.DBW6:INT"])

   # Load named tags from a TIA Portal XML export
   tags = load_tia_xml("db1.xml")
   temperature = client.read_tag(tags["Motor.Temperature"])

Address syntax
--------------

Two dialects are supported. Each has its own parser class that returns a
subtype of :class:`~snap7.tags.Tag`; a ``__str__`` on each subtype
round-trips to its source dialect.

**PLC4X / Siemens STEP7** — :class:`~snap7.tags.PLC4XTag`::

   DB1.DBX0.0:BOOL          # bit in data block
   DB1.DBB10:BYTE           # byte
   DB1.DBW10:INT            # word (2 bytes)
   DB1.DBD10:REAL           # double word (4 bytes)
   DB1:10:INT               # short form (DB 1, offset 10)
   DB1:10:STRING[20]        # variable-length string
   DB1:10:REAL[5]           # array of 5 REALs
   M10.5:BOOL               # Merker bit
   MW20:WORD                # Merker word
   I0.0:BOOL                # input bit
   Q0.0:BOOL                # output bit

The leading ``%`` is optional (``%DB1.DBX0.0:BOOL`` also works). The type
suffix (``:TYPE``) is required.

**nodeS7 / pyS7** — :class:`~snap7.tags.NodeS7Tag`::

   DB1,X0.0                 # bit in data block
   DB1,B10                  # byte
   DB1,W10                  # word (unsigned 16-bit)
   DB1,I10                  # int (signed 16-bit)
   DB1,DW10                 # dword / DB1,DI10 for dint
   DB1,R4                   # real
   DB1,LR8                  # lreal
   DB1,S10.20               # string at offset 10, 20 chars
   M10.5                    # marker bit
   MB10, MW10, MD10, MR10   # marker typed
   IW22, QR24               # input word, output real

Area shortcuts (``M``, ``I``, ``Q``, plus German ``E``, ``A``) imply the
type via the trailing typecode; no ``:TYPE`` suffix is needed.

**Autodetect** — :func:`~snap7.tags.parse_tag` picks the right parser
based on syntax markers. Pass ``strict=False`` to accept bare short
forms like ``M7.1`` or ``IW22`` (dispatched to the nodeS7 parser)::

   from snap7.tags import parse_tag

   parse_tag("DB1.DBD0:REAL")       # → PLC4XTag
   parse_tag("DB1,R0")              # → NodeS7Tag
   parse_tag("M7.1")                # raises: ambiguous under strict=True
   parse_tag("M7.1", strict=False)  # → NodeS7Tag (BOOL)

Supported types
---------------

``BOOL``, ``BYTE``, ``CHAR``, ``WCHAR``, ``SINT``, ``USINT``, ``INT``,
``UINT``, ``WORD``, ``DINT``, ``UDINT``, ``DWORD``, ``LINT``, ``ULINT``,
``LWORD``, ``REAL``, ``LREAL``, ``TIME``, ``LTIME``, ``TOD``, ``LTOD``,
``DATE``, ``DT``, ``LDT``, ``DTL``, ``STRING[n]``, ``WSTRING[n]``,
``FSTRING[n]``.

Arrays are supported for any fixed-size type via ``[count]`` suffix.

Optimized block access (S7CommPlus)
------------------------------------

.. warning::

   Symbolic (LID-based) access is **experimental** and requires real PLC
   testing.  The wire-level implementation follows the S7CommPlusDriver
   reference but has not yet been validated against hardware.

S7-1200/1500 DBs with "Optimized block access" enabled (the default in
TIA Portal V13+) do not use fixed byte offsets.  The PLC internally
relocates variables between downloads, so addresses like ``DB1.DBX0.0``
are unreliable.

For optimized blocks, use :meth:`~snap7.tags.Tag.from_access_string`
with LIDs discovered via :meth:`~s7.client.Client.browse`:

.. code-block:: python

   from s7 import Client, Tag

   client = Client()
   client.connect("192.168.1.10", 0, 1)

   # Create a symbolic tag (LIDs come from browse)
   tag = Tag.from_access_string(
       "8A0E0001.A",           # DB1, LID 0xA
       datatype="REAL",
       name="Motor.Speed",
       symbol_crc=0x12345678,  # optional layout version check
   )

   # Read/write via S7CommPlus symbolic access
   speed = client.read_tag(tag)
   client.write_tag(tag, 1500.0)

API reference
-------------

.. automodule:: snap7.tags
   :members:
