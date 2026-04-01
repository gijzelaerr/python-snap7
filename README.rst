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

The name "python-snap7" is historical — the library originally started as a
Python wrapper around the `Snap7 <http://snap7.sourceforge.net/>`_ C library.
As of version 3.0, the C library is no longer used, but the name is kept for
backwards compatibility.

The full documentation is available on `Read The Docs <https://python-snap7.readthedocs.io/en/latest/>`_.


Installation
============

Install using pip::

   $ pip install python-snap7

No native libraries or platform-specific dependencies are required — python-snap7
is a pure Python package that works on all platforms.


Version 3.0 — Pure Python Rewrite
==================================

Version 3.0 was a ground-up rewrite of python-snap7. The library no longer wraps
the C snap7 shared library — instead, the entire S7 protocol stack (TPKT, COTP,
and S7) is implemented in pure Python.

* **Portability**: No more platform-specific shared libraries (``.dll``, ``.so``, ``.dylib``).
  Works on any platform that runs Python — including ARM, Alpine Linux, and other
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


Version 3.1 — S7CommPlus Protocol Support (unreleased)
=======================================================

Version 3.1 adds support for the S7CommPlus protocol (up to V3), which is required
for communicating with newer Siemens S7-1200 and S7-1500 PLCs that have PUT/GET
disabled. This is fully backwards compatible with 3.0.

The biggest change is the new ``s7`` module, which is now the recommended entry point
for connecting to any supported S7 PLC::

   from s7 import Client

   client = Client()
   client.connect("192.168.1.10", 0, 1)  # auto-detects S7CommPlus vs legacy S7
   data = client.db_read(1, 0, 4)
   client.disconnect()

The ``s7.Client`` automatically tries S7CommPlus first, and falls back to legacy S7
if the PLC does not support it. The existing ``snap7.Client`` continues to work
unchanged for legacy S7 connections.

**Help us test!** Version 3.1 needs more real-world testing before release. If you
have access to any of the following PLCs, we would greatly appreciate testing and
feedback:

* S7-1200 (any firmware version)
* S7-1500 (any firmware version)
* S7-1500 with TLS enabled
* S7-300
* S7-400
* S7-1200/1500 with PUT/GET disabled (S7CommPlus-only)
* LOGO! 0BA8 and newer

Please report your results — whether it works or not — on the
`issue tracker <https://github.com/gijzelaerr/python-snap7/issues>`_.

To install the development version::

   $ pip install git+https://github.com/gijzelaerr/python-snap7.git@master
