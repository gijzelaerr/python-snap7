Introduction
============

python-snap7 is a pure Python implementation of the classic Siemens S7
protocol. It includes the TPKT (RFC 1006), COTP (ISO 8073), and S7 protocol
layers, synchronous and asynchronous clients, and a server for testing.

The name "python-snap7" is historical: the library originally started as a
Python wrapper around the `Snap7 <http://snap7.sourceforge.net/>`_ C library.
As of version 3.0, the C library is no longer used, but the name is kept for
backwards compatibility.

The core package requires Python 3.10+ and has no runtime dependencies. It runs
on Windows, macOS, and Linux. Optional features such as serial PPI, PROFINET
discovery, and the command-line tools have separate extras; see
:doc:`installation`.

Choosing an interface
---------------------

Use :class:`s7.Client <snap7.client.Client>` or
:class:`s7.AsyncClient <snap7.async_client.AsyncClient>` for S7-300/400 PLCs
and for S7-1200/1500 PLCs configured for PUT/GET. Use
:class:`s7.PPIClient <snap7.ppi.PPIClient>` for experimental serial access to
S7-200 PLCs, and :class:`s7.Logo <snap7.logo.Logo>` for LOGO! controllers.

The ``s7`` and ``snap7`` package names
--------------------------------------

``s7`` is the recommended import name:

.. code-block:: python

   from s7 import Client

   client = Client()
   client.connect("192.168.1.10", 0, 1)
   data = client.db_read(1, 0, 4)
   client.disconnect()

.. note::

   The ``snap7`` package name continues to work as an alias for ``s7``
   and is not deprecated. Existing code using ``from snap7 import Client``
   does not need to change.

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

.. note::

   Looking for S7CommPlus support? It moved to the standalone
   `s7commplus project <https://github.com/gijzelaerr/s7commplus>`_.

The project development is centralized on `github <https://github.com/gijzelaerr/python-snap7>`_.
