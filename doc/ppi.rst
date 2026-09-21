S7-200 Serial PPI
=================

python-snap7 3.2 adds experimental serial PPI support for a PC master talking
to one Siemens S7-200 slave. Install the optional serial dependency first::

   pip install "python-snap7[ppi]"

Connect with the serial device and PLC station address::

   from s7 import PPIClient

   with PPIClient("/dev/ttyUSB0", station=2, baudrate=9600) as client:
       data = client.v_read(0, 4)
       client.v_write(10, b"\x01\x02")

On Windows, pass a port such as ``"COM3"``. The serial transport uses the PPI
8E1 format. The adapter must provide the physical interface required by the
PLC; a serial device name alone does not imply electrical compatibility.

Memory areas
------------

Use :class:`~snap7.ppi.PPIArea` with ``read_area()`` and ``write_area()``:

.. list-table::
   :header-rows: 1
   :widths: 20 30 50

   * - Area
     - Meaning
     - Count and data units
   * - ``S`` / ``SM``
     - Special memory / special markers
     - Bytes
   * - ``I`` / ``Q`` / ``M``
     - Inputs / outputs / markers
     - Bytes
   * - ``V``
     - Variable memory
     - Bytes; encoded as DB1 on the wire
   * - ``AI`` / ``AQ``
     - Analog inputs / outputs
     - 16-bit items
   * - ``C`` / ``T``
     - Counters / timers
     - 16-bit items

For example::

   from s7 import PPIArea, PPIClient

   with PPIClient("/dev/ttyUSB0", station=2) as client:
       marker_bytes = client.read_area(PPIArea.M, start=0, count=8)
       counters = client.read_area(PPIArea.C, start=0, count=2)

Limits
------

The initial implementation supports SD1/SD2 request framing, PDU negotiation,
bounded retries, and a single PC-master/single-PLC exchange. It does not
implement multimaster token passing or PPI over TCP. Request sizes must fit the
negotiated PDU and the PPI frame-size limit. Validate the transport against the
target hardware before relying on it in production.

See :doc:`API/ppi` for all constructor options, frame helpers, and low-level
transport classes.
