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

S7-1200 and S7-1500
===================

On S7-1200 and S7-1500 controllers, python-snap7 only works when PUT/GET access
is enabled in TIA Portal, and it cannot access optimized data blocks. PUT/GET
is unauthenticated and disabled by default, so leaving it disabled is the more
secure configuration.

If PUT/GET is disabled, or you need optimized data blocks or symbolic access,
use `s7commplus <https://github.com/gijzelaerr/s7commplus>`_ instead::

   pip install s7commplus

s7commplus is a separate, younger project that implements S7CommPlus, the
protocol these controllers speak natively. Check the
`firmware versions validated so far <https://s7commplus.readthedocs.io/en/latest/connections.html>`_
before relying on it, and see the
`PLC support matrix <https://python-snap7.readthedocs.io/en/latest/plc-support.html>`_
for what python-snap7 supports on each controller family.

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

Documentation
=============

Read the full documentation at
`python-snap7.readthedocs.io <https://python-snap7.readthedocs.io/en/latest/>`_.

The safe volunteer hardware-test procedure is in
`Real-PLC acceptance testing <doc/real-plc-testing.rst>`_.
