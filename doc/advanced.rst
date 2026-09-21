Advanced PLC Operations
=======================

The client API includes PLC management operations in addition to memory reads
and writes. Availability depends on the PLC family, firmware, protection
level, and current CPU state. A PLC can reject a valid request that it does not
implement.

The examples below use :class:`~snap7.client.Client`. The corresponding
:class:`~snap7.async_client.AsyncClient` methods have the same purpose and must
be awaited.

Identification and diagnostics
------------------------------

Read common identification and status records after connecting::

   order_code = client.get_order_code()
   cpu_info = client.get_cpu_info()
   cp_info = client.get_cp_info()
   protection = client.get_protection()
   state = client.get_cpu_state()
   diagnostics = client.read_diagnostic_buffer()

For records without a convenience method, use ``read_szl(szl_id, index)`` or
``read_szl_list()``. SZL layouts vary between PLC generations; the typed
helpers in :mod:`snap7.szl` parse the layouts used by the convenience methods.

CPU state and clock
-------------------

``plc_stop()``, ``plc_hot_start()``, and ``plc_cold_start()`` change CPU state.
Clock operations are provided by ``get_plc_datetime()``,
``set_plc_datetime()``, and ``set_plc_system_datetime()``.

.. warning::

   CPU control and clock changes affect a real controller. Confirm that the
   operation is safe for the machine and process before issuing it.

Block operations
----------------

Use ``list_blocks()`` and ``list_blocks_of_type()`` to enumerate blocks,
``get_block_info()`` to inspect one, ``upload()`` or ``full_upload()`` to read
one, and ``download()`` or ``delete()`` to modify the PLC. ``compress()`` and
``copy_ram_to_rom()`` expose the corresponding PLC maintenance operations.

These methods transfer individual PLC blocks; they do not create a complete
TIA Portal project or full PLC backup.

Session passwords
-----------------

For classic S7 CPUs configured with a session password, authenticate after
connecting and clear the password before disconnecting::

   client.connect("192.168.1.10", 0, 2)
   client.set_session_password("secret")
   try:
       data = client.db_read(1, 0, 4)
   finally:
       client.clear_session_password()
       client.disconnect()

Forcing inputs and outputs
--------------------------

``force_bit()`` and ``cancel_force()`` support the ``Area.PE`` input and
``Area.PA`` output areas. ``read_force_table()`` returns active force entries
when the PLC supports SZL 0x0025::

   from s7.type import Area

   client.force_bit(Area.PA, byte_offset=0, bit=1, value=True)
   active_forces = client.read_force_table()
   client.cancel_force(Area.PA, byte_offset=0, bit=1)

.. warning::

   A force overrides normal process behavior and can remain active after the
   application exits. Track every applied force and cancel it deliberately.

Raw protocol and compatibility operations
-----------------------------------------

``iso_exchange_buffer()`` sends a caller-provided S7 PDU. The ``as_*`` methods
and completion callbacks preserve compatibility with the historical Snap7 API;
new asynchronous applications should normally use ``AsyncClient`` instead.
See :doc:`API/client` for the complete method reference.
