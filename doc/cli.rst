Command-Line Interface
======================

python-snap7 includes a CLI tool called ``s7`` for interacting with Siemens S7 PLCs
from the terminal. Install the CLI dependencies with::

    pip install python-snap7[cli]

All subcommands are available via ``s7 <subcommand>``. Use ``s7 --help`` to see
available commands, or ``s7 <subcommand> --help`` for detailed usage.

Common Options
--------------

.. option:: -v, --verbose

   Enable debug logging output.

.. option:: --version

   Show the python-snap7 version and exit.

server
------

Start an emulated S7 PLC server with default values::

    s7 server
    s7 server --port 1102

.. option:: -p, --port PORT

   Port the server will listen on (default: 1102).

read
----

Read data from a PLC data block::

    # Read 16 raw bytes from DB1 at offset 0
    s7 read 192.168.1.10 --db 1 --offset 0 --size 16

    # Read a typed value
    s7 read 192.168.1.10 --db 1 --offset 0 --type int
    s7 read 192.168.1.10 --db 1 --offset 4 --type real

    # Read a boolean (bit 3 of byte at offset 0)
    s7 read 192.168.1.10 --db 1 --offset 0 --type bool --bit 3

.. option:: --db DB

   DB number to read from (required).

.. option:: --offset OFFSET

   Byte offset to start reading (required).

.. option:: --size SIZE

   Number of bytes to read (required for ``--type bytes``).

.. option:: --type TYPE

   Data type to read. Choices: ``bool``, ``byte``, ``int``, ``uint``, ``word``,
   ``dint``, ``udint``, ``dword``, ``real``, ``lreal``, ``string``, ``bytes``
   (default: ``bytes``).

.. option:: --bit BIT

   Bit offset within the byte (only for ``bool`` type, default: 0).

.. option:: --rack RACK

   PLC rack number (default: 0).

.. option:: --slot SLOT

   PLC slot number (default: 1).

.. option:: --port PORT

   PLC TCP port (default: 102).

write
-----

Write data to a PLC data block::

    # Write raw bytes (hex)
    s7 write 192.168.1.10 --db 1 --offset 0 --type bytes --value "01 02 03 04"

    # Write a typed value
    s7 write 192.168.1.10 --db 1 --offset 0 --type int --value 42
    s7 write 192.168.1.10 --db 1 --offset 4 --type real --value 3.14

    # Write a boolean
    s7 write 192.168.1.10 --db 1 --offset 0 --type bool --bit 3 --value true

.. option:: --db DB

   DB number to write to (required).

.. option:: --offset OFFSET

   Byte offset to start writing (required).

.. option:: --type TYPE

   Data type to write (required). Same choices as ``read``.

.. option:: --value VALUE

   Value to write (required). For ``bytes`` type, provide hex (e.g. ``"01 02 FF"``).
   For ``bool``, use ``true``/``false``/``1``/``0``.

.. option:: --bit, --rack, --slot, --port

   Same as ``read``.

dump
----

Dump the contents of a data block as a hex dump::

    s7 dump 192.168.1.10 --db 1
    s7 dump 192.168.1.10 --db 1 --size 512 --format hex

.. option:: --db DB

   DB number to dump (required).

.. option:: --size SIZE

   Number of bytes to dump (default: 256).

.. option:: --format FORMAT

   Output format: ``hex`` (default) or ``bytes`` (raw hex string).

.. option:: --rack, --slot, --port

   Same as ``read``.

info
----

Get PLC information including CPU info, state, order code, protection level,
and block counts::

    s7 info 192.168.1.10
    s7 info 192.168.1.10 --rack 0 --slot 2

.. option:: --rack, --slot, --port

   Same as ``read``.

discover
--------

Discover PROFINET devices on the local network using DCP (Discovery and basic
Configuration Protocol). Requires the ``discovery`` extra::

    pip install python-snap7[discovery]

Usage::

    # Discover all devices (IP is the local network interface to use)
    s7 discover 192.168.1.1
    s7 discover 192.168.1.1 --timeout 10

.. option:: --timeout SECONDS

   How long to listen for responses (default: 5.0).

.. note::

   Network discovery uses raw sockets and may require elevated privileges
   (root/administrator) depending on your platform.
