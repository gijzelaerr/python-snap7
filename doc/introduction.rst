Introduction
============

python-snap7 is a pure Python S7 communication library for interfacing
natively with Siemens S7 PLCs. The library implements the complete S7
protocol stack including TPKT (RFC 1006), COTP (ISO 8073), and S7
protocol layers, as well as the S7CommPlus protocol for newer PLCs.

The name "python-snap7" is historical: the library originally started as a
Python wrapper around the `Snap7 <http://snap7.sourceforge.net/>`_ C library.
As of version 3.0, the C library is no longer used, but the name is kept for
backwards compatibility.

python-snap7 requires Python 3.10+ and runs on Windows, macOS and Linux
without any native dependencies.

The ``s7commplus`` package
--------------------------

For S7-1200 and S7-1500 PLCs, the ``s7commplus`` package provides a native
S7CommPlus protocol client. It supports V1, V2 (TLS), and V3 connections:

.. code-block:: python

   from s7commplus import Client

   client = Client()
   client.connect("192.168.1.10")
   data = client.db_read(1, 0, 4)
   client.disconnect()

The ``snap7`` package (legacy S7)
----------------------------------

The ``snap7`` package implements the classic S7 protocol. It supports
S7-300, S7-400, S7-1200 and S7-1500 PLCs via the PUT/GET interface:

.. code-block:: python

   from snap7 import Client

   client = Client()
   client.connect("192.168.1.10", 0, 1)
   data = client.db_read(1, 0, 4)
   client.disconnect()

Use ``snap7.Client`` for S7-300/400 PLCs or when PUT/GET access is enabled
on S7-1200/1500. Use ``s7commplus.Client`` for native S7CommPlus communication
with S7-1200/1500 PLCs.

.. note::

   **Version 3.0 is a complete rewrite.** Previous versions of python-snap7
   were a wrapper around the C snap7 shared library. Starting with version 3.0,
   the entire protocol stack is implemented in pure Python. This eliminates the
   need for platform-specific shared libraries and makes the library portable to
   any platform that runs Python.

   If you experience issues, please report them on the
   `issue tracker <https://github.com/gijzelaerr/python-snap7/issues>`_ with a
   clear description and the version you are using. As a workaround, you can
   install the last pre-3.0 release with ``pip install "python-snap7<3"``.

The project development is centralized on `github <https://github.com/gijzelaerr/python-snap7>`_.
