About
=====

Python-snap7 is a pure Python S7 communication library for interfacing with Siemens S7 PLCs.

Python-snap7 is tested with Python 3.10+, on Windows, Linux and OS X.

The full documentation is available on `Read The Docs <https://python-snap7.readthedocs.io/en/latest/>`_.


Version 3.0 - Breaking Changes
===============================

Version 3.0 is a major release that rewrites python-snap7 as a pure Python
implementation. The C snap7 library is no longer required.

This release may contain breaking changes. If you experience issues, you can
pin to the last pre-3.0 release::

    $ pip install "python-snap7<3"

The latest stable pre-3.0 release is version 2.1.0.


Installation
============

Install using pip::

   $ pip install python-snap7

No native libraries or platform-specific dependencies are required - python-snap7 is a pure Python package that works on all platforms.


Async support
=============

An ``AsyncClient`` is available for use with ``asyncio``::

   import asyncio
   import snap7

   async def main():
       async with snap7.AsyncClient() as client:
           await client.connect("192.168.1.10", 0, 1)
           data = await client.db_read(1, 0, 4)
           print(data)

   asyncio.run(main())
