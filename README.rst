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

Python-snap7 is a pure Python S7 communication library for interfacing with
Siemens S7 PLCs. It supports Python 3.10+ and runs on Windows, Linux, and macOS
without any native dependencies.

The name "python-snap7" is historical -- the library originally started as a
Python wrapper around the `Snap7 <http://snap7.sourceforge.net/>`_ C library.
As of version 3.0, the C library is no longer used, but the name is kept for
backwards compatibility.

The full documentation is available on `Read The Docs <https://python-snap7.readthedocs.io/en/latest/>`_.


Quick Start
===========

Install using pip::

   $ pip install python-snap7

Connect to any S7 PLC::

   import snap7

   client = snap7.Client()
   client.connect("192.168.1.10", 0, 1)
   data = client.db_read(1, 0, 4)
   client.disconnect()

No native libraries or platform-specific dependencies are required.


Version 4.0 -- S7CommPlus & the ``s7`` Package (unreleased)
============================================================

.. note::

   Version 4.0 is **not yet released**. Installing with ``pip install python-snap7``
   gives you version 3.0, which uses the ``snap7`` package shown above.
   To try 4.0 early, install from the development branch::

       $ pip install git+https://github.com/gijzelaerr/python-snap7.git@master

**S7CommPlus protocol support** -- the headline feature of 4.0. S7CommPlus is
required for communicating with S7-1200 and S7-1500 PLCs that have PUT/GET
disabled. python-snap7 now supports S7CommPlus V1, V2 (with TLS), and V3::

   from s7 import Client

   client = Client()
   client.connect("192.168.1.10", 0, 1)  # auto-detects S7CommPlus vs legacy S7
   data = client.db_read(1, 0, 4)
   client.disconnect()

The new ``s7`` package is the recommended entry point for all new projects. It
automatically tries S7CommPlus first (for S7-1200/1500) and falls back to legacy
S7 when needed. The existing ``snap7`` package continues to work unchanged.

**Other new features in 4.0:**

* **Command-line interface** (``s7 read``, ``s7 write``, ``s7 info``)
* **Partner BSend/BRecv** for peer-to-peer communication with S7-1500
* **TCP socket optimization** (TCP_NODELAY, SO_KEEPALIVE) for lower latency
* **S7CommPlus area read/write** for M, I, Q, counters, timers (not just DBs)
* **Structured logging** with PLC connection context for multi-PLC environments

**Experimental features** (API may change):

* **Multi-variable read optimizer** -- merges scattered reads into minimal PDU
  exchanges with parallel dispatch
* **S7 routing** -- connect to PLCs on remote subnets via a gateway PLC
* **Symbolic addressing** -- read/write by tag name instead of raw addresses
* **Live symbol browsing** -- resolve tag names directly from the PLC
* **TIA Portal XML import** -- import symbol tables from TIA Portal exports

**Help us test!** If you have access to any Siemens S7 PLC, we would greatly
appreciate testing and feedback. Please report results on the
`issue tracker <https://github.com/gijzelaerr/python-snap7/issues>`_.


Version 3.0 -- Pure Python Rewrite (current release)
=====================================================

Version 3.0 was a ground-up rewrite of python-snap7. The library no longer wraps
the C snap7 shared library -- instead, the entire S7 protocol stack (TPKT, COTP,
and S7) is implemented in pure Python.

* **Portability**: No more platform-specific shared libraries (``.dll``, ``.so``, ``.dylib``).
  Works on any platform that runs Python -- including ARM, Alpine Linux, and other
  environments where the C library was difficult or impossible to install.
* **Easier installation**: Just ``pip install python-snap7``. No native dependencies,
  no compiler toolchains, no manual library setup.
* **Easier to extend**: New features and protocol support can be added directly in Python.

**If you experience issues with 3.0:**

1. Please report them on the `issue tracker <https://github.com/gijzelaerr/python-snap7/issues>`_.
2. As a workaround, you can pin to the last pre-3.0 release::

       $ pip install "python-snap7<3"

   Documentation for pre-3.0 versions is available at
   `Read The Docs <https://python-snap7.readthedocs.io/en/2.1.1/>`_.
