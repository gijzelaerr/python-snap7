About
=====

Python-snap7 is a pure Python S7 communication library for interfacing with Siemens S7 PLCs.

The name "python-snap7" is historical — the library originally started as a Python wrapper
around the `Snap7 <http://snap7.sourceforge.net/>`_ C library. As of version 3.0, the C
library is no longer used, but the name is kept for backwards compatibility.

Python-snap7 is tested with Python 3.10+, on Windows, Linux and OS X.

The full documentation is available on `Read The Docs <https://python-snap7.readthedocs.io/en/latest/>`_.


Quick Start
===========

Connect to any S7 PLC::

   import snap7

   client = snap7.Client()
   client.connect("192.168.1.10", 0, 1)
   data = client.db_read(1, 0, 4)
   client.disconnect()

No native libraries or platform-specific dependencies are required.

Async support::

   import asyncio
   import snap7

   async def main():
       async with snap7.AsyncClient() as client:
           await client.connect("192.168.1.10", 0, 1)
           data = await client.db_read(1, 0, 4)

   asyncio.run(main())


What's New in 3.1
=================

* **AsyncClient** for ``asyncio`` support
* **Tag API** -- read/write by name: ``client.read_tag("DB1.DBD0:REAL")``
  with PLC4X and nodeS7 dialect support
* **Multi-variable read optimizer** -- merges scattered reads into minimal
  PDU exchanges
* **S7 routing** -- connect to PLCs on remote subnets via a gateway PLC
* **Heartbeat monitoring** and auto-reconnect with exponential backoff
* **Structured logging** with PLC connection context
* **PROFINET DCP** network discovery
* **CLI tools** for PLC interaction (``pip install "python-snap7[cli]"``)
* Numerous bug fixes -- see `CHANGES.md <https://github.com/gijzelaerr/python-snap7/blob/master/CHANGES.md>`_
  for the full list


Version 3.0 -- Pure Python Rewrite
====================================

Version 3.0 was a ground-up rewrite of python-snap7. The library no longer wraps
the C snap7 shared library -- instead, the entire S7 protocol stack (TPKT, COTP,
and S7) is implemented in pure Python.

* **Portability**: No more platform-specific shared libraries (``.dll``, ``.so``, ``.dylib``).
  Works on any platform that runs Python -- including ARM, Alpine Linux, and other
  environments where the C library was difficult or impossible to install.
* **Easier installation**: Just ``pip install python-snap7``. No native dependencies,
  no compiler toolchains, no manual library setup.
* **Easier to extend**: New features and protocol support can be added directly in Python.


Installation
============

Install using pip::

   $ pip install python-snap7

No native libraries or platform-specific dependencies are required — python-snap7 is a pure Python package that works on all platforms.
