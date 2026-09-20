.. image:: https://img.shields.io/pypi/v/python-snap7.svg
   :target: https://pypi.org/project/python-snap7/

.. image:: https://img.shields.io/pypi/pyversions/python-snap7.svg
   :target: https://pypi.org/project/python-snap7/

.. image:: https://img.shields.io/github/license/gijzelaerr/python-snap7.svg
   :target: https://github.com/gijzelaerr/python-snap7/blob/master/LICENSE

.. image:: https://github.com/gijzelaerr/python-snap7/actions/workflows/test.yml/badge.svg
   :target: https://github.com/gijzelaerr/python-snap7/actions/workflows/test.yml

.. image:: https://readthedocs.org/projects/python-snap7/badge/
   :target: https://python-snap7.readthedocs.io/en/latest/


python-snap7
============

python-snap7 is a pure-Python library for communicating with Siemens S7 PLCs
using the classic S7 protocol. It supports S7-300 and S7-400 controllers, as
well as S7-1200 and S7-1500 controllers with PUT/GET access enabled. It
supports Python 3.10+ on Windows, Linux, and macOS without native dependencies.

Installation
============

Install from PyPI::

   pip install python-snap7

Quick start
===========

::

   from s7 import Client

   client = Client()
   client.connect("192.168.1.10", 0, 1)
   data = client.db_read(1, 0, 4)
   client.disconnect()

The ``s7`` package is the recommended import. The ``snap7`` package name is
also available for backwards compatibility.

Experimental S7-200 PPI support
--------------------------------

Serial PPI communication is available through an optional dependency::

   $ pip install "python-snap7[ppi]"

Use ``PPIClient`` with the serial device and S7-200 station address. V memory
is translated to DB1, matching the PLC wire protocol::

   from s7 import PPIClient

   with PPIClient("/dev/ttyUSB0", station=2, baudrate=9600) as client:
       value = client.v_read(0, 4)
       client.v_write(10, b"\x01\x02")

The generic ``read_area()`` and ``write_area()`` methods accept ``PPIArea``
values for S, SM, AI, AQ, I, Q, M, V, counters, and timers. The initial
implementation supports a PC master talking to one S7-200 slave using SD1/SD2
request framing. Multimaster token passing and PPI-over-TCP are not yet
implemented and require hardware or trace validation.

Documentation
=============

Read the full documentation at
`python-snap7.readthedocs.io <https://python-snap7.readthedocs.io/en/latest/>`_.

For native communication with S7-1200 and S7-1500 controllers without PUT/GET,
see the standalone `s7commplus <https://github.com/gijzelaerr/s7commplus>`_ package.
