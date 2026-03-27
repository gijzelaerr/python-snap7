Introduction
============

python-snap7 is a pure Python S7 communication library for interfacing
natively with Siemens S7 PLCs. The library implements the complete S7
protocol stack including TPKT (RFC 1006), COTP (ISO 8073), and S7
protocol layers.

The name "python-snap7" is historical: the library originally started as a
Python wrapper around the `Snap7 <http://snap7.sourceforge.net/>`_ C library.
As of version 3.0, the C library is no longer used, but the name is kept for
backwards compatibility.

python-snap7 requires Python 3.10+ and runs on Windows, macOS and Linux
without any native dependencies.

The library provides two packages:

- **snap7** -- the original S7 protocol implementation, supporting S7-300,
  S7-400, S7-1200 and S7-1500 PLCs via the classic PUT/GET interface.
- **s7** -- a newer unified client that automatically tries the S7CommPlus
  protocol (used natively by S7-1200/1500) and falls back to legacy S7 when
  needed. ``s7.Client`` is a drop-in replacement for ``snap7.Client``.

.. note::

   The ``s7`` package and its S7CommPlus support are **experimental**.
   The legacy ``snap7`` package remains fully supported and is the safe choice
   for production use. See :doc:`API/s7commplus` for details.

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
